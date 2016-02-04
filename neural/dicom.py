'''methods to analyze DICOM format images'''

from __future__ import absolute_import
import subprocess,re,os,multiprocessing,glob,itertools,tempfile,shutil
from datetime import datetime
import neural as nl
import string
# No, I'm not importing myself... this is actually the pydicom library
import dicom as pydicom
from fuzzywuzzy import process
import nibabel as nib
import numpy as np

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
    
    ``tags`` is expected to be a list of tuples that contains the DICOM address in hex values.
    
    basically a rewrite of :meth:`info` because it's so slow. This is a lot faster and more reliable'''
    if isinstance(tags,tuple):
        tags = [tags]
    d = pydicom.read_file(filename)
    return_dict = {}
    dicom_info = None
    for k in tags:
        if k in d:
            return_dict[k] = d[k].value
        else:
            # Backup to the old method
            if dicom_info==None:
                dicom_info = info(filename)
            i = dicom_info.addr(k)
            if i:
                return_dict[k] = nl.numberize(i['value'])
    return return_dict

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

def max_diff(dset1,dset2):
    '''calculates maximal voxel-wise difference in datasets (in %)
    
    Useful for checking if datasets have the same data. For example, if the maximum difference is
    < 1.0%, they're probably the same dataset'''
    for dset in [dset1,dset2]:
        if not os.path.exists(dset):
            nl.notify('Error: Could not find file: %s' % dset,level=nl.level.error)
            return float('inf')
    try:
        dset1_d = nib.load(dset1)
        dset2_d = nib.load(dset2)
        dset1_data = dset1_d.get_data()
        dset2_data = dset2_d.get_data()
    except IOError:
        nl.notify('Error: Could not read files %s and %s' % (dset1,dset2),level=nl.level.error)
        return float('inf')
    try:
        old_err = np.seterr(divide='ignore',invalid='ignore')
        max_val = 100*np.max(np.ma.masked_invalid(np.double(dset1_data - dset2_data) / ((dset1_data+dset2_data)/2)))
        np.seterr(**old_err)
        return max_val
    except ValueError:
        return float('inf')

