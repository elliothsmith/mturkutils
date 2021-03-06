"""
Module of functions that streamline HIT publishing and data collection from
MTurk. Contact Ethan Solomon (esolomon@mit.edu), Diego Ardila (ardila@mit.edu),
or Ha Hong (hahong@mit.edu) for help!
"""
import pymongo
import copy
import glob
import urllib
import os.path
import itertools
import json
import datetime
import numpy as np
import scipy.stats as stats
import cPickle as pk
from collections import Counter, defaultdict
import csv
import boto
import boto.mturk
from warnings import warn
from tabular.tab import tabarray
from bson.objectid import ObjectId
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.mturk.connection import MTurkConnection
from boto.mturk.qualification import PercentAssignmentsApprovedRequirement
from boto.mturk.qualification import Qualifications
from boto.mturk.question import ExternalQuestion
from boto.pyami.config import Config

import mturkutils.utils as ut

MTURK_SANDBOX_HOST = 'mechanicalturk.sandbox.amazonaws.com'
MTURK_CRED_SECTION = 'MTurkCredentials'
MTURK_PAGE_SIZE_LIMIT = 100    # imposed by Amazon
BOTO_CRED_FILE = os.path.expanduser('~/.boto')
MONGO_PORT = 22334
MONGO_HOST = 'localhost'
MONGO_DBNAME = 'mturk'
IPINFODB_PATT = 'http://api.ipinfodb.com/v3/ip-city/' \
    '?key=8ee1f67f03db64c9d69c0ff899ee36348c3122d1a3e38f5cfaf1ec80ff269ee5' \
    '&ip=%s&format=json'
S3HTTPBASE = 'http://s3.amazonaws.com/'
S3HTTPSBASE = 'https://s3.amazonaws.com/'
LOG_PREFIX = './'
LOOKUP_FIELD = 'id'
BACKUP_ALGO_VER = 1


PREP_RULE_SIMPLE_RSVP_SANDBOX = [
        {
            'old': 'ExperimentData = null;',
            'new': 'ExperimentData = ${CHUNK};',
            'n': 1
        },
        {
            'old': 'https://www.mturk.com/mturk/externalSubmit',
            'new': 'https://workersandbox.mturk.com/mturk/externalSubmit',
            'n': 1
        },
    ]

PREP_RULE_SIMPLE_RSVP_PRODUCTION = [
        {
            'old': 'ExperimentData = null;',
            'new': 'ExperimentData = ${CHUNK};',
            'n': 1
        },
        {
            # Do not remove this part: although this doesn't really replace
            # `old` with `new`, this makes sure that there is one `old`.
            # Also, this part is required to check the existance of `new`
            # with the use of validate_html_files().
            'old': 'https://www.mturk.com/mturk/externalSubmit',
            'new': 'https://www.mturk.com/mturk/externalSubmit',
            'n': 1
        },
    ]


