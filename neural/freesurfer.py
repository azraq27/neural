import os,subprocess
import neural as nl

freesurfer_home = None
if 'FREESURFER_HOME' in os.environ:
    freesurfer_home = os.environ['FREESURFER_HOME']

subjects_dir = '.'

#: parent of parent directory of file: e.g., this_dir/other_dir/filename
parpar_dir = lambda d: os.path.abspath(os.path.join(os.path.dirname(d),os.pardir))

guess_locations = [
    '/Applications/freesurfer',
    '/usr/local/freesurfer',
    '/opt/freesurfer'
]

if_exists = lambda f: f if os.path.exists(f) else None

class FreesurferDir(object):
    '''Class to interact with a freesurfer-organized directory'''
    def __init__(self,subj_dir,subj_id):
        #: The parent subjects directory (the ``SUBJECTS_DIR`` environment variable)
        self.subj_dir = subj_dir
        #: The individual subject id
        self.subj_id = subj_id
        #: The individual subject's directory (i.e., "[subj_dir]/[subj_id]")
        self.dir_name = os.path.join(subj_dir,subj_id)

        #: Path to the skull-stripped anatomy
        self.skull_strip = if_exists(os.path.join(self.dir_name,'mri','brainmask.auto.mgz'))

def mgz_to_nifti(filename,prefix=None,gzip=True):
    '''Convert ``filename`` to a NIFTI file using ``mri_convert``'''
    setup_freesurfer()
    if prefix==None:
        prefix = nl.prefix(filename) + '.nii'
    if gzip and not prefix.endswith('.gz'):
        prefix += '.gz'
    nl.run([os.path.join(freesurfer_home,'bin','mri_convert'),filename,prefix],products=prefix)

def guess_home():
    '''If ``freesurfer_home`` is not set, try to make an intelligent guess at it'''
    global freesurfer_home
    if freesurfer_home != None:
        return True
    # if we already have it in the path, use that
    fv = nl.which('freeview')
    if fv:
        freesurfer_home = parpar_dir(os.path.realpath(fv))
        return True
    for guess_dir in guess_locations:
        if os.path.exists(guess_dir):
            freesurfer_home = guess_dir
            return True
    return False

environ_setup = False
def setup_freesurfer():
    '''Setup the freesurfer environment variables'''
    guess_home()
    os.environ['FREESURFER_HOME'] = freesurfer_home
    os.environ['SUBJECTS_DIR'] = subjects_dir
    # Run the setup script and collect the output:
    o = subprocess.check_output(['bash','-c','source %s/SetUpFreeSurfer.sh && env' % freesurfer_home])
    env = [(a.partition('=')[0],a.partition('=')[2]) for a in o.split('\n') if len(a.strip())>0]
    for e in env:
        os.environ[e[0]] = e[1]
    environ_setup = True

def recon_all(subj_id,anatomies):
    '''Run the ``recon_all`` script'''
    if not environ_setup:
        setup_freesurfer()
    if isinstance(anatomies,basestring):
        anatomies = [anatomies]
    nl.run([os.path.join(freesurfer_home,'bin','recon-all'),'-all','-subjid',subj_id] + [['-i',anat] for anat in anatomies])
