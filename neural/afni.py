''' wrapper functions for common AFNI tasks '''
import re,subprocess,os,glob,copy,tempfile,shutil
import multiprocessing
import neural
import neural as nl
import platform
from operator import mul

def _open_X11_ports():
    tcp_ports = []
    if platform.system()=='Darwin':
        tcp_ports = subprocess.check_output('lsof -i -n | awk \'$9 ~ /:60[0-9][0-9]$/ {split($9,a,":"); print a[length(a)]}\' | sort | uniq',shell=True).strip().split('\n')
    if platform.system()=='Linux':
        tcp_ports = subprocess.check_output('netstat -ntlp | awk \'$6=="LISTEN" && $4 ~ /:60[0-9][0-9]$/ {split($4,a,":"); print a[length(a)]}\' | sort | uniq',shell=True).strip().split('\n')
    local_sockets = []
    if os.path.exists('/tmp/.X11-unix/'): 
        local_sockets = [x[1:] for x in os.listdir('/tmp/.X11-unix/')]
    return ['localhost:%d' % (int(x)-6000) for x in tcp_ports] + [':%s' % x for x in local_sockets]
    
def openX11(dsets=[]):
    ''' hack-y style method to try to open an AFNI window with the directory or datasets given 
    
    if this function is useful, it should be made more stable/portable'''
    my_env = os.environ.copy()
    if 'DISPLAY' not in my_env or my_env['DISPLAY']=='':
        open_ports = _open_X11_ports()
        if len(open_ports)==0:
            raise Exception('Couldn\'t find any open X11 ports')
        my_env['DISPLAY'] = open_ports[0]
    subprocess.Popen(['afni'] + dsets, env=my_env)

def _dset_raw_info(dset):
    ''' returns raw output from running ``3dinfo`` '''
    return subprocess.check_output(['3dinfo','-verb',str(dset)],stderr=subprocess.STDOUT)

class DsetInfo:
    ''' contains organized output from ``3dinfo`` 
    
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

def dset_info(dset):
    ''' runs ``3dinfo`` and returns a :class:`DsetInfo` object containing the results '''
    info = DsetInfo()
    raw_info = _dset_raw_info(dset)
    # Subbrick info:
    sub_info = re.findall(r'At sub-brick #(\d+) \'([^\']+)\' datum type is (\w+).*(\n.*statcode = (\w+);  statpar = (.*)|)',raw_info)
    for brick in sub_info:
        info.subbricks.append({
            'label': brick[1],
            'datum': brick[2],
            'stat': brick[4],
            'params': brick[5].split()
        })
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
        'filetype': r'Storage Mode:\s+(.*)'
    }
    
    for d in details_regex:
        m = re.search(details_regex[d],raw_info)
        if m:
            setattr(info,d,m.group(1))
    
    return info

def subbrick(dset,label,coef=False,tstat=False,fstat=False,rstat=False):
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
    '''
    
    if coef:
        label += "#0_Coef"
    elif tstat:
        label += "#0_Tstat"
    elif fstat:
        label += "_Fstat"
    elif rstat:
        label += "_R^2"
    
    info = dset_info(dset)
    i = info.subbrick_labeled(label)
    return '%s[%d]' % (dset,i)

def calc(dsets,expr,prefix=None,datum=None):
    ''' returns a string of an inline 3dcalc expression
    
    ``dsets`` can be a single string, or list of strings. Each string in ``dsets`` will
    be labeled 'a','b','c', sequentially. The expression ``expr`` is used directly
    
    If ``prefix`` is not given, will return a 3dcalc string that can be passed to another 
    AFNI program as a dataset. Otherwise, will create the dataset with the name ``prefix``'''
    if isinstance(dsets,basestring):
        dsets = [dsets]
    if prefix:
        cmd = ['3dcalc']
    else:
        cmd = ['3dcalc(']
    
    for i in xrange(len(dsets)):
        cmd += ['-%s'% chr(97+i),dsets[i]]
    cmd += ['-expr',expr]
    if datum:
        cmd += ['-datum',datum]
    
    if prefix:
        cmd += ['-prefix',prefix]
        return nl.run(cmd,products=prefix)
    else:
        cmd += [')']
        return ' '.join(cmd)

def cdf(dset,p,subbrick=0):
    ''' converts *p*-values to the appropriate statistic for the specified subbrick '''
    info = dset_info(dset)
    command = ['cdf','-p2t',info.subbricks[subbrick]['stat'],str(p)] + info.subbricks[subbrick]['params']
    return float(subprocess.check_output(command).split()[2])