class Experiment(object):
    """An Experiment object contains all the functions and data necessary
    for publishing a hit on MTurk.

    MTurk Parameters
    ----------------
    - sandbox (default True): Publish to the MTurk Worker Sandbox if True
        (workersandbox.mturk.com). I recommend publishing to the sandbox
        first and checking that  your HIT works properly.
    - lifetime: Time, in seconds, for how long the HITs will stay active on
        Mechanical Turk. The default value is 2 weeks, which is fine for
        most purposes.
    - max_assignments: How many Workers are allowed to complete each HIT.
        Remember that a given Worker cannot complete the same HIT twice
        (but they can complete as many HITs within the same HIT Type
        as they want).
    - title: What shows up as the HIT Type header on the MTurk website.
    - reward: In dollars, how much a Worker gets paid for completing 1 HIT.
    - duration: Time, in seconds, that a worker has to complete a HIT aftering
        clicking "accept." I try to give them a comfortable margin beyond how
        long I actually expect the task to take. But don't make it too long or
        workers will be dissuaded from even trying it.
    - approval_delay: Time, in seconds, until MTurk automatically approves HITs
        and pays workers. The default is 2 days.
    - description: The text workers see on the MTurk website before previewing
        a HIT. Should be a short-and-sweet explanation of what the task is
        and how long it should take. Also include the experimental disclaimer.
    - frame_height_pix: Size of the embedded frame that pulls in your external
        URL. 1000 should be fine for most purposes.

    Non-MTurk Parameters
    --------------------
    - collection_name: String, name of collection within the 'mturk'
        database.  If `None`, no DB connection will be made.
    - comment: Explanation of the task and data format to be included in the
        database for this experiment. The description should be adequate for
        future investigators to understand what you did and what the data
        means.
    - meta (optional): Tabarray or dictionary to link stimulus names with their
        metadata. There's some work to be done with this feature. Right now,
        mturkutils extracts image filenames from 'StimShown' and looks up
        metadata in meta by that filename. For speed, it re-sorts any tabarray
        into a dictionary indexed by the original 'id' field.  Feel free to
        pass None and attach metadata yourself later, especially if your
        experiment isn't the usual recognition-style task.
    - log_prefix: Where to save a pickle file with a list of published HIT IDs.
        You can retrieve data from any hit published in the past using these
        IDs (within the Experiment object, the IDs are also saved in 'hitids').
    - set_destination (optional): if True, the destination database name and
        collection name will be set during prepHTMLs()
    """

    def __init__(self, htmlsrc, htmldst, othersrc=None,
            sandbox=True, keywords=None, lifetime=1209600,
            max_assignments=1, title='TEST', reward=0.01, duration=1500,
            approval_delay=172800, description='TEST', frame_height_pix=1000,
            comment='TEST', meta=None,
            log_prefix=LOG_PREFIX, section_name=MTURK_CRED_SECTION,
            bucket_name=None,
            trials_per_hit=100,
            tmpdir='tmp',
            productionpath='html',
            production_prefix='html',
            sandboxpath='html_sandbox',
            sandbox_prefix='html_sandbox',
            tmpdir_production=None,
            tmpdir_sandbox=None,
            trials_loc='trials.pkl',
            html_data=None,
            otherrules=None,
            additionalrules=None,
            mongo_port=None,
            mongo_host=None,
            mongo_dbname=MONGO_DBNAME,
            collection_name='TEST',
            other_quals=None,
            set_destination=False):

        if keywords is None:
            keywords = ['']
        self.sandbox = sandbox
        self.access_key_id, self.secretkey = \
                parse_credentials_file(section_name=section_name)
        self.keywords = keywords
        self.lifetime = lifetime
        self.max_assignments = max_assignments
        self.title = title
        self.reward = reward
        self.duration = duration
        self.approval_delay = approval_delay
        self.description = description
        self.frame_height_pix = frame_height_pix
        self.log_prefix = log_prefix
        self.section_name = section_name
        self.other_quals = other_quals
        self.setQual(90)
        self.bucket_name = bucket_name
        self.set_destination = set_destination

        self.tmpdir = tmpdir
        self.productionpath = productionpath
        self.sandboxpath = sandboxpath
        if tmpdir_production is None:
            tmpdir_production = os.path.join(tmpdir, productionpath)
        self.tmpdir_production = tmpdir_production
        if tmpdir_sandbox is None:
            tmpdir_sandbox = os.path.join(tmpdir, sandboxpath)
        self.tmpdir_sandbox = tmpdir_sandbox
        self.trials_loc = trials_loc
        self.sandbox_prefix = sandbox_prefix
        self.production_prefix = production_prefix

        self.htmlsrc = htmlsrc
        self.htmldst = htmldst
        self.othersrc = othersrc
        self.html_data = html_data
        self.otherrules = otherrules
        self.additionalrules = additionalrules

        self.trials_per_hit = trials_per_hit

        self.comment = comment
        self.meta = meta
        self.mongo_port = mongo_port
        self.mongo_host = mongo_host
        self.mongo_dbname = mongo_dbname
        self.collection_name = collection_name
        self.setMongoVars()
        self.conn = self.connect()

    def payBonuses(self, performance_threshold=None, bonus_threshold=None,
            performance_key='Performance', performance_error=False,
            auto_approve=True):
        """
        This function approves and grants bonuses on all hits above a certain
        performance, with a bonus (stored in database) under a certain
        threshold (checked for safety).
        """
        coll = self.db[self.collection_name]
        if auto_approve:
            for doc in coll.find():
                assignment_id = doc['AssignmentID']
                try:
                    assignment_status = \
                            self.conn.get_assignment(assignment_id
                                    )[0].AssignmentStatus
                    performance = doc.get(performance_key)
                    if (performance_threshold is not None) and \
                            (performance is not None):
                        if (performance_error and
                                performance > performance_threshold) or \
                                        (performance < performance_threshold):
                            if assignment_status in ['Submitted']:
                                self.conn.reject_assignment(assignment_id,
                                    feedback='Your performance was '
                                    'significantly lower than other subjects')
                    else:
                        if assignment_status in ['Submitted']:
                            self.conn.approve_assignment(assignment_id)
                except boto.mturk.connection.MTurkRequestError, e:
                    print('Error for assignment_id %s' % assignment_id, e)
        for doc in coll.find():
            assignment_id = doc['AssignmentID']
            worker_id = doc['WorkerID']
            try:
                assignment_status = \
                        self.conn.get_assignment(assignment_id
                                )[0].AssignmentStatus
            except boto.mturk.connection.MTurkRequestError, e:
                print('Error for assignment_id %s' % assignment_id, e)
                continue
            bonus = doc.get('Bonus')
            if (bonus is not None) and (assignment_status == 'Approved'):
                if (bonus_threshold is None) or (float(bonus) <
                        float(bonus_threshold)):
                    if not doc.get('BonusAwarded', False):
                        bonus = np.round(float(bonus) * 100) / 100
                        if bonus >= 0.01:
                            p = boto.mturk.price.Price(bonus)
                            print 'award granted'
                            print bonus
                            self.conn.grant_bonus(worker_id,
                                    assignment_id,
                                    p,
                                    "Performance Bonus")
                            coll.update({'_id': doc['_id']},
                                    {'$set': {'BonusAwarded': True}},
                                    multi=True)

    def getBalance(self):
        """Returns the amount of available funds. If you're in Sandbox mode,
        this will always return $10,000.
        """
        return self.conn.get_account_balance()[0].amount

    def setMongoVars(self):
        """Establishes connection to database

        :param collection_name: You must specify a valid collection name. If it
            does not already exist, a new collection with that name will be
            created in the mturk database.  If `None` is given, the actual db
            coonection will be bypassed, and all db-related functions will not
            work.
        :param comment: Explanation of the task and data format to be included
            in the database for this experiment. The description should be
            adequate for future investigators to understand what you did and
            what the data means.
        :param meta: You can optionally provide a metadata object, which will
            be converted into a dictionary indexed by the 'id' field (unless
        otherwise specified).
        """

        self.mongo_conn = None
        self.db = None
        self.collection = None

        meta = self.meta
        mongo_dbname = self.mongo_dbname
        collection_name = self.collection_name

        if self.mongo_port is None:
            mongo_port = MONGO_PORT
        else:
            mongo_port = self.mongo_port
        if self.mongo_host is None:
            mongo_host = MONGO_HOST
        else:
            mongo_host = self.mongo_host

        if isinstance(meta, tabarray):
            print('Converting tabarray to dictionary for speed. '
                    'This may take a minute...')
            self.meta = convertTabArrayToDict(meta)
        else:
            self.meta = meta

        # if no db connection is requested, bypass the rest
        if collection_name is None:
            return

        if self.comment is None or len(self.comment) == 0:
            raise AttributeError('Must provide comment!')

        # make db connection and create collection
        if not isinstance(self.collection_name, (str, unicode)) or \
                len(self.collection_name) == 0:
            raise NameError('Please provide a valid MTurk'
                    'database collection name.')

        #Connect to pymongo database for MTurk results.
        self.mongo_conn = pymongo.MongoClient(host=mongo_host, port=mongo_port)
        self.db = self.mongo_conn[mongo_dbname]
        self.collection = self.db[collection_name]

    def createTrials(self):
        raise NotImplementedError

    def prepHTMLs(self, chunkerfunc=None):
        trials = self._trials
        if hasattr(self, '_chunkerfunc'):
            chunkerfunc = self._chunkerfunc
        elif chunkerfunc is None:
            chunkerfunc = ut.dictchunker

        n_per_file = self.trials_per_hit
        htmlsrc = self.htmlsrc
        htmldst = self.htmldst
        auxfns = self.othersrc

        tmpdir = self.tmpdir
        tmpdir_sandbox = self.tmpdir_sandbox
        tmpdir_production = self.tmpdir_production
        trials_loc = self.trials_loc
        sandbox_prefix = self.sandbox_prefix
        production_prefix = self.production_prefix
        bucket_name = self.bucket_name

        sandbox_rules = copy.deepcopy(PREP_RULE_SIMPLE_RSVP_SANDBOX)
        production_rules = copy.deepcopy(PREP_RULE_SIMPLE_RSVP_PRODUCTION)

        if self.set_destination:
            mongo_dbname = self.mongo_dbname
            collection_name = self.collection_name
            dst_rules = [
                {
                    'old': 'var dstDB = null;',
                    'new': 'var dstDB = "%s";' % mongo_dbname,
                    'n': 1
                },
                {
                    'old': 'var dstCollection = null;',
                    'new': 'var dstCollection = "%s";' % collection_name,
                    'n': 1
                },
            ]
            sandbox_rules.extend(dst_rules)
            production_rules.extend(dst_rules)

        if auxfns is not None:
            for auxfn in auxfns:
                auxroot = os.path.split(auxfn)[1]
                new_sandbox_rule = {
                'old': auxroot,
                'new': 'https://s3.amazonaws.com/' + bucket_name + '/' +
                        sandbox_prefix + '/' + auxroot,
                        }
                new_production_rule = {
                'old': auxroot,
                'new': 'https://s3.amazonaws.com/' + bucket_name + '/' +
                        production_prefix + '/' + auxroot,
                        }
                sandbox_rules.append(new_sandbox_rule)
                production_rules.append(new_production_rule)

        if self.additionalrules is not None:
            sandbox_rules.extend(self.additionalrules)
            production_rules.extend(self.additionalrules)

        if self.otherrules is not None:
            rulesets = []
            for label, ruleset in self.otherrules:
                srules = copy.deepcopy(sandbox_rules)
                srules.extend(ruleset)
                prules = copy.deepcopy(production_rules)
                prules.extend(ruleset)
                rulesets.append(('sandbox_%s' % label,
                    srules, tmpdir_sandbox, label))
                rulesets.append(('production_%s' % label,
                    prules, tmpdir_production, label))

        else:
            rulesets = [('sandbox', sandbox_rules, tmpdir_sandbox, None),
                        ('production', production_rules, tmpdir_production,
                            None)]

        self.base_URLs = []
        self.final_rules = []
        for label, rules, dstdir, pfix in rulesets:
            print ('  ->', label, pfix)
            new_urls = ut.prep_web_simple(trials, htmlsrc,
                    dstdir, dstpatt=htmldst,
                    rules=rules, auxfns=auxfns,
                    n_per_file=n_per_file, verbose=True,
                    chunkerfunc=chunkerfunc,
                    prefix=pfix)
            self.base_URLs += new_urls
            self.final_rules.extend([rules for _ind in range(len(new_urls))])

        assert len(self.final_rules) == len(self.base_URLs)
        self.final_rules = dict(zip(self.base_URLs, self.final_rules))
        # save trials for future reference
        pk.dump(trials, open(os.path.join(tmpdir, trials_loc), 'wb'))

    def testHTMLs(self):
        """Test and validates the written html files"""

        tmpdir = self.tmpdir
        tmpdir_sandbox = self.tmpdir_sandbox
        tmpdir_production = self.tmpdir_production
        trials_loc = self.trials_loc

        trials_org = pk.load(open(os.path.join(tmpdir, trials_loc)))

        fns_sandbox = sorted(glob.glob(os.path.join(
            tmpdir_sandbox, '*.html')))
        fns_production = sorted(glob.glob(os.path.join(
            tmpdir_production, '*.html')))

        print '* Testing sandbox...'
        ut.validate_html_files(fns_sandbox,
                ruledict=self.final_rules,
                trials_org=trials_org)
        print '* Testing production...'
        ut.validate_html_files(fns_production,
                ruledict=self.final_rules,
                trials_org=trials_org)

    def uploadHTMLs(self):
        tmpdir_sandbox = self.tmpdir_sandbox
        tmpdir_production = self.tmpdir_production
        sandbox_prefix = self.sandbox_prefix
        production_prefix = self.production_prefix
        bucket_name = self.bucket_name

        """Upload generated web files into S3"""
        print '* Uploading sandbox...'
        fns = glob.glob(os.path.join(tmpdir_sandbox, '*.*'))
        keys = upload_files(fns, bucket_name,
                dstprefix=sandbox_prefix + '/', test=True, verbose=10)

        print '* Uploading production...'
        fns = glob.glob(os.path.join(tmpdir_production, '*.*'))
        keys += upload_files(fns, bucket_name,
                dstprefix=production_prefix + '/', test=True, verbose=10)
        return keys

    def connect(self):
        """Establishes connection to MTurk for publishing HITs and getting
        data. Pass sandbox=True if you want to use sandbox mode.
        """
        if not self.sandbox:
            conn = MTurkConnection(aws_access_key_id=self.access_key_id,
                                   aws_secret_access_key=self.secretkey, )
        else:
            conn = MTurkConnection(aws_access_key_id=self.access_key_id,
                                   aws_secret_access_key=self.secretkey,
                                   host=MTURK_SANDBOX_HOST)
        return conn

    def setQual(self, performance_thresh=90):
        self.qual = create_qual(performance_thresh)
        if self.other_quals is not None:
            for q in self.other_quals:
                self.qual.add(q)

    def URLs(self, secure=False):
        """urls of actual tasks for createHITs
           prepHTMLs must be run first
        """
        sandbox_prefix = self.sandbox_prefix
        production_prefix = self.production_prefix
        bucket_name = self.bucket_name

        if self.sandbox:
            prefix = sandbox_prefix
        else:
            prefix = production_prefix

        if secure:
            urlbase = S3HTTPSBASE
        else:
            urlbase = S3HTTPBASE

        base_URLs = [fn.split('/')[-1] for fn in self.base_URLs]
        base_URLs = [b for (i, b) in enumerate(base_URLs)
                if b not in base_URLs[:i]]

        return [urlbase + bucket_name + '/' + prefix + '/' + b
                for b in base_URLs]

    def createHIT(self, URLlist=None, verbose=True, hitidslog=None,
                  secure=False, hits_per_url=1):
        """
        - Pass a list of URLs (check that they work first!) for each one to be
          published as a HIT. If you've used mturkutils to upload HTML, those
          (self.URLs) will be used by default.
        - This function returns a list of HIT IDs which can be used to collect
          data later. Those IDs are stored in 'self.hitids'.
        - The HITids are also stored in a pickle file saved to LOG_PREFIXi or,
          if given, `hitidslog`.
        """
        if URLlist is None:
            URLlist = self.URLs(secure=secure)

        URLlist = URLlist * hits_per_url

        if self.sandbox:
            print('**WORKING IN SANDBOX MODE**')

        conn = self.conn

        #Check if sufficient funds are available
        totalCost = (self.max_assignments * len(URLlist) * self.reward) * 1.10
        available_funds = self.getBalance()

        if totalCost > available_funds:
            print(
                'Insufficient funds available. You have $' +
                str(available_funds) +
                ' in the bank, but this experiment will cost $' +
                str(totalCost) +
                '. Aborting HIT creation.')
            return

        self.hitids = []
        for urlnum, url in enumerate(URLlist):
            q = ExternalQuestion(external_url=url,
                    frame_height=self.frame_height_pix)
            create_hit_rs = conn.create_hit(question=q, lifetime=self.lifetime,
                    max_assignments=self.max_assignments, title=self.title,
                    keywords=self.keywords, reward=self.reward,
                    duration=self.duration, approval_delay=self.approval_delay,
                    annotation=url, qualifications=self.qual,
                    description=self.description, response_groups=['Minimal',
                        'HITDetail', 'HITQuestion', 'HITAssignmentSummary'])

            for hit in create_hit_rs:
                self.hitids.append(hit.HITId)
                self.htypid = hit.HITTypeId
            assert create_hit_rs.status

            if verbose:
                print(str(urlnum) + ': ' + url + ', ' + self.hitids[-1])

        if hitidslog is None:
            prefix = 'sandbox' if self.sandbox else 'production'
            date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")
            file_string = self.log_prefix  + '_'.join([self.bucket_name, prefix,
                                    'hitids', str(self.htypid), date]) + '.pkl'
        else:
            file_string = hitidslog
        pk.dump(self.hitids, file(file_string, 'wb'))
        return self.hitids

    def disableHIT(self, hitids=None):
        """Disable published HITs"""
        if hitids is None:
            hitids = self.hitids
        for hitid in hitids:
            self.conn.disable_hit(hitid)

    def _updateDBcore(self, srcs, mode, **kwargs):
        """See the documentation of updateDBwithHITs() and
        updateDBwithHITslocal()"""
        coll = self.collection
        meta = self.meta

        if coll is None:
            print('**NO DB CONNECTION**')
            return

        if mode in ['files', 'pkls', 'csvs']:
            # make sure all the files exist.
            assert all([os.path.exists(src) for src in srcs])

        if self.sandbox:
            print('**WORKING IN SANDBOX MODE**')

        all_data = []
        for src in srcs:
            if mode == 'hitids':
                sdata = self.getHITdata(src, full=False)
            elif mode in ['files', 'pkls', 'csvs']:
                if mode == 'csvs' or (mode == 'files' and 'csv' in
                        src.lower()):
                    sdata = parse_human_data(src)
                else:
                    assgns, hd = pk.load(open(src))[:2]
                    sdata = parse_human_data_from_HITdata(assgns, HITdata=hd,
                            comment=self.comment, description=self.description,
                            full=False)
            else:
                raise ValueError('Invalid "mode".')

            update_mongodb_once(coll, sdata, meta,
                    **kwargs)
            all_data.extend(sdata)

        self.all_data = all_data
        return all_data

    def updateDBwithHITs(self, hitids, **kwargs):
        """
        - Takes a list of HIT IDs, gets data from MTurk, attaches metadata (if
          necessary) and puts results in dicarlo5 database.
        - Also stores data in object variable 'all_data' for immediate use.
          This might be dangerous for MH17's memory.
        - Even if you've already gotten some HITs, this will try to get them
          again anyway. Maybe later I'll fix this.
        - With `kwargs`, you can specify the followings:
          - verbose: show the progress of db update
          - overwrite: if True, the existing records will be overwritten.
        """
        return self._updateDBcore(hitids, 'hitids', **kwargs)

    def updateDBwithHITslocal(self, datafiles, mode='files', **kwargs):
        """
        - Takes data directly downloaded from MTurk in the form of csv or
          pickle files, attaches metadata (if necessary) and puts results in
          dicarlo2 database.
        - Also stores data in object variable 'all_data' for immediate use.
        - Even if you've already gotten some HITs, this will get them again
          anyway. Maybe later I'll fix this.
        - With `kwargs`, you can specify the followings:
          - verbose: show the progress of db update
          - overwrite: if True, the existing records will be overwritten.
        """
        return self._updateDBcore(datafiles, mode, **kwargs)

    def getHITdataraw(self, hitid, retry=5):
        """Get the human data as raw boto objects for the given `hitid`"""
        # NOTE: be extra careful when modify this function.
        # especially download_results() and cli.make_backup()
        # depends on this.  In short: avoid modification of this func
        # as much as possible, especially the returned data.

        try:
            assignments = self.conn.get_assignments(hit_id=hitid,
                    page_size=min(self.max_assignments, MTURK_PAGE_SIZE_LIMIT))
            HITdata = self.conn.get_hit(hit_id=hitid)
        except Exception as e:
            if retry == 0:
                raise e
            from time import sleep
            sleep(5)
            assignments, HITdata = self.getHITdataraw(hitid, retry=retry - 1)

        return assignments, HITdata

    def getHITdata(self, hitid, verbose=True, full=False):
        assignments, HITdata = self.getHITdataraw(hitid)
        return parse_human_data_from_HITdata(assignments, HITdata,
                    comment=self.comment, description=self.description,
                    full=full, verbose=verbose)


