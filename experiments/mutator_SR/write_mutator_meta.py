import tabular as tb
import sys
from os import listdir
from os.path import isfile, join
import cPickle as pickle

def parsefname(fname):
    # based on naming convention from the output of Walter -> MATLAB pipeline
    parts = fname.split('_')

    obj_id = parts[0]
    bg_id = parts[1]
    s = parts[4][2:]

    # TODO: write these parsers
    tx = ''
    ty = ''
    rx = ''
    ry = ''
    rz = ''
    var = ''
    return obj_id, bg_id, s, tx, ty, rx, ry, rz, var

def get_img_url(fname):
    # Get image url hosted on dlmug s3 repository
    url = 'https://s3.amazonaws.com/mutatorsr/resources/mutator_stimuli/' + fname
    return url

def main(argv=[]):
    # Write meta tabarray for mutator images, based on naming convention from Walter -> MATLAB pipeline

    obj_directory = '/mindhive/dicarlolab/u/mil/mutator_stimulus_generation/stimuli/pilot4'
    savename = "meta_pilot4.pkl"
    onlyfiles = [f for f in listdir(obj_directory) if isfile(join(obj_directory, f))]

    Recs = []
    for fname in onlyfiles:
        obj_id, bg_id, _, _, _, _, _, _, _ = parsefname(fname)
        Recs.append((obj_id, bg_id, get_img_url(fname)))

    meta = tb.tabarray(records = Recs, names = ['obj', 'bg_id', 'url'])
    pickle.dump(meta, open(savename, "wb"))

if __name__ == '__main__':
    main(sys.argv)