def thresh_at(dset,p,subbrick=0,positive_only=False,output_suffix=None,prefix=None):
    ''' returns a string containing an inline ``3dcalc`` command that thresholds the 
        given dataset at the specified *p*-value, or will create a new dataset if a 
        suffix or prefix is given '''
    t = cdf(dset,p,subbrick)
    expr = 'astep(a,%f)' % t
    if positive_only:
        expr = 'abs(a)*step(a-%f)' % t
    subref = '-a%d' % subbrick
    if subbrick==0 and dset[-1]==']':
        subref = '-a'
    if prefix:
        dset_out = prefix
    elif output_suffix:
        dset_out = suffix(dset,output_suffix)
    else:
        return '3dcalc( %s %s -expr %s )' % (subref,dset,expr)
    neural.run(['3dcalc',subref,dset,'-expr',expr,'-prefix',dset_out])

def cluster(dset,min_distance,min_cluster_size,prefix):
    ''' runs 3dmerge to cluster given dataset '''
    neural.run(['3dmerge','-1clust',min_distance,min_cluster_size,'-prefix',prefix,dset])

def blur(dset,fwhm,prefix=None):
    ''' runs 3dmerge to blur dataset to given ``fwhm``
    default ``prefix`` is to suffix ``dset`` with ``_blur%dmm``'''
    if prefix==None:
        prefix = suffix(dset,'_blur%dmm'%fwhm)
    neural.run(['3dmerge','-1blur_fwhm',fwhm,'-prefix',prefix,dset],products=prefix)

def voxel_count(dset,subbrick=0,p=None,positive_only=False,mask=None,ROI=None):
    ''' returns the number of non-zero voxels
    
    :subbrick:      use the given subbrick
    :p:             threshold the dataset at the given *p*-value, then count
    :positive_only: only count positive values
    :mask:          count within the given mask
    :ROI:           only use the ROI with the given value (or list of values) within the mask
                    if ROI is 'all' then return the voxel count of each ROI
                    as a dictionary
    '''
    if p:
        dset = thresh_at(dset,p,subbrick,positive_only)
    else:
        if not dset.startswith('3dcalc('):
            dset = '%s[%d]' % (dset,subbrick)
            if positive_only:
                dset = calc(dset,'step(a)')
    
    count = 0
    devnull = open(os.devnull,"w")
    if mask:
        cmd = ['3dROIstats','-1Dformat','-nomeanout','-nobriklab', '-nzvoxels']
        cmd += ['-mask',str(mask),str(dset)]
        out = subprocess.check_output(cmd,stderr=devnull).split('\n')
        if len(out)<4:
            return 0
        rois = [int(x.replace('NZcount_','')) for x in out[1].strip()[1:].split()]
        counts = [int(x.replace('NZcount_','')) for x in out[3].strip().split()]
        count_dict = None
        if ROI==None:
            ROI = rois
        if ROI=='all':
            count_dict = {}
            ROI = rois
        else:
            if not isinstance(ROI,list):
                ROI = [ROI]
        for r in ROI:
            if r in rois:
                roi_count = counts[rois.index(r)]
                if count_dict!=None:
                    count_dict[r] = roi_count
                else:
                    count += roi_count
    else:
        cmd = ['3dBrickStat', '-slow', '-count', '-non-zero', str(dset)]
        count = int(subprocess.check_output(cmd,stderr=devnull).strip())
    if count_dict:
        return count_dict
    return count

