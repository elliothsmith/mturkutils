#!/usr/bin/env python
import numpy as np
import cPickle as pk
import tabular as tb
import itertools
import copy
from yamutils import fast
import sys
import dldata.stimulus_sets.freiwald_tsao as ft
from mturkutils.base import Experiment



def get_repeats_practices(meta, good_ids, seed):
    perm = np.random.RandomState(seed=seed).permutation(len(meta))
    meta0 = meta[perm]

    repeat_inds = []
    r_ind = 0
    for ident in good_ids:
        _inds = (meta0['identity'] == ident).nonzero()[0]
        r_ind_l = r_ind % len(_inds)
        repeat_inds.append(_inds[r_ind_l])
        r_ind += 1

    repeat_inds = fast.isin(meta['id'], meta0[repeat_inds]['id']).nonzero()[0]

    practice_inds = []
    r_ind = 1
    for ident in good_ids:
        _inds = (meta0['identity'] == ident).nonzero()[0]
        r_ind_l = r_ind % len(_inds)
        practice_inds.append(_inds[r_ind_l])
        r_ind += 1

    practice_inds = fast.isin(meta['id'], meta0[practice_inds]['id']).nonzero()[0]

    return repeat_inds, practice_inds


class MatchToSampleExperiment(Experiment):

    def createTrials(self, dummy_upload=True):

        mult = self.html_data['mult']

        dataset = ft.FreiwaldTsao2010()
        meta = dataset.meta
        inds = ((meta['identity'] != 8) & (meta['identity'] != 22)  & (meta['identity'] != 27)).nonzero()[0]
        meta = meta[inds]

        good_ids = list(np.unique(meta['identity']))

        preproc = dataset.default_preproc
        image_bucket_name = 'freiwald_tsao_2010'
        urls = dataset.publish_images(inds, preproc,
                                  image_bucket_name,
                                  dummy_upload=dummy_upload)


        #imgFiles, labels, meta_field, imgData
        canon_url = 'https://canonical_images.s3.amazonaws.com/'
        resp = [canon_url + 'freiwald_tsao_2010_face%.2da.png' % i for i in good_ids]

        self._trials = {'imgFiles': [], 'labels': [], 'meta_field': [], 'imgData': []}

        fields = ['id', 'identity', 'pose']
        for i in range(mult):
            trials = {}
            pracs = {}
            reps = {}

            rep_inds, prac_inds = get_repeats_practices(meta, good_ids, i)

            perm = np.random.RandomState(seed=i).permutation(len(urls))
            ulist = [urls[p] for p in perm]
            trials['imgFiles'] = [[u, resp]  for u in ulist]
            trials['labels'] = [good_ids[:]] * len(urls)
            trials['meta_field'] = ['identity'] * len(urls)
            trials['imgData'] = [{'Sample': {k: meta[p][k] for k in fields},
                                  'Test': [{'identity': i} for i in good_ids]} for p in perm]

            prac_urls = [urls[_p] for _p in prac_inds]
            pracs['imgFiles'] = [[u, resp] for u in prac_urls]
            pracs['labels'] = [good_ids[:]] * len(prac_inds)
            pracs['meta_field'] = ['identity'] * len(prac_inds)
            pracs['imgData'] = [{'Sample': {k: meta[_p][k] for k in fields},
                                'Test': [{'identity': i} for i in good_ids]} for _p in prac_inds]

            rep_urls = [urls[_p] for _p in rep_inds]
            reps['imgFiles'] = [[u, resp] for u in rep_urls]
            reps['labels'] = [good_ids[:]] * len(rep_inds)
            reps['meta_field'] = ['identity'] * len(rep_inds)
            reps['imgData'] = [{'Sample': {k: meta[_p][k] for k in fields},
                                'Test': [{'identity': i} for i in good_ids]} for _p in rep_inds]

            rep_sched = np.random.RandomState(seed=i).permutation(len(trials['imgFiles']))[: len(rep_inds)]
            rep_sched.sort()
            rep_sched_list = [(0, rep_sched[0])] + zip(rep_sched[:-1], rep_sched[1:]) + [(rep_sched[-1], len(trials['imgFiles']))]

            new_trials = {}
            for k in ['imgFiles', 'labels', 'meta_field', 'imgData']:
                new_trials[k] = pracs[k][:]
                for _rind in range(len(rep_urls)):
                    rs1, rs2 = rep_sched_list[_rind]
                    new_trials[k].extend(trials[k][rs1: rs2])
                    new_trials[k].append(reps[k][_rind])
                rs1, rs2 = rep_sched_list[-1]
                new_trials[k].extend(trials[k][rs1:rs2])
                self._trials[k].extend(new_trials[k])


