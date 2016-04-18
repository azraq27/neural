'''methods to do simple manipulations of datasets'''
import neural as nl
import shutil,os,glob,re,subprocess
from operator import mul

_afni_suffix_regex = r"((\+(orig|tlrc|acpc))?\.?(nii|HEAD|BRIK)?(.gz|.bz2)?)(\[\d+\])?$"

def prefix(filename):
    ''' strips common fMRI dataset suffixes from filenames '''
    return os.path.split(re.sub(_afni_suffix_regex,"",str(filename)))[1]

def suffix(filename,suffix):
    ''' returns a filenames with ``suffix`` inserted before the dataset suffix '''
    return os.path.split(re.sub(_afni_suffix_regex,"%s\g<1>" % suffix,str(filename)))[1]

def strip_subbrick(filename):
    ''' returns the filename without any ``[]`` subbrick modifiers '''
    return re.sub(r'\[\d+\]$','',filename)

def afni_copy(filename):
    ''' creates a ``+orig`` copy of the given dataset and returns the filename as a string '''
    if nl.pkg_available('afni',True):
        afni_filename = "%s+orig" % nl.prefix(filename)
        if not os.path.exists(afni_filename + ".HEAD"):
            nl.calc(filename,'a',prefix=nl.prefix(filename))
        return afni_filename

def nifti_copy(filename,prefix=None,gzip=True):
    ''' creates a ``.nii`` copy of the given dataset and returns the filename as a string'''
    # I know, my argument ``prefix`` clobbers the global method... but it makes my arguments look nice and clean
    if prefix==None:
        prefix = filename
    nifti_filename = globals()['prefix'](prefix) + ".nii"
    if gzip:
        nifti_filename += '.gz'
    if not os.path.exists(nifti_filename):
        try:
            subprocess.check_call(['3dAFNItoNIFTI','-prefix',nifti_filename,str(filename)])
        except subprocess.CalledProcessError:
            nl.notify('Error: could not convert "%s" to NIFTI dset!' % filename,level=nl.level.error)
            return None
    return nifti_filename

afni_dset_regex = r'^.*\+(orig|acpc|tlrc)\.?(HEAD|BRIK)?(.gz|.bz)?$'
nifti_dset_regex = r'^.*\.nii(.gz|.bz)?$'

def is_nifti(filename):
    '''return True/False if this looks like a NIFTI dset'''
    return re.match(nifti_dset_regex,filename)!=None

def is_afni(filename):
    '''return True/False if this looks like an AFNI dset'''
    return re.match(afni_dset_regex,filename)!=None

def is_dset(filename):
    '''just checks if the filename has the format of an fMRI dataset'''
    return nl.is_nifti(filename) or is_afni(filename)

class temp_afni_copy:
    ''' used within a ``with`` block, will create a temporary ``+orig`` copy of dataset

    When invoked in a ``with`` block, will make a ``+orig`` copy of the given dataset
    and return the filename as a string.

    On exiting the block, it will delete the ``+orig`` copy. If out_dsets is a string
    or list of strings, it will try to make nifti copies of all datasets listed
    and then delete the original version if successful. AFNI datasets should be specified
    with the ``+view``.

    Example usage::
        with temp_afni_copy('dataset.nii.gz') as dset_afni:
            do_something_with_a_dset(dset_afni)

        with temp_afni_copy('dataset.nii.gz','output_dataset+orig') as dset_afni:
            do_something_with_a_dset(dset_afni,output='output_dataset')
    '''
    def __init__(self,in_dset,out_dsets=None):
        self.in_dset = in_dset
        self.out_dsets = out_dsets

    def __enter__(self):
        self.afni_filenames = []
        if isinstance(self.in_dset,list):
            for dset in self.in_dset:
                self.afni_filenames.append(nl.afni_copy(dset))
            return self.afni_filenames
        else:
            self.afni_filenames.append(nl.afni_copy(self.in_dset))
            return self.afni_filenames[0]

    def __exit__(self, type, value, traceback):
        for afni_filename in self.afni_filenames:
            for dset in glob.glob(afni_filename + '.*'):
                try:
                    os.remove(dset)
                except OSError:
                    pass
        if self.out_dsets:
            if isinstance(self.out_dsets,basestring):
                self.out_dsets = [self.out_dsets]
            for out_dset in self.out_dsets:
                nifti_dset = nl.nifti_copy(out_dset)
                if os.path.exists(nifti_dset):
                    for dset in [out_dset,out_dset+'.HEAD']:
                        try:
                            os.remove(dset)
                        except OSError:
                            pass