def ROIstats(mask,dsets):
    '''runs 3dROIstats on ``dsets`` using ``mask`` as the mask
    returns a dictionary with the structure::
    
        {
            ROI: {
                dset: [
                    # list of dset subbricks:
                    {keys: stat},
                    ...
                ],
                ...
            },
            ...
        }
    
    keys::
    
        :mean:
        :median:
        :mode:
        :nzmean:
        :nzmedian:
        :nzmode:
        :min:
        :max:
        :nzmin:
        :nzmax:
        :sigma:
        :nzsigma:
        :sum:
        :nzsum:
    '''
    out_dict = {}
    values = [{'Med': 'median', 'Min': 'min', 'Max': 'max', 'NZVoxels': 'nzvoxels', 
               'NZMean': 'nzmean', 'NZSum': 'nzsum', 'NZSigma': 'nzsigma', 
               'Mean': 'mean', 'Sigma': 'sigma', 'Mod': 'mode','NZcount':'nzcount'},
              {'NZMod': 'nzmode', 'NZMed': 'nzmedian', 'NZMax': 'nzmax', 'NZMin': 'nzmin','Mean':'mean'}]
    options = [['-nzmean','-nzsum','-nzvoxels','-minmax','-sigma','-nzsigma','-median','-mode'],
               ['-nzminmax','-nzmedian','-nzmode']]
    if isinstance(dsets,basestring):
        dsets = [dsets]
    for i in xrange(2):
        cmd = ['3dROIstats','-1Dformat','-nobriklab','-mask',mask] + options[i] + dsets
        out = subprocess.check_output(cmd).split('\n')
        header = [(values[i][x.split('_')[0]],int(x.split('_')[1])) for x in out[1].split()[1:]]
        for j in xrange(len(out)/2-1):
            dset_subbrick = out[(j+1)*2][1:].split()
            stats = [float(x) for x in out[(j+1)*2+1][1:].split()]
            for s in xrange(len(stats)):
                roi = header[s][1]
                stat_name = header[s][0]
                stat = stats[s]
                if roi not in out_dict:
                    out_dict[roi] = {}
                if dset_subbrick[0] not in out_dict[roi]:
                    out_dict[roi][dset_subbrick[0]] = []
                subbrick = int(dset_subbrick[1])
                if subbrick>=len(out_dict[roi][dset_subbrick[0]]):
                    for diff in xrange(subbrick-len(out_dict[roi][dset_subbrick[0]])+1):
                        out_dict[roi][dset_subbrick[0]].append({})
                out_dict[roi][dset_subbrick[0]][subbrick][stat_name] = stat
    return out_dict

_afni_suffix_regex = r"((\+(orig|tlrc|acpc))?\.?(nii|HEAD|BRIK)?(.gz|.bz2)?)(\[\d+\])?$"

def prefix(filename):
    ''' strips common fMRI dataset suffixes from filenames '''
    return os.path.split(re.sub(_afni_suffix_regex,"",str(filename)))[1]

def suffix(filename,suffix):
    ''' returns a filenames with ``suffix`` inserted before the dataset suffix '''
    return os.path.split(re.sub(_afni_suffix_regex,"%s\g<1>" % suffix,str(filename)))[1]

def afni_copy(filename):
    ''' creates a ``+orig`` copy of the given dataset and returns the filename as a string '''
    afni_filename = "%s+orig" % prefix(filename)
    if not os.path.exists(afni_filename + ".HEAD"):
        subprocess.call(['3dcalc','-a',str(filename),'-expr','a','-prefix',prefix(filename)])
    return afni_filename

def nifti_copy(filename,copy_prefix=None):
    ''' creates a ``.nii.gz`` copy of the given dataset and returns the filename as a string 
    
    If no prefix is given, will use prefix from ``filename``'''
    nifti_filename = prefix(filename) + ".nii.gz"
    if copy_prefix:
        nifti_filename = copy_prefix + ".nii.gz"
    if not os.path.exists(nifti_filename):
        subprocess.check_call(['3dAFNItoNIFTI','-prefix',nifti_filename,str(filename)])
    return nifti_filename

afni_dset_regex = r'^.*\+(orig|acpc|tlrc)\.?(HEAD|BRIK)?(.gz|.bz)?$'
nifti_dset_regex = r'^.*\.nii(.gz|.bz)?$'

def is_nifti(filename):
    return re.match(nifti_dset_regex,filename)!=None

def is_afni(filename):
    return re.match(afni_dset_regex,filename)!=None
    
def is_dset(filename):
    '''just checks if the filename has the format of an fMRI dataset'''
    return is_nifti(filename) or is_afni(filename)

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
                self.afni_filenames.append(afni_copy(dset))
            return self.afni_filenames
        else:
            self.afni_filenames.append(afni_copy(self.in_dset))
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
                nifti_dset = nifti_copy(out_dset)
                if os.path.exists(nifti_dset):
                    for dset in [out_dset,out_dset+'.HEAD']:
                        try:
                            os.remove(dset)
                        except OSError:
                            pass

