#!/usr/bin/env python
import numpy as np
import cPickle as pk
import tabular as tb
import itertools
import copy
import sys
import dldata.stimulus_sets.freiwald_tsao as ft
from mturkutils.base import MatchToSampleFromDLDataExperiment

dataset = ft.FreiwaldTsao2010()
meta = dataset.meta

REPEATS_PER_QE_IMG = 1
ACTUAL_TRIALS_PER_HIT = 220
LEARNING_PERIOD = 28

repeat_inds = []
r_ind = 0
for ident in range(1, 29):
    inds = (meta['identity'] == ident).nonzero()[0]
    r_ind_l = r_ind % len(inds)
    repeat_inds.append(inds[r_ind_l])
    r_ind += 1

practice_inds = []
r_ind = 1
for ident in range(1, LEARNING_PERIOD + 1):
    inds = (meta['identity'] == ident).nonzero()[0]
    r_ind_l = r_ind % len(inds)
    practice_inds.append(inds[r_ind_l])
    r_ind += 1

def get_exp(sandbox=True, dummy_upload=True):

    n_hits_from_data = len(meta) / ACTUAL_TRIALS_PER_HIT
    categories = np.unique(dataset.meta['identity'])
    combs = [categories]

    inds = np.arange(len(meta))
    preproc = dataset.default_preproc
    #preproc['flip_tb'] = True
    image_bucket_name = 'freiwald_tsao_2010'
    urls = dataset.publish_images(inds, preproc,
                                  image_bucket_name,
                                  dummy_upload=dummy_upload)

    base_url = 'https://canonical_images.s3.amazonaws.com/'
    response_images = [{
        'urls': [base_url + 'freiwald_tsao_2010_face%.2da.png' % i for i in range(1, 29)],
        'meta': [{'identity': i} for i in range(1, 29)],
        'labels': categories}]

    mult = 10
    html_data = {
            'response_images': response_images,
            'combs': combs,
            'num_trials': 220 * mult,
            'meta_field': 'identity',
            'meta': tb.tab_rowstack([meta] * mult),
            'urls': urls * mult,
            'shuffle_test': False,
    }

    additionalrules = [{'old': 'LEARNINGPERIODNUMBER',
                        'new':  str(LEARNING_PERIOD)}]

    trials_per_hit = ACTUAL_TRIALS_PER_HIT + REPEATS_PER_QE_IMG * len(repeat_inds) + LEARNING_PERIOD
    exp = MatchToSampleFromDLDataExperiment(
            htmlsrc='ft_identity.html',
            htmldst='ft_identity_n%05d.html',
            tmpdir='tmp_ft_identity',
            sandbox=sandbox,
            title='Face recognition --- report what you see',
            reward=0.35,
            duration=1500,
            keywords=['neuroscience', 'psychology', 'experiment', 'object recognition'],  # noqa
            description="***You may complete as many HITs in this group as you want*** Complete a visual object recognition task where you report the identity of objects you see. We expect this HIT to take about 10 minutes or less, though you must finish in under 25 minutes.  By completing this HIT, you understand that you are participating in an experiment for the Massachusetts Institute of Technology (MIT) Department of Brain and Cognitive Sciences. You may quit at any time, and you will remain anonymous. Contact the requester with questions or concerns about this experiment.",  # noqa
            comment="freiwald_tsao_identification",  # noqa
            collection_name = 'freiwald_tsao_identification',
            max_assignments=1,
            bucket_name='freiwald_tsao_identification',
            trials_per_hit=trials_per_hit,
            html_data=html_data,
            frame_height_pix=1200,
            othersrc = ['../../mturkutils/lib/dltk.js', '../../mturkutils/lib/dltkexpr.js', '../../mturkutils/lib/dltkrsvp.js'],
            additionalrules=additionalrules,
            log_prefix='freiwald_tsao_identification_'
            )

    # -- create trials
    exp.createTrials(sampling='without-replacement', verbose=1)
    n_total_trials = len(exp._trials['imgFiles'])
    assert n_total_trials == 220 * mult, n_total_trials

    # -- in each HIT, the followings will be repeated 4 times to
    # estimate "quality" of data

    ind_repeats = repeat_inds * REPEATS_PER_QE_IMG
    rng = np.random.RandomState(0)
    rng.shuffle(ind_repeats)
    trials_qe = {e: [copy.deepcopy(exp._trials[e][r]) for r in ind_repeats]
            for e in exp._trials}

    ind_learn = practice_inds
    goodids = [meta[i]['id'] for i in ind_learn]

    trials_lrn = {}
    for e in exp._trials:
        trials_lrn[e] = []
        got = []
        for _ind, r in enumerate(exp._trials[e]):
            if exp._trials['imgData'][_ind]['Sample']['id'] in goodids and exp._trials['imgData'][_ind]['Sample']['id'] not in got :
                trials_lrn[e].append(copy.deepcopy(r))
                got.append(exp._trials['imgData'][_ind]['Sample']['id'])
    assert len(trials_lrn['imgData']) == len(goodids), len(trials_lrn['imgData'])

    offsets = np.arange(ACTUAL_TRIALS_PER_HIT - 1, -1, -ACTUAL_TRIALS_PER_HIT / float(len(ind_repeats))
            ).round().astype('int')

    print(len(offsets), offsets)

    print('a', len(exp._trials['imgFiles']))
    n_hits_floor = n_total_trials / ACTUAL_TRIALS_PER_HIT
    n_applied_hits = 0
    for i_trial_begin in xrange((n_hits_floor - 1) * ACTUAL_TRIALS_PER_HIT,
            -1, -ACTUAL_TRIALS_PER_HIT):
        for k in trials_qe:
            for i, offset in enumerate(offsets):
                exp._trials[k].insert(i_trial_begin + offset, trials_qe[k][i])
        n_applied_hits += 1

    print('b', len(exp._trials['imgFiles']))
    for j in range(n_applied_hits):
        for k in trials_lrn:
            for i in range(len(ind_learn)):
                exp._trials[k].insert(trials_per_hit * j, trials_lrn[k][i])

    print('c', len(exp._trials['imgFiles']))

    #shuffle test on a per-hit basis
    for j in range(n_applied_hits):
        rng = np.random.RandomState(seed=j)
        perm = rng.permutation(28)
        for i in range(trials_per_hit * j, min(trials_per_hit * (j+1), len(exp._trials['imgFiles']))):
            f = copy.deepcopy(exp._trials['imgFiles'][i])
            t = copy.deepcopy(exp._trials['imgData'][i])
            f[1] = [f[1][_j] for _j in perm]
            exp._trials['imgFiles'][i] = f
            t['Test'] = [t['Test'][_j] for _j in perm]
            exp._trials['imgData'][i] = t
            l = copy.deepcopy(exp._trials['labels'][i])
            exp._trials['labels'][i] = [l[_j] for _j in perm]


    print('d', len(exp._trials['imgFiles']))

    print '** n_applied_hits =', n_applied_hits
    print '** len for each in _trials =', \
            {e: len(exp._trials[e]) for e in exp._trials}


    _K = LEARNING_PERIOD + REPEATS_PER_QE_IMG * len(repeat_inds)
    # -- sanity check
    assert n_hits_floor == n_applied_hits == mult * n_hits_from_data, (n_total_trials, ACTUAL_TRIALS_PER_HIT, n_hits_floor, n_applied_hits, mult, n_hits_from_data)
    assert len(exp._trials['imgFiles']) == mult * (len(meta) + n_hits_from_data * _K),  (len(exp._trials['imgFiles']), mult,  (len(meta) + n_hits_from_data * _K), len(meta), n_hits_from_data, _K)

    return exp, html_data


if __name__ == '__main__':
    sandbox = bool(int(sys.argv[1]))
    dummy_upload = bool(int(sys.argv[2]))
    exp, _ = get_exp(sandbox=sandbox, dummy_upload=dummy_upload)
    exp.prepHTMLs()
    exp.testHTMLs()
    hl = exp.uploadHTMLs()
    #exp.createHIT(secure=True)

    #hitids = cPickle.load(open('3ARIN4O78FSZNXPJJAE45TI21DLIF1_2014-06-13_16:25:48.143902.pkl'))
    #exp.disableHIT(hitids=hitids)