class MatchToSampleFromDLDataExperiment(Experiment):
    """
    Creates an experiment with the given ``html_data``.  Although the class
    name implies use of an dldata object, it is possible to pass ``meta`` and
    ``urls`` directly and skip dependency to dldata altogether (see example
    experiment "objectome_cars_subord" for details).
    """

    def createTrials(self, sampling='without-replacement', verbose=0):
        """
        - Create trials with the given ``html_data``.
        Html data is a spec that can have the following parameters:
        :param dummy_upload: If true, image files are assumed to have been uploaded previouls
        :param preproc: what preproc to use on images
            (see dldata.stimulus_sets.dataset_templates.ImageLoaderPreprocesser)
        :param image_bucket_name: what bucket to upload files to
        :param seed: random seed to use for shuffling
        :param dataset: which dataset to get images from
        :param combs: List of tuples of synsets to measure confusions for
        :param k: Number of times to measure each confusion.
        :param meta_query: subset the dataset according to this query, evaluated once at every meta entry
        sampled equally
        :param: labelfunc: callable that takes a dictionary meta entry and the dataset, and returns the label to be
            printed
        :param: response_images: list of
            tuple of image_urls, imgData, and labels to use for response images. There must be one set
             of responses per confusion to be measured. If this is not
                set, random images from the same category are used by default.
        :param shuffle_test: whether to shuffle order of presentatino of test images
        - Parameter ``sampling`` determines the behavior of image sampling:
          * "without-replacement" (default): no same images will be presented
            across the entire population of subjects.
          * "with-replacement": allows recycling of images.

        """

        assert sampling in ['without-replacement', 'with-replacement']
        html_data = self.html_data

        dataset = html_data.get('dataset')
        preproc = html_data.get('preproc')
        meta_query = html_data.get('meta_query')
        meta_field = html_data.get('meta_field', 'category')
        k = html_data['num_trials']
        response_images = html_data.get('response_images')
        dummy_upload = html_data.get('dummy_upload', True)
        image_bucket_name = html_data.get('image_bucket_name')
        combs = html_data['combs']
        labelfunc = html_data.get('labelfunc')
        seed = html_data.get('seed', 0)  # no need to change most cases
        urls = html_data.get('urls')
        meta = html_data.get('meta')
        shuffle_test = html_data.get('shuffle_test', False)

        if meta is None:
            if dataset is None:
                raise ValueError('Either "meta" or "dataset" '
                        'must be defined')
            meta = dataset.meta

        if meta_query is not None:
            query_inds = set(np.ravel(np.argwhere(map(meta_query, meta))))
        else:
            query_inds = set(range(len(meta)))

        category_occurences = Counter(itertools.chain.from_iterable(combs))
        synset_urls = defaultdict(list)
        img_inds = []
        imgData = []
        n = len(list(combs[0]))
        category_meta_dicts = defaultdict(list)
        if response_images is None:
            num_per_category = int(np.ceil(float(k) / n) * (n + 1))
            response_images = [None] * len(combs)
        else:
            num_per_category = int(np.ceil(float(k) / n))

        rng = np.random.RandomState(seed=seed)
        for category in category_occurences.keys():
            cat_inds = set(np.ravel(np.argwhere(meta[meta_field] == category)))
            inds = list(query_inds & cat_inds)
            num_sample = category_occurences[category] * num_per_category

            if sampling == 'without-replacement':
                if len(inds) < num_sample:
                    raise ValueError(("Category %s has %d images, "
                            "%d are required for this experiment") %
                            (category, len(inds), num_sample))
                img_inds.extend(list(
                    np.array(inds)[rng.permutation(len(inds))[:num_sample]]))

            elif sampling == 'with-replacement':
                img_inds.extend(list(
                    np.array(inds)[rng.randint(len(inds), size=num_sample)]))

            else:
                raise ValueError('Invalid "sampling"')

        if urls is None:
            assert image_bucket_name is not None
            urls = dataset.publish_images(img_inds, preproc,
                    image_bucket_name, dummy_upload=dummy_upload)
        else:
            assert len(meta) == len(urls)
            urls = np.array(urls)[img_inds]
        assert len(urls) == len(img_inds)

        if verbose > 0:
            print '** n =', n
            print '** k =', k
            print '** num_per_category =', num_per_category
            print '** num_sample =', num_sample
            print '** len(urls) =', len(urls)
            print '** len(meta) =', len(meta)
        if verbose > 1:
            print '** category_occurences =', category_occurences

        for url, img_ind in zip(urls, img_inds):
            meta_entry = meta[img_ind]
            category = meta_entry[meta_field]
            synset_urls[category].append(url)
            meta_dict = {name: value for name, value in
                         zip(meta_entry.dtype.names, meta_entry.tolist())}
            category_meta_dicts[category].append(meta_dict)
        imgs = []
        labels = []
        for c, ri in zip(combs, response_images):
            #We cycle through the possible sample categories one by one.
            for _rep in np.arange(np.ceil(float(k) / n)):
                for sample_synset in c:
                    rng = np.random.RandomState(seed=(seed, _rep))
                    sample = synset_urls[sample_synset].pop()
                    sample_meta = category_meta_dicts[sample_synset].pop()

                    if ri is None:
                        test = [synset_urls[s].pop() for s in c]
                        test_meta = [category_meta_dicts[s].pop() for s in c]
                        if labelfunc is None:
                            lbls = [''] * len(test_meta)
                        else:
                            lbls = [labelfunc(meta_dict, dataset)
                                for meta_dict in test_meta]
                    else:
                        test = ri['urls']
                        test_meta = ri['meta']
                        lbls = ri['labels']

                    si = range(len(lbls))
                    assert len(si) == len(test) == len(test_meta)
                    if shuffle_test:
                        rng.shuffle(si)

                    # write down one prepared trial
                    imgs.append([sample, [test[e] for e in si]])
                    imgData.append({
                        "Sample": sample_meta,
                        "Test": [test_meta[e] for e in si]})
                    labels.append([lbls[e] for e in si])

        for list_data in [imgs, imgData, labels]:
            rng = np.random.RandomState(seed=seed)
            rng.shuffle(list_data)

        if verbose > 0:
            print '** max len in left synset_urls =', \
                    sorted([(len(synset_urls[e]), e)
                        for e in synset_urls])[-1]
            print '** max len in left category_meta_dicts =', \
                    sorted([(len(category_meta_dicts[e]), e)
                            for e in category_meta_dicts])[-1]
        if verbose > 1:
            print '** len for each in left synset_urls =', \
                    {e: len(synset_urls[e]) for e in synset_urls}
            print '** len for each in left category_meta_dicts =', \
                    {e: len(category_meta_dicts[e])
                            for e in category_meta_dicts}
        if verbose > 2:
            print '** synset_urls =', synset_urls
            print '** category_meta_dicts =', category_meta_dicts

        self._trials = {'imgFiles': imgs, 'imgData': imgData, 'labels': labels,
                               'meta_field': [meta_field] * len(labels)}