class Decon:
    '''wrapper for AFNI 3dDeconvolve command
    
    Properties:
        :input_dset:        list of input datasets
        :stim_files:        dictionary where keys are used as stimulus labels
                            and the values are taken as 1D files
        :stim_times:        same as stim_files, but used as a stim_times file
        :models:            dictionary of model names to use for each of the
                            listed stimuli (optional)
        :model_default:     default model to use for each ``stim_times`` stimulus if nothing
                            is listed in ``models``
        :stim_base:         list of names of stimuli (defined either in stim_files or 
                            stim_times) that should be considered in the baseline instead
                            of full model
        :stim_am1:          list of names of stimuli defined in stim_times that should
                            use the ``-stim_times_AM1`` model
        :stim_am2:          list of names of stimuli defined in stim_times that should
                            use the ``-stim_times_AM2`` model
        :glts:              dictionary where keys are GLT labels, and the value
                            is a symbolic statement
        :mask:              either a mask file, or "auto", which will use "-automask"
        :errts:             name of file to save residual time series to
        
        Options that are obvious:
            nfirst (default: 3), censor_file, polort (default: 'A'), tout, vout, rout, prefix
            
        opts        = list of extra things to put in the command
        
        **Example:**::
        
            decon = neural.afni.Decon()
            decon.input_dsets = ['dset_run1.nii.gz', 'dset_run2.nii.gz']
            decon.censor_file = 'subject_censor.1D'
            decon.stim_files = {
                'motion_1': 'motion_file.1D[0]',
                'motion_2': 'motion_file.1D[1]',
                'motion_3': 'motion_file.1D[2]',
                'motion_4': 'motion_file.1D[3]',
                'motion_5': 'motion_file.1D[4]',
                'motion_6': 'motion_file.1D[5]'
            }
            decon.stim_base = ['motion_%d' % i for i in range(1,7)]
            decon.stim_times = {
                'stim_a': 'stim_a.stimtimes',
                'stim_b': 'stim_b.stimtimes',
                'stim_c': 'stim_c.stimtimes',
            }
            decon.glts ={
                'a-b': '1*stim_a + -1*stim_b',
                'ab-c': '0.5*stim_a + 0.5*stim_b + -1*stim_c'
            }
            decon.prefix = 'subject_decon.nii.gz'
            decon.run()
    '''
    def __init__(self):
        self.input_dsets=[]
        self.stim_files={}
        self.stim_times={}
        self.model_default = 'GAM'
        self.models = {}
        self.stim_base = []
        self.stim_am1 = []
        self.stim_am2 = []
        self.censor_file=None
        self.glts={}
        self.opts=[]
        self.nfirst = 3
        self.mask = 'auto'
        self.polort = 'A'
        self.prefix = None
        self.bout = True
        self.tout = True
        self.vout = True
        self.rout = True
        self.reps = None
        self.TR = None
        self.stim_sds = None
        self.errts = None
    
    def command_list(self):
        '''returns the 3dDeconvolve command as a list
    
        The list returned can be run by passing it into a subprocess-like command
        (e.g., neural.utils.run())
        '''
        cmd = ['3dDeconvolve']

        cmd += ['-jobs',multiprocessing.cpu_count()]
        cmd += self.opts
        if(len(self.input_dsets)):
            cmd += ['-input'] + self.input_dsets
        else:
            cmd += ['-nodata']
            if self.reps:
                cmd += [str(self.reps)]
                if self.TR:
                    cmd += [str(self.TR)]
        if self.censor_file:
            cmd += ['-censor', self.censor_file]
        cmd += ['-nfirst',str(self.nfirst)]
        if self.mask:
            if self.mask=='auto':
                cmd += ['-automask']
            else:
                cmd += ['-mask',self.mask]
        cmd += ['-polort',str(self.polort)]
        
        cmd += ['-num_stimts',len(self.stim_files)+len(self.stim_times)]
        
        stim_num = 1
        for stim in self.stim_files:
            cmd += ['-stim_file',stim_num,self.stim_files[stim],'-stim_label',stim_num,stim]
            if stim in self.stim_base:
                cmd += ['-stim_base',stim_num]
            stim_num += 1
        
        for stim in self.stim_times:
            opt = '-stim_times'
            if stim in self.stim_am1:
                opt = '-stim_times_AM1'
            if stim in self.stim_am2:
                opt = '-stim_times_AM2'
            cmd += [opt,stim_num,self.stim_times[stim]]
            if stim in self.models:
                cmd += [self.models[stim]]
            else:
                cmd += [self.model_default]
            cmd += ['-stim_label',stim_num,stim]
            if stim in self.stim_base:
                cmd += ['-stim_base',stim_num]
            stim_num += 1
        
        cmd += ['-num_glt',len(self.glts)]
        
        glt_num = 1
        for glt in self.glts:
            cmd += ['-gltsym','SYM: %s' % self.glts[glt],'-glt_label',glt_num,glt]
            glt_num += 1
        
        if self.bout:
            cmd += ['-bout']
        if self.tout:
            cmd += ['-tout']
        if self.vout:
            cmd += ['-vout']
        if self.rout:
            cmd += ['-rout']
        
        if self.errts:
            cmd += ['-errts', self.errts]
        
        if self.prefix:
            cmd += ['-bucket', self.prefix]
        
        return [str(x) for x in cmd]
    
    def command_string(self):
        '''returns the 3dDeconvolve command as as string
        
        This command can then be run in something like a shell script
        '''
        return ' '.join(self.command_list())
    
    def run(self):
        '''runs 3dDeconvolve through the neural.utils.run shortcut'''
        out = neural.run(self.command_list(),products=self.prefix)
        # Not sure where the SDs went in the deconvolve output... but they aren't there for me now
        '''if out and out.output:
            stim_sds_list = [x.split() for x in out.output.strip().split('\n\n')]
            self.stim_sds = {}
            for stim in stim_sds_list:
                self.stim_sds[stim[1]] = float(stim[-1])'''

