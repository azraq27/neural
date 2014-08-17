'''methods to analyze DICOM format images'''

from __future__ import absolute_import
import subprocess,re,os,multiprocessing,glob
import neural as nl
import string
# No, I'm not importing myself... this is actually the pydicom library
import dicom as pydicom

def is_dicom(filename):
    '''returns Boolean of whether the given file has the DICOM magic number'''
    try:
        with open(filename) as f:
            d = f.read(132)
            return d[128:132]=="DICM"
    except:
        return False

_dicom_hdr = 'dicom_hdr'

class DicomInfo:
    '''container for header information from DICOM file
    
    Header frames are dictionaries with the following values:
    
    :addr:      tuple of (group,element) tags in hex
    :label:     description
    :offset:    offset of data
    :size:      size of data
    :value:     data value
    '''
    
    def __init__(self,frames=[],sex_info={},slice_times=[]):
        self.raw_frames = frames    #! list of dictionaries containing information on each frame
        self.sex_info = sex_info    #! dictinary with Siemen's extra info fields
        self.slice_times = slice_times #! list of Siemen's slice timing information     
    
    def addr(self,address):
        '''returns dictionary with frame information for given address (a tuple of two hex numbers)'''
        if isinstance(address,basestring):
            # If you just gave me a single string, assume its "XXXX XXXX"
            addr = address.split()
        else:
            addr = list(address)            
        # Convert to actual hex if you give me strings
        for i in xrange(len(addr)):
            if isinstance(addr[i],basestring):
                addr[i] = int(addr[i],16)
        for frame in self.raw_frames:
            if frame['addr']==address:
                return frame
    
    def label(self,label):
        '''returns dictionary with frame information for a given text label'''
        for frame in self.raw_frames:
            if frame['label']==label:
                return frame

def info(filename):
    '''returns a DicomInfo object containing the header information in ``filename``'''
    try:
        out = subprocess.check_output([_dicom_hdr,'-sexinfo',filename])
    except subprocess.CalledProcessError:
        return None
    slice_timing_out = subprocess.check_output([_dicom_hdr,'-slice_times',filename])
    slice_timing = [float(x) for x in slice_timing_out.strip().split()[5:]]
    frames = []
    for frame in re.findall(r'^(\w{4}) (\w{4})\s+(\d+) \[(\d+)\s+\] \/\/(.*?)\/\/(.*?)$',out,re.M):
        new_frame = {}
        new_frame['addr'] = (int(frame[0],16),int(frame[1],16))
        new_frame['size'] = int(frame[2])
        new_frame['offset'] = int(frame[3])
        new_frame['label'] = frame[4].strip()
        new_frame['value'] = frame[5].strip()
        frames.append(new_frame)
    sex_info = {}
    for i in re.findall(r'^(.*?)\s+= (.*)$',out,re.M):
        sex_info[i[0]] = i[1]

    return DicomInfo(frames,sex_info,slice_timing)

def info_for_tags(filename,tags):
    '''return a dictionary for the given ``tags`` in the header of the DICOM file ``filename``
    
    basically a rewrite of :meth:`info` because it's so slow'''
    d = pydicom.read_file(filename)
    return {k:d[k].value for k in tags if k in d}

def scan_dir(dirname,tags=None,md5_hash=False):
    '''scans a directory tree and returns a dictionary with files and key DICOM tags
    
    return value is a dictionary absolute filenames as keys and with dictionaries of tags/values
    as values
    
    the param ``tags`` is the list of DICOM tags (given as tuples of hex numbers) that 
    will be obtained for each file. If not given,
    the default list is:
    
    :0008 0021:     Series date
    :0008 0031:     Series time
    :0008 103E:     Series description
    :0008 0080:     Institution name
    :0010 0020:     Patient ID
    :0028 0010:     Image rows
    :0028 0011:     Image columns
    
    If the param ``md5_hash`` is ``True``, this will also return the MD5 hash of the file. This is useful
    for detecting duplicate files
    '''
    if tags==None:
        tags = [
            (0x0008, 0x0021),
            (0x0008, 0x0031),
            (0x0008, 0x103E),
            (0x0008, 0x0080),
            (0x0010, 0x0020),
            (0x0028, 0x0010),
            (0x0028, 0x0011),
        ]
    
    return_dict = {}    
    
    for root,dirs,files in os.walk(dirname):
        for filename in files:
            fullname = os.path.join(root,filename)
            if is_dicom(fullname):
                return_dict[fullname] = info_for_tags(fullname,tags)
                if md5_hash:
                    return_dict[fullname]['md5'] = nl.hash(fullname)
    return return_dict

valid = '_.' + string.ascii_letters + string.digits
def scrub_fname(fname):
    return ''.join(c for c in fname.replace(' ','_') if c in valid).replace('__','_')
    
def find_dups(file_dict):
    '''takes output from :meth:`scan_dir` and returns list of duplicate files'''
    found_hashes = {}
    for f in file_dict:
        if file_dict[f]['md5'] not in found_hashes:
            found_hashes[file_dict[f]['md5']] = []
        found_hashes[file_dict[f]['md5']].append(f)
    final_hashes = dict(found_hashes)
    for h in found_hashes:
        if len(found_hashes[h])<2:
            del(final_hashes[h])
    return final_hashes.values()