class MatchToSampleFromDLDataExperimentWithTiming(
        MatchToSampleFromDLDataExperiment):

    def createTrials(self, presentation_time=None, **kwargs):
        if presentation_time is None:
            presentation_time = self.presentation_time
        MatchToSampleFromDLDataExperiment.createTrials(self, **kwargs)
        N = len(self._trials['imgFiles'])
        self._trials['stimduration'] = [presentation_time] * N


class MatchToSampleFromDLDataExperimentWithReward(
        MatchToSampleFromDLDataExperiment):

        def createTrials(self, **kwargs):
            MatchToSampleFromDLDataExperiment.createTrials(self, **kwargs)
            html_data = self.html_data
            combs = html_data['combs']
            acc = np.linspace(0, 1, 100)
            n = float(len(combs[0]))
            print n
            fudged_hr = (acc / n) / (1 / n)
            fudged_fa = ((1 / n) - acc / n) / (1 - 1 / n)
            fudged_hr[0] = 1. / (2 * 100)
            fudged_fa[0] = 1 - 1. / (2 * 100)
            fudged_fa[-1] = 1. / (2 * 100)
            fudged_hr[-1] = 1 - 1. / (2 * 100)
            dprime = stats.norm.ppf(fudged_hr) - stats.norm.ppf(fudged_fa)
            reward = dprime
            reward[reward < 0] = 0
            reward_scale = html_data['reward_scale']
            reward = list(reward / max(reward) * reward_scale)
            self._trials['reward_scale'] = \
                [reward] * len(self._trials['imgFiles'])