def tshift(dset,suffix='_tshft',initial_ignore=3):
    neural.run(['3dTshift','-prefix',neural.suffix(dset,suffix),'-ignore',initial_ignore,dset],products=neural.suffix(dset,suffix))

def volreg(dset,suffix='_volreg',base_subbrick=3,tshift=True):
    ''' simple interface to 3dvolreg (recommend looking at align_epi_anat instead of using this) '''
    cmd = ['3dvolreg','-prefix',neural.suffix(dset,suffix),'-base',base_subbrick]
    if tshift:
        cmd += ['-tshift',base_subbrick]
    cmd += [dset]
    neural.run(cmd,products=neural.suffix(dset,suffix))

def affine_align(dset_from,dset_to,skull_strip=True,mask=None,affine_suffix='_aff'):
    ''' interface to 3dAllineate to align anatomies and EPIs '''
    
    dset_ss = lambda dset: os.path.split(suffix(dset,'_ns'))[1]
    def dset_source(dset):      
        if skull_strip==True or skull_strip==dset:
            return dset_ss(dset)
        else:
            return dset
    
    dset_affine = os.path.split(suffix(dset_from,affine_suffix))[1]
    dset_affine_1D = prefix(dset_affine) + '.1D'
        
    if os.path.exists(dset_affine):
        # final product already exists
        return
    
    for dset in [dset_from,dset_to]:
        if skull_strip==True or skull_strip==dset:
            neural.default.skull_strip(dset,'_ns')
        
    mask_use = mask
    if mask:
        # the mask was probably made in the space of the original dset_to anatomy,
        # which has now been cropped from the skull stripping. So the lesion mask
        # needs to be resampled to match the corresponding mask
        if skull_strip==True or skull_strip==dset_to:
            neural.run(['3dresample','-master',dset_u(dset_ss(dset)),'-inset',mask,'-prefix',neural.afni.suffix(mask,'_resam')],products=neural.afni.suffix(mask,'_resam'))
            mask_use = neural.afni.suffix(mask,'_resam')
    
    all_cmd = [
        '3dAllineate',
        '-prefix', dset_affine,
        '-base', dset_source(dset_to),
        '-source', dset_source(dset_from),
        '-cost', 'lpa',
        '-1Dmatrix_save', dset_affine_1D,
        '-autoweight',
        '-cmass'
    ]
    
    if mask:
        all_cmd += ['-emask', mask_use]
    
    neural.run(all_cmd,products=dset_affine)

def affine_apply(dset_from,affine_1D,master,affine_suffix='_aff',interp='NN',inverse=False,prefix=None):
    '''apply the 1D file from a previously aligned dataset
    Applies the matrix in ``affine_1D`` to ``dset_from`` and makes the final grid look like the dataset ``master``
    using the interpolation method ``interp``. If ``inverse`` is True, will apply the inverse of ``affine_1D`` instead'''
    affine_1D_use = affine_1D
    if inverse:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(subprocess.check_output(['cat_matvec',affine_1D,'-I']))
            affine_1D_use = temp.name
    if prefix==None:
        prefix = suffix(dset_from,affine_suffix)
    nl.run(['3dAllineate','-1Dmatrix_apply',affine_1D_use,'-input',dset_from,'-prefix',prefix,'-master',master,'-final',interp],products=suffix(dset_from,affine_suffix))