def cluster_files(file_dict):
    '''takes output from :meth:`scan_dir` and organizes into lists of files with the same tags
    
    returns a dictionary where values are a tuple of the unique tag combination and values contain
    another dictionary with the keys ``info`` containing the original tag dict and ``files`` containing
    a list of files that match'''
    return_dict = {}
    for filename in file_dict:
        info_dict = dict(file_dict[filename])
        if 'md5' in info_dict:
            del(info_dict['md5'])
        dict_key = tuple(sorted([file_dict[filename][x] for x in info_dict]))
        if dict_key not in return_dict:
            return_dict[dict_key] = {'info':info_dict,'files':[]}
        return_dict[dict_key]['files'].append(filename)
    return return_dict

def max_diff(dset_a,dset_b):
    '''calculates maximal voxel-wise difference in datasets
    
    Useful for checking if datasets have the same data. For example, if the maximum difference is
    < 1.0, they're probably the same dataset'''
    for dset in [dset_a,dset_b]:
        if not os.path.exists(dset):
            raise IOError('Could not find file: %s' % dset)
    try:
        with open(os.devnull,'w') as null:
            return float(subprocess.check_output(['3dBrickStat','-max','3dcalc( -a %s -b %s -expr abs(a-b) )' %(dset_a,dset_b)],stderr=null).split()[0])
    except subprocess.CalledProcessError:
        return float('inf')

def _create_dset_dicom(directory):
    with nl.notify('Trying to create datasets from %s' % directory):
        d = str(directory)
        while d.endswith('/'):
            d = d[:1]
    
        if not os.path.exists(directory):
            nl.notify('Error: could not find %s',level=nl.level.error)
            return False
        
        out_file = '%s.nii' % nl.afni.prefix(d)
        return_val = out_file + '.gz'
        try:
            out = subprocess.check_output([
            'Dimon',
            '-infile_prefix','%s/' % directory,
            '-dicom_org', '-GERT_Reco', 
            '-gert_to3d_prefix', nl.afni.prefix(d),
            '-gert_create_dataset', '-gert_write_as_nifti', '-gert_quit_on_err',
            '-max_images','100000',
            '-quit'],stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError, e:
            nl.notify('Error: Dimon returned an error while creating dataset',level=nl.level.error)
            return_val = False
        
        if os.path.exists(out_file):
            nl.run(['gzip',out_file])
        else:
            return_val = False
        
        for junk in ['dimon.files.run.*','GERT_Reco_dicom_*']:
            for fname in glob.glob(junk):
                try:
                    os.remove(fname)
                except IOError:
                    pass
        return return_val

def create_dset(directory):
    '''tries to autocreate a dataset from images in the given directory'''
    return _create_dset_dicom(directory)
    # Add more options for GE I-files, and other non-DICOM data formats

def organize_dir(orig_dir):
    '''scans through the given directory and organizes DICOMs that look similar into subdirectories
    
    output directory is the ``orig_dir`` with ``-sorted`` appended to the end'''
    
    tags = [
        (0x10,0x20),    # Subj ID
        (0x8,0x21),     # Date
        (0x8,0x31),     # Time
        (0x8,0x103e)    # Descr
    ]
    files = scan_dir(orig_dir,tags=tags,md5_hash=True)
    dups = find_dups(files)
    for dup in dups:
        nl.notify('Found duplicates of %s...' % dup[0])
        for each_dup in dup[1:]:
            nl.notify('\tdeleting %s' % each_dup)
            try:
                os.remove(each_dup)
            except IOError:
                nl.notify('\t[failed]')
            del(files[each_dup])
    
    clustered = cluster_files(files)
    output_dir = '%s-sorted' % orig_dir
    for key in clustered:
        if (0x8,0x31) in clustered[key]['info']:
            clustered[key]['info'][(0x8,0x31)] = str(int(float(clustered[key]['info'][(0x8,0x31)])))
        for t in tags:
            if t not in clustered[key]['info']:
                clustered[key]['info'][t] = '_'
        run_name = '-'.join([scrub_fname(str(clustered[key]['info'][x])) for x in tags])+'-%d_images' %len(clustered[key]['files'])
        run_dir = os.path.join(output_dir,run_name)
        nl.notify('Moving files into %s' % run_dir)
        try:
            if not os.path.exists(run_dir):
                os.makedirs(run_dir)
        except IOError:
            nl.notify('Error: failed to create directory %s' % run_dir)
        else:
            for f in clustered[key]['files']:
                try:
                    dset_fname = os.path.split(f)[1]
                    if dset_fname[0]=='.':
                        dset_fname = '_' + dset_fname[1:]
                    os.rename(f,os.path.join(run_dir,dset_fname))
                except (IOError, OSError):
                    pass
    for r,ds,fs in os.walk(output_dir,topdown=False):
        for d in ds:
            dname = os.path.join(r,d)
            if len(os.listdir(dname))==0:
                os.remove(dname)