# -- helper functions
def parse_credentials_file(path=None, section_name='Credentials'):
    if path is None:
        path = BOTO_CRED_FILE
    config = Config(path)
    assert config.has_section(section_name), \
        'Field ' + section_name + \
        ' not found in credentials file located at ' + path
    return config.get(section_name, 'aws_access_key_id'), \
            config.get(section_name, 'aws_secret_access_key')


def create_qual(performance_thresh=90):
    """Returns an MTurk Qualification object which can then be passed to
    a HIT object. For now, I've only implemented a prior HIT approval
    qualification, but boto supports many more.
    """
    performance_thresh = int(performance_thresh)
    req = PercentAssignmentsApprovedRequirement(comparator='GreaterThan',
            integer_value=performance_thresh)
    qual = Qualifications()
    qual.add(req)
    return qual


def parse_human_data(datafile):
    warn('Use of parse_human_data() is deprecated.')
    csv.field_size_limit(10000000000)
    count = 0
    with open(datafile, 'rb+') as csvfile:

        datareader = csv.reader(csvfile, delimiter='\t')
        subj_data = []
        for row in datareader:
            if count == 0 and len(row) > 0 and row[0] == 'hitid':
                count += 1
                # column_labels = row

            else:
                try:
                    subj_data.append(json.loads(row[-1][1:-1]))
                except ValueError:
                #   print(row[-1])
                    continue
                subj_data[-1]['HITid'] = row[0]
                subj_data[-1]['Title'] = row[2]
                subj_data[-1]['Reward'] = row[5]
                subj_data[-1]['URL'] = row[13]
                subj_data[-1]['Duration'] = row[14]
                subj_data[-1]['ViewHIT'] = row[17]
                subj_data[-1]['AssignmentID'] = row[18]
                subj_data[-1]['WorkerID'] = row[19]
                subj_data[-1]['Timestamp'] = row[23]

        csvfile.close()
    return subj_data