def qwarp_align(dset_from,dset_to,skull_strip=True,mask=None,affine_suffix='_aff',qwarp_suffix='_qwarp'):
    '''aligns ``dset_from`` to ``dset_to`` using 3dQwarp
    
    Will run ``3dSkullStrip`` (unless ``skull_strip`` is ``False``), ``3dUnifize``,
    ``3dAllineate``, and then ``3dQwarp``. This method will add suffixes to the input
    dataset for the intermediate files (e.g., ``_ss``, ``_u``). If those files already
    exist, it will assume they were intelligently named, and use them as is
    
    :skull_strip:       If True/False, turns skull-stripping of both datasets on/off.
                        If a string matching ``dset_from`` or ``dset_to``, will only
                        skull-strip the given dataset
    :mask:              Applies the given mask to the alignment. Because of the nature
                        of the alignment algorithms, the mask is **always** applied to
                        the ``dset_to``. If this isn't what you want, you need to reverse
                        the transform and re-apply it (e.g., using :meth:`qwarp_invert` 
                        and :meth:`qwarp_apply`). If the ``dset_to`` dataset is skull-stripped,
                        the mask will also be resampled to match the ``dset_to`` grid.
    :affine_suffix:     Suffix applied to ``dset_from`` to name the new dataset, as well as
                        the ``.1D`` file.
    :qwarp_suffix:      Suffix applied to the final ``dset_from`` dataset. An additional file
                        with the additional suffix ``_WARP`` will be created containing the parameters
                        (e.g., with the default ``_qwarp`` suffix, the parameters will be in a file with
                        the suffix ``_qwarp_WARP``)
    
    The output affine dataset and 1D, as well as the output of qwarp are named by adding
    the given suffixes (``affine_suffix`` and ``qwarp_suffix``) to the ``dset_from`` file
    
    If ``skull_strip`` is a string instead of ``True``/``False``, it will only skull strip the given
    dataset instead of both of them
    
    # TODO: currently does not work with +tlrc datasets because the filenames get mangled
    '''
    
    dset_ss = lambda dset: os.path.split(suffix(dset,'_ns'))[1]
    dset_u = lambda dset: os.path.split(suffix(dset,'_u'))[1]
    def dset_source(dset):      
        if skull_strip==True or skull_strip==dset:
            return dset_ss(dset)
        else:
            return dset
    
    dset_affine = os.path.split(suffix(dset_from,affine_suffix))[1]
    dset_affine_1D = prefix(dset_affine) + '.1D'
    dset_qwarp = os.path.split(suffix(dset_from,qwarp_suffix))[1]
    
    if os.path.exists(dset_qwarp):
        # final product already exists
        return
    
    affine_align(dset_from,dset_to,skull_strip,mask,affine_suffix)
      
    for dset in [dset_from,dset_to]:  
        neural.run([
            '3dUnifize',
            '-prefix', dset_u(dset_source(dset)),
            '-input', dset_source(dset)
        ],products=[dset_u(dset_source(dset))])
    
    mask_use = mask
    if mask:
        # the mask was probably made in the space of the original dset_to anatomy,
        # which has now been cropped from the skull stripping. So the lesion mask
        # needs to be resampled to match the corresponding mask
        if skull_strip==True or skull_strip==dset_to:
            neural.run(['3dresample','-master',dset_u(dset_ss(dset)),'-inset',mask,'-prefix',neural.afni.suffix(mask,'_resam')],products=neural.afni.suffix(mask,'_resam'))
            mask_use = neural.afni.suffix(mask,'_resam')
    
    warp_cmd = [
        '3dQwarp',
        '-prefix', dset_qwarp,
        '-duplo', '-useweight', '-blur', '0', '3',
        '-iwarp',
        '-base', dset_u(dset_source(dset_to)),
        '-source', dset_affine
    ]
    
    if mask:
        warp_cmd += ['-emask', mask_use]
    
    neural.run(warp_cmd,products=dset_qwarp)

def qwarp_apply(dset_from,dset_warp,affine=None,warp_suffix='_warp',master='WARP',interp=None):
    '''applies the transform from a previous qwarp
    
    Uses the warp parameters from the dataset listed in 
    ``dset_warp`` (usually the dataset name ends in ``_WARP``) 
    to the dataset ``dset_from``. If a ``.1D`` file is given
    in the ``affine`` parameter, it will be applied simultaneously
    with the qwarp.
    
    If the parameter ``interp`` is given, will use as interpolation method,
    otherwise it will just use the default (currently wsinc5)
    
    Output dataset with have the ``warp_suffix`` suffix added to its name
    '''
    out_dset = os.path.split(suffix(dset_from,warp_suffix))[1]
    dset_from_info = dset_info(dset_from)
    dset_warp_info = dset_info(dset_warp)
    if(dset_from_info.orient!=dset_warp_info.orient):
        # If the datasets are different orientations, the transform won't be applied correctly
        nl.run(['3dresample','-orient',dset_warp_info.orient,'-prefix',suffix(dset_from,'_reorient'),'-inset',dset_from],products=suffix(dset_from,'_reorient'))
        dset_from = suffix(dset_from,'_reorient')
    warp_opt = str(dset_warp)
    if affine:
        warp_opt += ' ' + affine
    cmd = [
        '3dNwarpApply',
        '-nwarp', warp_opt]
    cmd += [
        '-source', dset_from,
        '-master',master,
        '-prefix', out_dset
    ]
    
    if interp:
        cmd += ['-interp',interp]
    
    neural.run(cmd,products=out_dset)