def get_exp(sandbox=True, dummy_upload=True):


    additionalrules = [{'old': 'LEARNINGPERIODNUMBER',
                        'new':  str(25)}]

    trials_per_hit = 250
    mult = 1
    html_data = {'mult': mult}

    exp = MatchToSampleExperiment(
            htmlsrc='ft_identity2.html',
            htmldst='ft_identity2_n%05d.html',
            tmpdir='tmp_ft_identity',
            sandbox=sandbox,
            title='Face recognition --- report what you see',
            reward=0.40,
            duration=1500,
            keywords=['neuroscience', 'psychology', 'experiment', 'object recognition'],
            description="***You may complete as many HITs in this group as you want*** Complete a visual object recognition task where you report the identity of objects you see. We expect this HIT to take about 10 minutes or less, though you must finish in under 25 minutes.  By completing this HIT, you understand that you are participating in an experiment for the Massachusetts Institute of Technology (MIT) Department of Brain and Cognitive Sciences. You may quit at any time, and you will remain anonymous. Contact the requester with questions or concerns about this experiment.",  # noqa
            comment="freiwald_tsao_identification",  # noqa
            collection_name = 'freiwald_tsao_identification',
            max_assignments=1,
            bucket_name='freiwald_tsao_identification',
            trials_per_hit=trials_per_hit,
            frame_height_pix=1200,
            othersrc = ['../../mturkutils/lib/dltk.js', '../../mturkutils/lib/dltkexpr.js', '../../mturkutils/lib/dltkrsvp.js'],
            additionalrules=additionalrules,
            log_prefix='freiwald_tsao_identification_',
            html_data = html_data

            )


    # -- create trials
    exp.createTrials(dummy_upload=dummy_upload)
    assert len(exp._trials['imgFiles']) == trials_per_hit*html_data['mult'], (len(exp._trials['imgFiles']), trials_per_hit, html_data['mult'])

    #shuffle test on a per-hit basis
    n_labels = len(exp._trials['labels'][0])
    assert n_labels == 25, n_labels
    for j in range(mult):
        rng = np.random.RandomState(seed=j)
        perm = rng.permutation(n_labels)
        for i in range(trials_per_hit * j, min(trials_per_hit * (j+1), len(exp._trials['imgFiles']))):
            f = copy.deepcopy(exp._trials['imgFiles'][i])
            t = copy.deepcopy(exp._trials['imgData'][i])
            f[1] = [f[1][_j] for _j in perm]
            exp._trials['imgFiles'][i] = f
            t['Test'] = [t['Test'][_j] for _j in perm]
            exp._trials['imgData'][i] = t
            l = copy.deepcopy(exp._trials['labels'][i])
            exp._trials['labels'][i] = [l[_j] for _j in perm]

    return exp


if __name__ == '__main__':
    sandbox = bool(int(sys.argv[1]))
    dummy_upload = bool(int(sys.argv[2]))
    exp = get_exp(sandbox=sandbox, dummy_upload=dummy_upload)
    exp.prepHTMLs()
    exp.testHTMLs()
    hl = exp.uploadHTMLs()
    exp.createHIT(secure=True)

    #hitids = cPickle.load(open('3ARIN4O78FSZNXPJJAE45TI21DLIF1_2014-06-13_16:25:48.143902.pkl'))
    #exp.disableHIT(hitids=hitids)