def parse_human_data_from_HITdata(assignments, HITdata=None, comment='',
        description='', full=False, verbose=False):
    """Parse human response data from boto HIT data objects.  This only
    supports external questions for now"""
    fields = ['HITid', 'Title', 'Reward', 'URL', 'Duration', 'HITTypeID',
            'Keywords', 'CreationTime', 'Qualification']

    if HITdata is None:
        HITdata = {}

    # -- sanitize HITdata
    hitdat = {}   # sanitized HITdata
    if isinstance(HITdata, dict):
        for field in zip(fields):
            hitdat[field] = HITdata.get(field)
    elif isinstance(HITdata, (list, boto.resultset.ResultSet)):
        # list of boto.mturk.connection.HIT
        assert len(HITdata) == 1
        h = HITdata[0]
        assert isinstance(h, boto.mturk.connection.HIT)

        # this MUST match the order of `fields` above.
        attrs = ['HITId', 'Title', 'FormattedPrice', 'RequesterAnnotation',
                'AssignmentDurationInSeconds', 'HITTypeId', 'Keywords',
                'CreationTime', ('QualificationTypeId', 'IntegerValue',
                    'Comparator')]
        assert len(fields) == len(attrs)

        for field, attr in zip(fields, attrs):
            if type(attr) is not tuple:
                # regular attribs
                hitdat[field] = getattr(h, attr)
            else:
                hd = {}
                try:
                    # Should see how this code works for
                    # multiple qual types.
                    for ae in attr:
                        hd[ae] = getattr(h, ae)
                    hitdat[field] = hd
                except AttributeError:
                    continue
    else:
        raise ValueError('Unknown type of HITdata')

    # -- get all assignments
    subj_data = []
    for a in assignments:
        try:
            if verbose:
                print a.WorkerId
            assert len(a.answers) == 1      # must be
            assert len(a.answers[0]) == 1   # multiple ans not supported
            qfa = a.answers[0][0]
            assert len(qfa.fields) == 1     # must be...?
            ansdat = json.loads(qfa.fields[0])
            assert len(ansdat) == 1, \
                    len(ansdat)             # only this format is supported
            ansdat = ansdat[0]
            if 'Response' in ansdat:
                if hasattr(ansdat['Response'][0], '__iter__'):
                    for _r in ansdat['Response']:
                        if '_id' in _r and '$oid' in _r['_id']:
                            _r['_id'] = _r['_id']['$oid']
            ansdat['AssignmentID'] = a.AssignmentId
            ansdat['WorkerID'] = a.WorkerId
            ansdat['Timestamp'] = a.SubmitTime
            ansdat['AcceptTime'] = a.AcceptTime
            ansdat['Comment'] = comment
            ansdat['Description'] = description
            ansdat.update(hitdat)
            subj_data.append(ansdat)
        except ValueError:
            print('Error in decoding JSON data. Skipping for now...')
            continue

    if full:
        return subj_data, hitdat
    return subj_data