def qwarp_invert(warp_param_dset,output_dset,affine_1Dfile=None):
    '''inverts a qwarp (defined in ``warp_param_dset``) (and concatenates affine matrix ``affine_1Dfile`` if given)
    outputs the inverted warp + affine to ``output_dset``'''
    
    cmd = ['3dNwarpCat','-prefix',output_dset]
    
    if affine_1Dfile:
        cmd += ['-warp1','INV(%s)' % affine_1Dfile, '-warp2','INV(%s)' % warp_param_dset]
    else:
        cmd += ['-warp1','INV(%s)' % warp_param_dset]
            
    neural.run(cmd,products=output_dset)

def skull_strip(dset,out_suffix='_ns'):
    ''' runs 3dSkullStrip (I would recommend looking at fsl.bet instead)'''
    neural.run([
        '3dSkullStrip',
        '-input', dset,
        '-prefix', suffix(dset,out_suffix),
        '-niter', '400',
        '-ld', '40'
    ],products=suffix(dset,out_suffix))

def align_epi_anat(anatomy,epi_dsets,skull_strip_anat=True):
    ''' aligns epis to anatomy using ``align_epi_anat.py`` script
    
    :epi_dsets:       can be either a string or list of strings of the epi child datasets
    :skull_strip_anat:     if ``True``, ``anatomy`` will be skull-stripped using the default method (in ``neural.default``)
    
    The default output suffix is "_al"
    '''
    
    if isinstance(epi_dsets,basestring):
        epi_dsets = [epi_dsets]
    
    if len(epi_dsets)==0:
        nl.notify('Warning: no epi alignment datasets given for anatomy %s!' % anatomy,level=nl.level.warning)
        return
    
    if all(os.path.exists(suffix(x,'_al')) for x in epi_dsets):
        return
    
    anatomy_use = anatomy
    
    if skull_strip_anat:
        nl.default.skull_strip(anatomy,'_ns')
        anatomy_use = suffix(anatomy,'_ns')
    
    inputs = [anatomy_use] + epi_dsets
    dset_products = lambda dset: [nl.suffix(dset,'_al'), nl.prefix(dset)+'_al_mat.aff12.1D', nl.prefix(dset)+'_tsh_vr_motion.1D']
    products = nl.flatten([dset_products(dset) for dset in epi_dsets])
    with nl.run_in_tmp(inputs,products): 
        if is_nifti(anatomy_use):
            anatomy_use = afni_copy(anatomy_use)
        epi_dsets_use = []
        for dset in epi_dsets:
            if is_nifti(dset):
                epi_dsets_use.append(afni_copy(dset))
            else:
                epi_dsets_use.append(dset)
        cmd = ["align_epi_anat.py", "-epi2anat", "-anat_has_skull", "no", "-epi_strip", "3dAutomask","-anat", anatomy_use, "-epi_base", "5", "-epi", epi_dsets_use[0]]
        if len(epi_dsets_use)>1:
            cmd += ['-child_epi'] + epi_dsets_use[1:]
            out = nl.run(cmd)
        
        for dset in epi_dsets:
            if is_nifti(dset):
                dset_nifti = nifti_copy(prefix(dset)+'_al+orig')
                if dset_nifti and os.path.exists(dset_nifti) and dset_nifti.endswith('.nii') and dset.endswith('.gz'):
                    nl.run(['gzip',dset_nifti])

def auto_polort(dset):
    '''a copy of 3dDeconvolve's ``-polort A`` option'''
    info = dset_info(dset)
    return 1 + round(info.reps/150.0)

class AFNI_Censor_TooManyOutliers (RuntimeError):
    pass