def dset_copy(dset,to_dir):
    '''robust way to copy a dataset (including AFNI briks)'''
    if nl.is_afni(dset):
        dset_strip = re.sub(r'\.(HEAD|BRIK)?(\.(gz|bz))?','',dset)
        for dset_file in [dset_strip + '.HEAD'] + glob.glob(dset_strip + '.BRIK*'):
            if os.path.exists(dset_file):
                shutil.copy(dset_file,to_dir)
    else:
        if os.path.exists(dset):
            shutil.copy(dset,to_dir)
        else:
            nl.notify('Warning: couldn\'t find file %s to copy to %s' %(dset,to_dir),level=nl.level.warning)

class DsetInfo:
    '''Container for dset meta-data

    All lists are returned in RAI order (i.e., a list of 3 numbers refers to the R-L axis,
    A-P axis, then I-S axis)'''
    def __init__(self):
        self.subbricks = []
        self.voxel_size = []        #! size of voxel in mm, listed in LPI order
        self.voxel_volume = None    #! volume of voxel in mm^3
        self.voxel_dims = []
        self.spatial_from = []
        self.spatial_to = []
        self.slice_timing = None
        self.TR = None
        self.orient = None

    def subbrick_labeled(self,label):
        for i in xrange(len(self.subbricks)):
            if self.subbricks[i]['label']==label:
                return i
        raise LookupError

def _dset_info_afni(dset):
    ''' returns raw output from running ``3dinfo`` '''
    info = DsetInfo()
    try:
        raw_info = subprocess.check_output(['3dinfo','-verb',str(dset)],stderr=subprocess.STDOUT)
    except:
        return None
    if raw_info==None:
        return None
    # Subbrick info:
    sub_pattern = r'At sub-brick #(\d+) \'([^\']+)\' datum type is (\w+)(:\s+(.*)\s+to\s+(.*))?\n(.*statcode = (\w+);  statpar = (.*)|)'
    sub_info = re.findall(sub_pattern,raw_info)
    for brick in sub_info:
        brick_info = {
            'index': int(brick[0]),
            'label': brick[1],
            'datum': brick[2]
        }
        if brick[3]!='':
            brick_info.update({
                'min': float(brick[4]),
                'max': float(brick[5])
            })
        if brick[6]!='':
            brick_info.update({
                'stat': brick[7],
                'params': brick[8].split()
            })
        info.subbricks.append(brick_info)
    info.reps = len(info.subbricks)
    # Dimensions:

    orient = re.search('\[-orient ([A-Z]+)\]',raw_info)
    if orient:
        info.orient = orient.group(1)
    for axis in ['RL','AP','IS']:
        m = re.search(r'%s-to-%s extent:\s+([0-9-.]+) \[%s\] -to-\s+([0-9-.]+) \[%s\] -step-\s+([0-9-.]+) mm \[\s*([0-9]+) voxels\]' % (axis[0],axis[1],axis[0],axis[1]),raw_info)
        if m:
            info.spatial_from.append(float(m.group(1)))
            info.spatial_to.append(float(m.group(2)))
            info.voxel_size.append(float(m.group(3)))
            info.voxel_dims.append(float(m.group(4)))
    if len(info.voxel_size)==3:
        info.voxel_volume = reduce(mul,info.voxel_size)

    slice_timing = re.findall('-time:[tz][tz] \d+ \d+ [0-9.]+ (.*?) ',raw_info)
    if len(slice_timing):
        info.slice_timing = slice_timing[0]
    TR = re.findall('Time step = ([0-9.]+)s',raw_info)
    if len(TR):
        info.TR = float(TR[0])

    # Other info..
    details_regex = {
        'identifier': r'Identifier Code:\s+(.*)',
        'filetype': r'Storage Mode:\s+(.*)',
        'space': r'Template Space:\s+(.*)'
    }
    for d in details_regex:
        m = re.search(details_regex[d],raw_info)
        if m:
            setattr(info,d,m.group(1))

    return info