def update_mongodb_once(coll, subj_data, meta, verbose=False, overwrite=False):
    """Update mongodb with the human data for a single HIT

    Parameters
    ----------
    coll : string
        Name of mongodb collection
    subj_data : list
        Human data for a single HIT.  This must be `subj_data` returned from
        `parse_human_data_from_HITdata()` (or `parse_human_data()`, although
        this is outdataed) and can contain multiple subjects.
    meta : dict or tabarray
        The object that contains the stimuli information.
    verbose : bool
        If True (False by default), show the progress.
    overwrite : bool
        If True (False by default), the contents in the database will be
        overwritten.
    """
    if coll is None:
        raise ValueError('`coll` is `None`: no db connection?')

    coll.ensure_index([
        ('WorkerID', pymongo.ASCENDING),
        ('Timestamp', pymongo.ASCENDING)],
        unique=True)

    for subj in subj_data:
        assert isinstance(subj, dict)
        try:
            doc_id = coll.insert_one(subj)
        except pymongo.errors.DuplicateKeyError:
            if not overwrite:
                warn('Entry already exists, moving to next...')
                continue
            if 'WorkerID' not in subj or 'Timestamp' not in subj:
                warn("No WorkerID or Timestamp in the subject's "
                        "record: invalid HIT data?")
                continue
            spec = {'WorkerID': subj['WorkerID'],
                    'Timestamp': subj['Timestamp']}
            doc = coll.find_one(spec)
            assert doc is not None
            doc_id = doc['_id']
            if '_id' in subj:
                _id = subj.pop('_id')
                if verbose and str(_id) not in str(doc_id) \
                        and str(doc_id) not in str(_id):
                    print 'Dangling _id:', _id
            coll.update({'_id': doc_id}, {
                '$set': subj
                }, w=0)

        if verbose:
            print 'Added:', doc_id

        if meta is None:
            continue

        # handle ImgData
        m = [search_meta(getidfromURL(e), meta) for e in subj['StimShown']]
        coll.update({'_id': doc_id}, {
            '$set': {'ImgData': m}
            }, w=0)


def search_meta(needles, meta, lookup_field=LOOKUP_FIELD):
    """Search `needles` in `meta` and returns the corresponding records.
    This replaces old `get_meta()` and `get_meta_fromtabarray()`."""
    single = False
    if isinstance(needles, (str, unicode)):
        single = True
        needles = [needles]

    dat = []
    if isinstance(meta, dict):
        # this should be much faster!
        for n in needles:
            dat.append(meta[n])
    else:
        # Assuming meta is a tabarray
        for n in needles:
            si = meta[lookup_field] == n
            assert np.sum(si) == 1         # must unique
            meta0 = convertTabArrayToDict(meta[si])
            dat.append(meta0[n])

    return dat if not single else dat[0]


def getidfromURL(urls):
    """Extract the id from the URL or list of URLs"""
    single = False
    if not isinstance(urls, list):
        single = True
        urls = [urls]

    ids = [urllib.url2pathname(u).split('/')[-1].split('.')[0] for u in urls]
    return ids if not single else ids[0]


def convertTabArrayToDict(meta_tabarray, lookup_field=LOOKUP_FIELD):
    meta_dict = {}
    for m in meta_tabarray:
        meta_dict[m[lookup_field]] = SONify(dict(zip(meta_tabarray.dtype.names,
            m)))
    return meta_dict


