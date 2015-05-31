import os
import neural as nl

freesurfer_home = None
subjects_dir = '.'

#: parent of parent directory of file: e.g., this_dir/other_dir/filename
parpar_dir = lambda d: os.path.abspath(os.path.join(os.path.dirname(d),os.pardir))

guess_locations = [
    '/Applications/freesurfer',
    '/usr/local/freesurfer'
]

if_exists = lambda f: f if os.path.exists(f) else None

class FreesurferDir(object):
    '''Class to interact with a freesurfer-organized directory'''
    def __init__(self,subj_dir,subj_id):
        self.subj_dir = subj_dir
        self.subj_id = subj_id
        self.dir_name = os.path.join(subj_dir,subj_id)
        
        self.skull_strip = if_exists(os.path.join(self.dir_name,'mri','brainmask.auto.mgz'))

def mgz_to_nifti(filename,prefix=None,gzip=True):
    setup_freesurfer()
    if prefix==None:
        prefix = nl.prefix(filename) + '.nii'
    if gzip and not prefix.endswith('.gz'):
        prefix += '.gz'
    nl.run([os.path.join(freesurfer_home,'bin','mri_convert'),filename,prefix],products=prefix)

def guess_home():
    global freesurfer_home
    if freesurfer_home != None:
        return True
    # if we already have it in the path, use that
    fv = nl.which('freeview')
    if fv:
        freesurfer_home = parpar_dir(fv)
        return True
    for guess_dir in guess_locations:
        if os.path.exists(guess_dir):
            freesurfer_home = guess_dir
            return True
    return False

environ_setup = False
def setup_freesurfer():
    guess_home()
    os.environ['FREESURFER_HOME'] = freesurfer_home
    os.environ['SUBJECTS_DIR'] = subjects_dir
    environ_setup = True

def recon_all(subj_id,anatomies):
    if not environ_setup:
        setup_freesurfer()
    if isinstance(anatomies,basestring):
        anatomies = [anatomies]
    nl.run([os.path.join(freesurfer_home,'bin','recon-all'),'-all','-subjid',subj_id] + [['-i',anat] for anat in anatomies])