import tabular as tb
import sys
from os import listdir
from os.path import isfile, join
import cPickle as pickle

def parsefname(fname):
    # based on naming convention from the output of Walter -> MATLAB pipeline
    parts = fname.split('_')


    # TODO: make this less hacky, in conjunction with the MATLAB function namehash in mutator_gen
    obj_id = parts[0] # The colloquial name I gave it (e.g. 'octopus')
    bg_id = parts[1] # Name of background file, without file extension (i.e. .png)
    s = parts[4][2:] # Scale parameter

    tx = parts[6].split('x')[0][1:]
    ty = parts[6].split('x')[1][:-1]
    rx = parts[8].split('x')[0][1:]
    ry = parts[8].split('x')[1].split('y')[0]
    rz = parts[8].split('x')[1].split('y')[1]
    var = 'V'+parts[10].split('.')[0][-1:] # 'V6', 'V0', 'V3'
    return obj_id, bg_id, s, tx, ty, rx, ry, rz, var

def get_img_url(fname, s3_directory):
    # Get image url hosted on dlmug s3 repository
    url = s3_directory + fname
    return url

def main(argv=[]):
    # Write meta tabarray for mutator images, based on naming convention from Walter -> MATLAB pipeline

    obj_directory = '/mindhive/dicarlolab/u/mil/mutator_stimulus_generation/stimuli/pilot11/' # local folder containing images of the imageset.
    s3_directory = 'https://s3.amazonaws.com/mutatorsr/resources/mutator_stimuli/pilot11/pilot11/' # s3 folder containing the publically accessible images of the imageset
    savename = "meta_pilot11.pkl"

    print '\nLoading directory...'
    onlyfiles = [f for f in listdir(obj_directory) if isfile(join(obj_directory, f)) and f.endswith('.png')] # to avoid random .DS_Store

    print '\n***Done loading. Writing meta.'
    Recs = []
    for fname in onlyfiles:
        obj_id, bg_id, _, _, _, _, _, _, var = parsefname(fname)
        Recs.append((obj_id, bg_id, var, get_img_url(fname, s3_directory)))

    meta = tb.tabarray(records = Recs, names = ['obj', 'bg_id', 'var', 'url'])
    pickle.dump(meta, open(savename, "wb"))

if __name__ == '__main__':
    main(sys.argv)
