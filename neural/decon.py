import os,shutil,tempfile,re,multiprocessing
import neural as nl

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
        
            decon = neural.decon.Decon()
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
        (e.g., neural.run())
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
        out = nl.run(self.command_list(),products=self.prefix)
        # Not sure where the SDs went in the deconvolve output... but they aren't there for me now
        '''if out and out.output:
            stim_sds_list = [x.split() for x in out.output.strip().split('\n\n')]
            self.stim_sds = {}
            for stim in stim_sds_list:
                self.stim_sds[stim[1]] = float(stim[-1])'''

def smooth_decon_to_fwhm(decon,fwhm):
    '''takes an input :class:`Decon` object and uses ``3dBlurToFWHM`` to make the output as close as possible to ``fwhm``
    returns the final measured fwhm'''
    if os.path.exists(decon.prefix):
        return
    with nl.notify('Running smooth_decon_to_fwhm analysis (with %.2fmm blur)' % fwhm):
        tmpdir = tempfile.mkdtemp()
#        try:
        for i in xrange(1):
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
                    info = nl.dset_info(dset)
                    residual_dset = 'residual-part%d.nii.gz'%(i+1)
                    nl.run(['3dbucket','-prefix',residual_dset,'%s[%d..%d]'%(decon.errts,running_reps,running_reps+info.reps-1)],products=residual_dset)
                    cmd = ['3dBlurToFWHM','-quiet','-input',dset,'-blurmaster',residual_dset,'-prefix',blur_input(i),'-FWHM',fwhm]
                    if decon.mask:
                        if decon.mask=='auto':
                            cmd += ['-automask']
                        else:
                            cmd += ['-mask',decon.mask]
                    nl.run(cmd,products=blur_input(i))
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
#        except Exception as e:
#            raise e
#        finally:
#            shutil.rmtree(tmpdir,True)