def create_censor_file(input_dset,out_prefix=None,fraction=0.1,clip_to=0.1,max_exclude=0.3):
    '''create a binary censor file using 3dToutcount
    
    :input_dset:        the input dataset
    :prefix:            output 1D file (default: ``prefix(input_dset)`` + ``.1D``)
    :fraction:          censor a timepoint if proportional of outliers in this
                        time point is greater than given value
    :clip_to:           keep the number of time points censored under this proportion
                        of total reps. If more time points would be censored, 
                        it will only pick the top ``clip_to*reps`` points
    :max_exclude:       if more time points than the given proportion of reps are excluded for the 
                        entire run, throw an exception -- something is probably wrong
    '''
    polort = auto_polort(input_dset)
    info = dset_info(input_dset)
    outcount = [float(x) for x in subprocess.check_output(['3dToutcount','-fraction','-automask','-polort',str(polort),str(input_dset)]).split('\n') if len(x.strip())>0]
    binary_outcount = [x<fraction for x in outcount]
    perc_outliers = 1 - (sum(binary_outcount)/float(info.reps))
    if max_exclude and perc_outliers > max_exclude:
        raise AFNI_Censor_TooManyOutliers('Found %f outliers in dset %s' % (perc_outliers,input_dset))
    if clip_to:
        while perc_outliers > clip_to:
            best_outlier = min([(outcount[i],i) for i in range(len(outcount)) if binary_outcount[i]])
            binary_outcount[best_outlier[1]] = False
            perc_outliers = sum(binary_outcount)/float(info.reps)
    if not out_prefix:
        out_prefix = prefix(input_dset) + '.1D'
    with open(out_prefix,'w') as f:
        f.write('\n'.join([str(int(x)) for x in binary_outcount]))

def smooth_decon_to_fwhm(decon,fwhm):
    '''takes an input :class:`Decon` object and uses ``3dBlurToFWHM`` to make the output as close as possible to ``fwhm``
    returns the final measured fwhm'''
    if os.path.exists(decon.prefix):
        return
    with nl.notify('Running smooth_decon_to_fwhm analysis (with %.2fmm blur)' % fwhm):
        tmpdir = tempfile.mkdtemp()
        try:
            cwd = os.getcwd()
            random_files = [re.sub(r'\[\d+\]$','',x) for x in nl.flatten([x for x in decon.__dict__.values() if isinstance(x,basestring) or isinstance(x,list)]+[x.values() for x in decon.__dict__.values() if isinstance(x,dict)])]
            files_to_copy = [x for x in random_files if os.path.exists(x) and x[0]!='/']
            # copy crap
            for file in files_to_copy:
                try:
                    shutil.copytree(file,tmpdir)
                except OSError as e:
                    shutil.copy(file,tmpdir)
                shutil.copy(file,tmpdir)
            with nl.run_in(tmpdir):
                if os.path.exists(decon.prefix):
                    os.remove(decon.prefix)
                old_errts = decon.errts
                decon.errts = 'residual.nii.gz'
                decon.prefix = os.path.basename(decon.prefix)
                # Run once in place to get the residual dataset
                decon.run()
                running_reps = 0
                blur_input = lambda i: 'input_blur-part%d.nii.gz'%(i+1)
                for i in xrange(len(decon.input_dsets)):
                    dset = decon.input_dsets[i]
                    info = dset_info(dset)
                    residual_dset = 'residual-part%d.nii.gz'%(i+1)
                    nl.run(['3dbucket','-prefix',residual_dset,'%s[%d..%d]'%(decon.errts,running_reps,running_reps+info.reps-1)],products=residual_dset)
                    nl.run(['3dBlurToFWHM','-quiet','-input',dset,'-blurmaster',residual_dset,'-prefix',blur_input(i),'-automask','-FWHM',fwhm],products=blur_input(i))
                    running_reps += info.reps
                decon.input_dsets = [blur_input(i) for i in xrange(len(decon.input_dsets))]
                for d in [decon.prefix,decon.errts]:
                    if os.path.exists(d):
                        try:
                            os.remove(d)
                        except:
                            pass
                decon.errts = old_errts
                decon.run()
                for copyfile in [decon.prefix,decon.errts]:
                    if os.path.exists(copyfile):
                        shutil.copy(copyfile,cwd)
                    else:
                        nl.notify('Warning: deconvolve did not produce expected file %s' % decon.prefix,level=nl.level.warning)
        except Exception as e:
            raise
        finally:
            shutil.rmtree(tmpdir,True)

def temporal_snr(signal_dset,noise_dset,mask=None,prefix='temporal_snr.nii.gz'):
    '''Calculates temporal SNR by dividing average signal of ``signal_dset`` by SD of ``noise_dset``.
    ``signal_dset`` should be a dataset that contains the average signal value (i.e., nothing that has
    been detrended by removing the mean), and ``noise_dset`` should be a dataset that has all possible
    known signal fluctuations (e.g., task-related effects) removed from it (the residual dataset from a 
    deconvolve works well)'''
    for d in [('mean',signal_dset), ('stdev',noise_dset)]:
        new_d = suffix(d[1],'_%s' % d[0])
        cmd = ['3dTstat','-%s' % d[0],'-prefix',new_d]
        if mask:
            cmd += ['-mask',mask]
        cmd += [d[1]]
        nl.run(cmd,products=new_d)
    calc([suffix(signal_dset,'_mean'),suffix(noise_dset,'_stdev')],'a/b',prefix=prefix)