def updateGeoData(collect):
    conn = pymongo.MongoClient(port=MONGO_PORT, host=MONGO_HOST)
    db = conn.mturk
    col = db[collect]

    workers_seen = {}
    for c in col.find():
        if c.get('countryName') is not None:
            continue
        else:
            if workers_seen.get(c['WorkerID']) is not None:
                col.update({'_id': c['_id']},
                        {'$set': workers_seen[c['WorkerID']]}, w=0)
                #print('Worker already seen, updating entry...')
            else:
                #worker not already seen, get data from API
                response = json.loads(urllib.urlopen(
                    IPINFODB_PATT % str(c['IPaddress'])).read())
                workers_seen[c['WorkerID']] = response
                col.update({'_id': c['_id']},
                        {'$set': workers_seen[c['WorkerID']]}, w=0)
                print(str(c['WorkerID']) + ': ' +
                        str(response['countryName']))


def SONify(arg, memo=None):
    if memo is None:
        memo = {}
    if id(arg) in memo:
        rval = memo[id(arg)]
    if isinstance(arg, ObjectId):
        rval = arg
    elif isinstance(arg, datetime.datetime):
        rval = arg
    elif isinstance(arg, np.floating):
        rval = float(arg)
    elif isinstance(arg, np.integer):
        rval = int(arg)
    elif isinstance(arg, (list, tuple)):
        rval = type(arg)([SONify(ai, memo) for ai in arg])
    elif isinstance(arg, collections.OrderedDict):
        rval = collections.OrderedDict([(SONify(k, memo), SONify(v, memo))
            for k, v in arg.items()])
    elif isinstance(arg, dict):
        rval = dict([(SONify(k, memo), SONify(v, memo))
            for k, v in arg.items()])
    elif isinstance(arg, (basestring, float, int, type(None))):
        rval = arg
    elif isinstance(arg, np.ndarray):
        if arg.ndim == 0:
            rval = SONify(arg.sum())
        else:
            rval = map(SONify, arg)  # N.B. memo None
    # -- put this after ndarray because ndarray not hashable
    elif arg in (True, False):
        rval = int(arg)
    else:
        raise TypeError('SONify', arg)
    memo[id(rval)] = rval
    return rval


def upload_files(srcfiles, bucketname, dstprefix='',
        section_name=MTURK_CRED_SECTION, test=True, verbose=False,
        accesskey=None, secretkey=None, dstfiles=None, acl='public-read'):
    """Upload multiple files into a S3 bucket"""
    # -- establish connections
    _, bucket = connect_s3(section_name=section_name, accesskey=accesskey,
            secretkey=secretkey, bucketname=bucketname, createbucket=True)

    if dstfiles is None:
        dstfiles = [None] * len(srcfiles)

    # -- upload files
    keys = []
    for i_fn, (fn, dfn) in enumerate(zip(srcfiles, dstfiles)):
        if dfn is None:
            dfn = fn
        # upload
        key_dst = dstprefix + os.path.basename(dfn)
        k = Key(bucket)
        k.key = key_dst
        k.set_contents_from_filename(fn)
        k.close()
        if acl is not None:
            bucket.set_acl(acl, key_dst)

        # download and check... although this is a bit redundant
        if test:
            k = Key(bucket)
            k.key = key_dst
            s = k.get_contents_as_string()
            k.close()
            assert s == open(fn).read()
        keys.append(k)

        if verbose and i_fn % verbose == 0:
            print 'At:', i_fn, 'out of', len(srcfiles)

    return keys


def download_results(hitids, dstprefix=None, sandbox=True,
        replstr='${HIT_ID}', verbose=False, full=False):
    """Download all assignment results in `hittids` and save one pickle file
    per HIT with `dstprefix` if it is not `None`.  If `dstprefix` is `None`,
    the downloaded info will be returned without saving files."""
    exp = Experiment(None, None, sandbox=sandbox,
        max_assignments=MTURK_PAGE_SIZE_LIMIT,
        reward=0.,
        collection_name=None,   # disables db connection
        meta=None,
        )

    res = []
    n_total = len(hitids)
    n_hits = 0
    n_assgns = 0
    meta = {'boto_version': boto.__version__,
            'backup_algo_version': BACKUP_ALGO_VER}

    for hitid in hitids:
        if verbose:
            print 'At (%d/%d):' % (n_hits + 1, n_total), hitid

        assignments, HITdata = exp.getHITdataraw(hitid)
        n_hits += 1
        n_assgns += len(assignments)

        if dstprefix is None:
            res.append((assignments, HITdata))
            continue

        # save files otherwise
        if replstr in dstprefix:
            dst = dstprefix.replace(replstr, str(hitid))
        else:
            dst = dstprefix + str(hitid) + '.pkl'
        pk.dump((assignments, HITdata, meta), open(dst, 'wb'))

    if full:
        return res, n_hits, n_assgns
    if dstprefix is None:
        return res


def connect_s3(section_name=MTURK_CRED_SECTION, accesskey=None,
        secretkey=None, bucketname=None, createbucket=False):
    """Get a S3 connection"""
    if accesskey is None or secretkey is None:
        accesskey, secretkey = \
                parse_credentials_file(section_name=section_name)

    # -- establish connections
    try:
        conn = S3Connection(accesskey, secretkey)
    except boto.exception.S3ResponseError:
        raise ValueError('Could not establish an S3 conection. '
                'Is your account properly configured?')

    if bucketname is not None:
        try:
            bucket = conn.get_bucket(bucketname)
        except boto.exception.S3ResponseError:
            print('Bucket does not exist.')
            bucket = None
            if createbucket:
                print('Creating a new bucket...')
                bucket = conn.create_bucket(bucketname)
        return conn, bucket
    return conn


def exists_s3(bucketname_or_bucket, keyname, section_name=MTURK_CRED_SECTION,
        accesskey=None, secretkey=None):
    """Check whether a key is in the bucket"""
    if isinstance(bucketname_or_bucket, (str, unicode)):
        # -- establish connections
        _, bucket = connect_s3(section_name=section_name, accesskey=accesskey,
                secretkey=secretkey, bucketname=bucketname_or_bucket)
    else:
        bucket = bucketname_or_bucket

    if bucket is None:
        return

    k = Key(bucket)
    k.key = keyname
    return k.exists()