def dset_info(dset):
    '''returns a :class:`DsetInfo` object containing the meta-data from ``dset``'''
    if nl.pkg_available('afni'):
        return _dset_info_afni(dset)
    nl.notify('Error: no packages available to get dset info',level=nl.level.error)
    return None

def auto_polort(dset):
    '''a copy of 3dDeconvolve's ``-polort A`` option'''
    info = nl.dset_info(dset)
    return 1 + round(info.reps/150.0)

def subbrick(dset,label,coef=False,tstat=False,fstat=False,rstat=False,number_only=False):
    ''' returns a string referencing the given subbrick within a dset

    This method reads the header of the dataset ``dset``, finds the subbrick whose
    label matches ``label`` and returns a string of type ``dataset[X]``, which can
    be used by most AFNI programs to refer to a subbrick within a file

    The options coef, tstat, fstat, and rstat will add the suffix that is
    appended to the label by 3dDeconvolve

    :coef:  "#0_Coef"
    :tstat: "#0_Tstat"
    :fstat: "_Fstat"
    :rstat: "_R^2"

    if ``number_only`` is set to ``True``, will only return the subbrick number instead of a string
    '''

    if coef:
        label += "#0_Coef"
    elif tstat:
        label += "#0_Tstat"
    elif fstat:
        label += "_Fstat"
    elif rstat:
        label += "_R^2"

    info = nl.dset_info(dset)
    if info==None:
        nl.notify('Error: Couldn\'t get info from dset "%s"'%dset,level=nl.level.error)
        return None
    i = info.subbrick_labeled(label)
    if number_only:
        return i
    return '%s[%d]' % (dset,i)

def dset_grids_equal(dsets):
    '''Tests if each dataset in the ``list`` ``dsets`` has the same number of voxels and voxel-widths'''
    infos = [dset_info(dset) for dset in dsets]
    for i in xrange(3):
        if len(set([x.voxel_size[i] for x in infos]))>1 or len(set([x.voxel_dims[i] for x in infos]))>1:
            return False
    return True

def resample_dset(dset,template,prefix=None,resam='NN'):
    '''Resamples ``dset`` to the grid of ``template`` using resampling mode ``resam``.
    Default prefix is to suffix ``_resam`` at the end of ``dset``

    Available resampling modes:
        :NN:    Nearest Neighbor
        :Li:    Linear
        :Cu:    Cubic
        :Bk:    Blocky
    '''
    if prefix==None:
        prefix = nl.suffix(dset,'_resam')
    nl.run(['3dresample','-master',template,'-rmode',resam,'-prefix',prefix,'-inset',dset])

def ijk_to_xyz(dset,ijk):
    '''convert the dset indices ``ijk`` to RAI coordinates ``xyz``'''
    i = nl.dset_info(dset)
    orient_codes = [int(x) for x in nl.run(['@AfniOrient2RAImap',i.orient]).output.split()]
    orient_is = [abs(x)-1 for x in orient_codes]
    rai = []
    for rai_i in xrange(3):
         ijk_i = orient_is[rai_i]
         if orient_codes[rai_i] > 0:
             rai.append(ijk[ijk_i]*i.voxel_size[rai_i] + i.spatial_from[rai_i])
         else:
             rai.append(i.spatial_to[rai_i] - ijk[ijk_i]*i.voxel_size[rai_i])
    return rai

def bounding_box(dset):
    '''return the coordinates (in RAI) of the corners of a box enclosing the data in ``dset``'''
    o = nl.run(["3dAutobox","-input",dset])
    ijk_coords = re.findall(r'[xyz]=(\d+)\.\.(\d+)',o.output)
    from_rai = ijk_to_xyz(dset,[float(x[0]) for x in ijk_coords])
    to_rai = ijk_to_xyz(dset,[float(x[1]) for x in ijk_coords])
    return (from_rai,to_rai)

def value_at_coord(dset,coords):
    '''returns value at specified coordinate in ``dset``'''
    return nl.numberize(nl.run(['3dmaskave','-q','-dbox'] + list(coords) + [dset],stderr=None).output)