def _create_dset_dicom(directory,slice_order='alt+z',sort_order=None,force_slices=None):
    tags = {
        'num_rows': (0x0028,0x0010),
        'num_reps': (0x0020,0x0105),
        'num_frames': (0x0028,0x0008),
        'acq_time': (0x0008,0x0032),
        'siemens_slices': (0x0019, 0x100a),
        'TR': (0x0018,0x0080)
    }
    with nl.notify('Trying to create datasets from %s' % directory):
        directory = os.path.abspath(directory)
            
        if not os.path.exists(directory):
            nl.notify('Error: could not find %s' % directory,level=nl.level.error)
            return False
        
        out_file = '%s.nii.gz' % nl.prefix(os.path.basename(directory))
        if os.path.exists(out_file):
            nl.notify('Error: file "%s" already exists!' % out_file,level=nl.level.error)
            return False

        cwd = os.getcwd()
        sorted_dir = tempfile.mkdtemp()
        try:
            with nl.run_in(sorted_dir):
                file_list = glob.glob(directory + '/*')
                num_reps = None
                
                new_file_list = []
                for f in file_list:
                    try:
                        if len(info_for_tags(f,tags['num_rows']))>0:
                            # Only include DICOMs that actually have image information
                            new_file_list.append(f)
                    except:
                        pass
                file_list = new_file_list
                if len(file_list)==0:
                    nl.notify('Error: Couldn\'t find any valid DICOM images',level=nl.level.error)
                    return False
                
                with open('file_list.txt','w') as f:
                    f.write('\n'.join(file_list))
                try:
                    subprocess.check_output([
                    'Dimon',
                    '-infile_list','file_list.txt',
                    '-dicom_org', 
                    '-save_details','details',
                    '-max_images','100000',
                    '-fast','-no_wait',
                    '-quit'],stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError, e:
                    nl.notify('Warning: Dimon returned an error while sorting images',level=nl.level.warning)
                else:
                    if os.path.exists('details.2.final_list.txt'):
                        with open('details.2.final_list.txt') as f:
                            details = [x.strip().split() for x in f.readlines() if x[0]!='#']
                            file_list = [x[0] for x in details]
                    else:
                        nl.notify('Warning: Dimon didn\'t return expected output, unable to sort images',level=nl.level.warning)
                
                cmd = ['to3d','-skip_outliers','-quit_on_err','-prefix',out_file]
                
                num_reps = None
                i = info_for_tags(file_list[0],[tags['num_reps'],tags['acq_time'],tags['TR']])
                if tags['num_reps'] in i and i[tags['num_reps']]>1:
                    # multiple reps per file
                    num_reps = i[tags['num_reps']]
                    # probably makes sense to default to "tz"
                    if sort_order==None:
                        sort_order='tz'
                else:
                    if tags['acq_time'] in i and len(file_list)>1:
                        i2 = info_for_tags(file_list[1],[tags['acq_time']])
                        if i[tags['acq_time']] != i2[tags['acq_time']]:
                            # each file is a different rep
                            num_reps = len(file_list)
                            # "zt" sounds like a good default
                            if sort_order==None:
                                sort_order='zt'
                
                if num_reps:
                    # This is a time-dependent dataset
                    cmd += ['-time:' + sort_order]
                    num_files = len(file_list)
                    num_slices = None
                    if force_slices:
                        num_slices = force_slices
                    else:
                        for f in file_list:
                            # Take into account multi-frame DICOMs
                            num_frames_info = info_for_tags(f,[tags['num_frames'],tags['siemens_slices']])
                            if tags['num_frames'] in num_frames_info and not isinstance(num_frames_info[tags['num_frames']],basestring):
                                num_files += num_frames_info[tags['num_frames']] - 1
                            if tags['siemens_slices'] in num_frames_info and not isinstance(num_frames_info[tags['siemens_slices']],basestring):
                                num_files += num_frames_info[tags['siemens_slices']] - 1                            
                        num_slices = num_files/num_reps
                    if sort_order=='zt':
                        cmd += [str(num_slices),str(num_reps)]
                    else:
                        cmd += [str(num_reps),str(num_slices)]
                    cmd += [str(i[tags['TR']]),slice_order]
                
                cmd += ['-@']
                p = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                out = p.communicate('\n'.join(file_list))
                
                if os.path.exists(out_file):
                    shutil.copy(out_file,cwd)
                    return out_file
                nl.notify('Error: Failed to create dataset\nStdout:\n%s\nStderr:\n%s' % out,level=nl.level.error)
                
                return False
        finally:
            shutil.rmtree(sorted_dir)
            
def create_dset_to3d(prefix,file_list,file_order='zt',num_slices=None,num_reps=None,TR=None,slice_order='alt+z',only_dicoms=True,sort_filenames=False):
    '''manually create dataset by specifying everything (not recommended, but necessary when autocreation fails)
    
    If `num_slices` or `num_reps` is omitted, it will be inferred by the number of images. If both are omitted,
    it assumes that this it not a time-dependent dataset
    
    :only_dicoms:       filter the given list by readable DICOM images
    :sort_filenames:    sort the given files by filename using the right-most number in the filename'''
    
    tags = {
        'num_rows': (0x0028,0x0010),
        'TR': (0x0018,0x0080)
    }
    with nl.notify('Trying to create dataset %s' % prefix):
        if os.path.exists(prefix):
            nl.notify('Error: file "%s" already exists!' % prefix,level=nl.level.error)
            return False
        
        if only_dicoms:
            new_file_list = []
            for f in file_list:
                try:
                    if len(info_for_tags(f,tags['num_rows']))>0:
                        # Only include DICOMs that actually have image information
                        new_file_list.append(f)
                except:
                    pass
            file_list = new_file_list
        
        if sort_filenames:
            def file_num(fname):
                try:
                    nums = [x.strip('.') for x in re.findall(r'[\d.]+',fname) if x.strip('.')!='']
                    return float(nums[-1])
                except:
                    return fname
            file_list = sorted(file_list,key=file_num)
        
        if len(file_list)==0:
            nl.notify('Error: Couldn\'t find any valid DICOM images',level=nl.level.error)
            return False
        

        cmd = ['to3d','-skip_outliers','-quit_on_err','-prefix',prefix]

        if num_slices!=None or num_reps!=None:
            # Time-based dataset
            if num_slices==None:
                if len(file_list)%num_reps!=0:
                    nl.notify('Error: trying to guess # of slices, but %d (number for files) doesn\'t divide evenly into %d (number of reps)' % (len(file_list),num_reps),level=nl.level.error)
                    return False
                num_slices = len(file_list)/num_reps
            if num_reps==None:
                if len(file_list)%num_slices!=0:
                    nl.notify('Error: trying to guess # of reps, but %d (number for files) doesn\'t divide evenly into %d (number of slices)' % (len(file_list),num_slices),level=nl.level.error)
                    return False
                num_reps = len(file_list)/num_slices
        
            if TR==None:
                i = info_for_tags(file_list[0],[tags['TR']])
                TR = i[tags['TR']]
            cmd += ['-time:%s'%file_order]
            if file_order=='zt':
                cmd += [num_slices,num_reps]
            else:
                cmd += [num_reps,num_slices]
            cmd += [TR,slice_order]
        cmd += ['-@']
        cmd = [str(x) for x in cmd]
        out = None
        try:
            p = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out = p.communicate('\n'.join(file_list))
            if p.returncode!=0:
                raise Exception
        except:
            with nl.notify('Error: to3d returned error',level=nl.level.error):
                if out:
                    nl.notify('stdout:\n' + out[0] + '\nstderr:\n' + out[1],level=nl.level.error)
            return False

def create_dset(directory,slice_order='alt+z',sort_order='zt',force_slices=None):
    '''tries to autocreate a dataset from images in the given directory'''
    return _create_dset_dicom(directory,slice_order,sort_order,force_slices=force_slices)
    # Add more options for GE I-files, and other non-DICOM data formats

def date_for_str(date_str):
    '''tries to guess date from ambiguous date string'''
    try:
        for date_format in itertools.permutations(['%Y','%m','%d']):
            try:
                date = datetime.strptime(date_str,''.join(date_format))
                raise StopIteration
            except ValueError:
                pass
        return None
    except StopIteration:
        return date

def date_for_image(image_fname):
    '''returns date from DICOM header of ``image_fname`` as datetime object'''
    date_info = info_for_tags(image_fname,[(0x8,0x21)])
    date_str = date_info[(0x8,0x21)]
    return date_for_str(date_str)

def organize_dir(orig_dir):
    '''scans through the given directory and organizes DICOMs that look similar into subdirectories
    
    output directory is the ``orig_dir`` with ``-sorted`` appended to the end'''
    
    tags = [
        (0x10,0x20),    # Subj ID
        (0x8,0x21),     # Date
        (0x8,0x31),     # Time
        (0x8,0x103e)    # Descr
    ]
    orig_dir = orig_dir.rstrip('/')
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
                
def classify(label_dict,image_fname=None,image_label=None):
    '''tries to classify a DICOM image based on known string patterns (with fuzzy matching)
    
    Takes the label from the DICOM header and compares to the entries in ``label_dict``. If it finds something close
    it will return the image type, otherwise it will return ``None``. Alternatively, you can supply your own string, ``image_label``,
    and it will try to match that.
    
    ``label_dict`` is a dictionary where the keys are dataset types and the values are lists of strings that match that type.
    For example::
    
        {
            'anatomy': ['SPGR','MPRAGE','anat','anatomy'],
            'dti': ['DTI'],
            'field_map': ['fieldmap','TE7','B0']
        }
    '''
    min_acceptable_match = 80
    if image_fname:
        label_info = info_for_tags(image_fname,[(0x8,0x103e)])
        image_label = label_info[(0x8,0x103e)]
    # creates a list of tuples: (type, keyword)
    flat_dict = [i for j in [[(b,x) for x in label_dict[b]]  for b in label_dict] for i in j]
    best_match = process.extractOne(image_label,[x[1] for x in flat_dict])
    if best_match[1]<min_acceptable_match:
        return None
    else:
        return [x[0] for x in flat_dict if x[1]==best_match[0]][0]

def reconstruct_files(input_dir):
    '''sorts ``input_dir`` and tries to reconstruct the subdirectories found'''
    input_dir = input_dir.rstrip('/')
    with nl.notify('Attempting to organize/reconstruct directory'):
        # Some datasets start with a ".", which confuses many programs
        for r,ds,fs in os.walk(input_dir):
            for f in fs:
                if f[0]=='.':
                    shutil.move(os.path.join(r,f),os.path.join(r,'i'+f))
        nl.dicom.organize_dir(input_dir)
        output_dir = '%s-sorted' % input_dir
        if os.path.exists(output_dir):
            with nl.run_in(output_dir):
                for dset_dir in os.listdir('.'):
                    with nl.notify('creating dataset from %s' % dset_dir):
                        nl.dicom.create_dset(dset_dir)
        else:
            nl.notify('Warning: failed to auto-organize directory %s' % input_dir,level=nl.level.warning)

def unpack_archive(fname,out_dir):
    '''unpacks the archive file ``fname`` and reconstructs datasets into ``out_dir``
    
    Datasets are reconstructed and auto-named using :meth:`create_dset`. The raw directories
    that made the datasets are archive with the dataset name suffixed by ``tgz``, and any other
    files found in the archive are put into ``other_files.tgz``'''
    with nl.notify('Unpacking archive %s' % fname):
        tmp_dir = tempfile.mkdtemp()
        tmp_unpack = os.path.join(tmp_dir,'unpack')
        os.makedirs(tmp_unpack)
        nl.utils.unarchive(fname,tmp_unpack)
        reconstruct_files(tmp_unpack)
        out_dir = os.path.abspath(out_dir)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        if not os.path.exists(tmp_unpack+'-sorted'):
            return
        with nl.run_in(tmp_unpack+'-sorted'):
            for fname in glob.glob('*.nii'):
                nl.run(['gzip',fname])
            for fname in glob.glob('*.nii.gz'):
                new_file = os.path.join(out_dir,fname)
                if not os.path.exists(new_file):
                    shutil.move(fname,new_file)
            raw_out = os.path.join(out_dir,'raw')
            if not os.path.exists(raw_out):
                os.makedirs(raw_out)
            for rawdir in os.listdir('.'):
                rawdir_tgz = os.path.join(raw_out,rawdir+'.tgz')
                if not os.path.exists(rawdir_tgz):
                    with tarfile.open(rawdir_tgz,'w:gz') as tgz:
                        tgz.add(rawdir)
        if len(os.listdir(tmp_unpack))!=0:
            # There are still raw files left
            with tarfile.open(os.path.join(raw_out,'other_files.tgz'),'w:gz') as tgz:
                tgz.add(tmp_unpack)
    shutil.rmtree(tmp_dir)