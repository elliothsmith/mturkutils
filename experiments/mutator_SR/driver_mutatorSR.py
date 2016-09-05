#!/usr/bin/env python
import numpy as np
import cPickle as pk
import tabular as tb
import itertools
import copy
import sys
import dldata.stimulus_sets.hvm as hvm
from mturkutils.base import MatchToSampleFromDLDataExperiment
from os import path
import json
REPEATS_PER_QE_IMG = 4 # Number of times to repeat select images, for "Quality Estimation" purposes
ACTUAL_TRIALS_PER_HIT = 140 # Number of experimental trials, without repeat images. And without tutorial trials.

def get_url_labeled_resp_img(cat):
    # Get canonical response image for this 'category' cat.
    base_url = 'https://s3.amazonaws.com/mutatorsr/resources/response_images/'
    return base_url+ cat+ '.png'


def get_exp(sandbox=True, debug=True, dummy_upload=True):
    dataset = hvm.HvMWithDiscfade() # Pull urls and meta from this dldata dataset.
    meta = dataset.meta # Load meta.
    response_images = []
    categories = ['Animals', 'Boats', 'Cars', 'Chairs'] #np.unique(meta['category']) # The categories for this experiment are the ones in meta.
    cat_combs= [('Animals', 'Boats', 'Cars', 'Chairs')] #[e for e in itertools.combinations(categories, 4)] # Get every possible pairing of categories; these are the confusions to be measured.
    response_images.extend([{
    'urls': [get_url_labeled_resp_img(c1), get_url_labeled_resp_img(c2), get_url_labeled_resp_img(c3), get_url_labeled_resp_img(c4)],
    'meta': [{'category': category} for category in [c1, c2, c3, c4]],
    'labels': [c1, c2, c3, c4]
    } for c1, c2, c3, c4 in cat_combs]) # List of dicts for response images information; one entry (a dict)_ for each confusion to be measured.
    combs = cat_combs

    urls = dataset.publish_images(range(len(dataset.meta)), None, 'hvm_timing', # dldata method that uploads to s3 the images, in their own bucket.
                                      dummy_upload=dummy_upload)

    with open(path.join(path.dirname(__file__), 'tutorial_html_basic'), 'r') as tutorial_html_file:
        tutorial_html = tutorial_html_file.read()
    label_func = lambda x: hvm.OBJECT_NAMES[x['obj']]
    html_data = {
        'combs': combs,
        'response_images': response_images,
        'num_trials': 125 * 2, # "Number of times to measure each confusion." I think this means total times over the population
        'meta_field': 'category',
        'meta': meta,
        'urls': urls,
        'shuffle_test': False, # Shuffle position of test images or no?
        'meta_query' : lambda x: x['var'] == 'V6',
        'label_func': label_func
    }
    cat_dict = {'Animals': 'Animal', 'Boats': 'Boat', 'Cars': 'Car',
               'Chairs': 'Chair'}#, 'Faces': 'Face', 'Fruits': 'Fruit',
               #'Planes': 'Plane', 'Tables': 'Table'}

    additionalrules = [{'old': 'LEARNINGPERIODNUMBER',
                        'new':  str(10)},
                       {'old': 'OBJTYPE',
                        'new': 'Object Recognition'},
                       {'old': 'TUTORIAL_HTML',
                        'new': tutorial_html},
                       {'old': 'CATDICT',
                        'new': json.dumps(cat_dict)},
                       {'old': 'METAFIELD',
                        'new': "'category'"}]

    exp = MatchToSampleFromDLDataExperiment(
            htmlsrc='web/general_mutatorSR.html',
            htmldst='hvm_mutatorSR_n%05d.html',
            sandbox=sandbox,
            title='Visual object learning --- match strange objects to hieroglyphs',
            reward=0.25,
            duration=1600,
            keywords=['neuroscience', 'psychology', 'experiment', 'object recognition'],  # noqa
            description="***You may complete as many HITs in this group as you want*** Complete a visual object recognition task where you report the identity of objects you see. We expect this HIT to take about 10 minutes or less, though you must finish in under 25 minutes.  By completing this HIT, you understand that you are participating in an experiment for the Massachusetts Institute of Technology (MIT) Department of Brain and Cognitive Sciences. You may quit at any time, and you will remain anonymous. Contact the requester with questions or concerns about this experiment.",  # noqa
            comment='mutatorSR',
            collection_name= None,#'hvm_basic_2ways', # name of MongoDB db to update / create on dicarlo5. Safe to change?
            max_assignments=1, # how many unique workers can complete a particular hit.
            bucket_name='hvm_2ways', # Refers to amazon; either mturk or s3 service (I'm not sure.) on which to store htmls. not safe to change before uploading source to bucket
            trials_per_hit= ACTUAL_TRIALS_PER_HIT, #+ 24,  # ACTUAL_TRIALS_PER_HIT + (6xREPEATS_PER_QE_IMG) repeats
            html_data=html_data,
            tmpdir='tmp',
            frame_height_pix=1200,
            othersrc=['../../lib/dltk.js', '../../lib/dltkexpr.js', '../../lib/dltkrsvp.js'],
            additionalrules=additionalrules
            )

    # -- create trials
    exp.createTrials(sampling='with-replacement', verbose=1)
    n_total_trials = len(exp._trials['imgFiles'])
    print n_total_trials
   # assert n_total_trials == (70) * 250 # Number of confusions * number of times each confusion is to be measured html_data['num_trials']
    if debug:
        return exp, html_data

    # -- in each HIT, the followings will be repeated 4 times to
    # estimate "quality" of data
    ind_repeats = [] #[0, 4, 47, 9, 17, 18] * REPEATS_PER_QE_IMG
    rng = np.random.RandomState(0)
    rng.shuffle(ind_repeats)
    trials_qe = {e: [copy.deepcopy(exp._trials[e][r]) for r in ind_repeats]
                 for e in exp._trials}

    # -- flip answer choices of some repeated images
    n_qe = len(trials_qe['labels'])
    # if True, flip
    flips = [True] * (n_qe / 2) + [False] * (n_qe - n_qe / 2)
    assert len(flips) == n_qe
    rng.shuffle(flips)
    assert len(trials_qe.keys()) == 4

    for i, flip in enumerate(flips):
        if not flip:
            continue
        trials_qe['imgFiles'][i][1].reverse()
        trials_qe['labels'][i].reverse()
        trials_qe['imgData'][i]['Test'].reverse()

    # -- actual application
    offsets = np.arange(
        ACTUAL_TRIALS_PER_HIT - 3, -1,
        -ACTUAL_TRIALS_PER_HIT / float(len(ind_repeats))
    ).round().astype('int')
    assert len(offsets) == len(offsets)

    n_hits_floor = n_total_trials / ACTUAL_TRIALS_PER_HIT
    n_applied_hits = 0
    for i_trial_begin in xrange((n_hits_floor - 1) * ACTUAL_TRIALS_PER_HIT,
                                -1, -ACTUAL_TRIALS_PER_HIT):
        for k in trials_qe:
            for i, offset in enumerate(offsets):
                exp._trials[k].insert(i_trial_begin + offset, trials_qe[k][i])
                # exp._trials[k].insert(i_trial_begin + offset, 'test')
        n_applied_hits += 1

    print '** n_applied_hits =', n_applied_hits
    print '** len for each in _trials =', \
        {e: len(exp._trials[e]) for e in exp._trials}

    # -- sanity check
    assert 50 == n_applied_hits, n_applied_hits
    assert len(exp._trials['imgFiles']) == 50 * 164
    s_ref_labels = [tuple(e) for e in trials_qe['labels']]
    offsets2 = np.arange(24)[::-1] + offsets
    ibie = zip(range(0, 50 * 164, 164), range(164, 50 * 164, 164))
    assert all(
        [[(e1, e2) for e1, e2 in
         np.array(exp._trials['labels'][ib:ie])[offsets2]] == s_ref_labels
         for ib, ie in ibie])

    # -- drop unneeded, potentially abusable stuffs
    #del exp._trials['imgData']
    print '** Finished creating trials.'

    return exp, html_data


def main(argv=[], partial=True, debug=True):
    sandbox = True
    if len(argv) > 1 and argv[1] == 'production':
        sandbox = False
        print '** Creating production HITs'
    else:
        print '** Sandbox mode'
        print '** Enter "driver.py production" to publish production HITs.'

    exp = get_exp(sandbox=sandbox, debug=debug)[0]
    exp.prepHTMLs()
    print '** Done prepping htmls.'
    if partial:
        return exp

    exp.testHTMLs()
    print '** Done testing htmls.'
    exp.uploadHTMLs()
    exp.createHIT(secure=True)
    return exp


if __name__ == '__main__':
    main(sys.argv)
