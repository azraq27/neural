''' wrapper functions for common AFNI tasks '''
import re,subprocess,os
import multiprocessing
import neural
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
	
def open(dsets=[]):
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
	return subprocess.check_output(['3dinfo','-verb',dset])

class DsetInfo:
	''' contains organized output from ``3dinfo`` 
	
	All lists are returned in RAI order (i.e., a list of 3 numbers refers to the R-L axis,
	A-P axis, then I-S axis)'''
	def __init__(self):
		self.subbricks = []
		self.voxel_size = []		#! size of voxel in mm, listed in LPI order
		self.voxel_volume = None	#! volume of voxel in mm^3
		self.voxel_dims = []
		self.spatial_from = []
		self.spatial_to = []
	
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
	
	for axis in ['RL','AP','IS']:
		m = re.search(r'%s-to-%s extent:\s+([0-9-.]+) \[%s\] -to-\s+([0-9-.]+) \[%s\] -step-\s+([0-9-.]+) mm \[([0-9]+) voxels\]' % (axis[0],axis[1],axis[0],axis[1]),raw_info)
		if m:
			info.spatial_from.append(float(m.group(1)))
			info.spatial_to.append(float(m.group(2)))
			info.voxel_size.append(float(m.group(3)))
			info.voxel_dims.append(float(m.group(4)))
	if len(info.voxel_size)==3:
		info.voxel_volume = reduce(mul,info.voxel_size)
	
	# Other info..
	details_regex = {
		r'Identifier Code:\s+([^ ]+)': 'identifier',
	}
	
	return info

def subbrick(dset,label,coef=False,tstat=False,fstat=False,rstat=False):
	''' returns a string referencing the given subbrick within a dset
	
	This method reads the header of the dataset ``dset``, finds the subbrick whose
	label matches ``label`` and returns a string of type ``dataset[X]``, which can
	be used by most AFNI programs to refer to a subbrick within a file
	
	The options coef, tstat, fstat, and rstat will add the suffix that is
	appended to the label by 3dDeconvolve
	
	:coef:	"#0_Coef"
	:tstat:	"#0_Tstat"
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

def calc(dsets,expr):
	''' returns a string of an inline 3dcalc expression
	
	``dsets`` can be a single string, or list of strings. Each string in ``dsets`` will
	be labeled 'a','b','c', sequentially. The expression ``expr`` is used directly'''
	if isinstance(dsets,basestring):
		dsets = [dsets]
	cmd = '3dcalc( '
	for i in xrange(len(dsets)):
		cmd += '-%s %s ' % (chr(97+i),dsets[i])
	cmd += '-expr %s )' % expr
	return cmd

def cdf(dset,p,subbrick=0):
	''' converts *p*-values to the appropriate statistic for the specified subbrick '''
	info = dset_info(dset)
	command = ['cdf','-p2t',info.subbricks[subbrick]['stat'],str(p)] + info.subbricks[subbrick]['params']
	return float(subprocess.check_output(command).split()[2])

def thresh_at(dset,p,subbrick=0,positive_only=False):
	''' returns a string containing an inline ``3dcalc`` command that thresholds the 
		given dataset at the specified *p*-value '''
	t = cdf(dset,p,subbrick)
	expr = 'astep(a,%f)' % t
	if positive_only:
		expr = 'step(a-%f)' % t
	return '3dcalc( -a%d %s -expr %s )' % (subbrick,dset,expr)

def voxel_count(dset,subbrick=0,p=None,positive_only=False):
	''' returns the number of non-zero voxels, or number of voxels exceeding the given *p*-value threshold '''
	if p:
		dset = thresh_at(dset,p,subbrick,positive_only)
	else:
		if not dset.startswith('3dcalc('):
			dset = '%s[%d]' % (dset,subbrick)
	if positive_only:
		opt = '-non-negative'
	else:
		opt = '-non-zero'
	return int(subprocess.check_output(['3dBrickStat','-slow','-count',opt,dset]))

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
		subprocess.call(['3dcalc','-a',filename,'-expr','a','-prefix',prefix(filename)])
	return afni_filename

def nifti_copy(filename):
	''' creates a ``.nii.gz`` copy of the given dataset and returns the filename as a string '''
	nifti_filename = prefix(filename) + ".nii.gz"
	if not os.path.exists(nifti_filename):
		subprocess.call(['3dcalc','-a',filename,'-expr','a','-prefix',nifti_filename])
	return nifti_filename

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
		:input_dset:		list of input datasets
		:stim_files:		dictionary where keys are used as stimulus labels
					  		and the values are taken as 1D files
		:stim_times:		same as stim_files, but used as a stim_times file
		:stim_times_model:	default model to use for each stim_times
		:stim_base:			list of names of stimuli (defined either in stim_files or 
							stim_times) that should be considered in the baseline instead
							of full model
		:stim_am1:			list of names of stimuli defined in stim_times that should
							use the ``-stim_times_AM1`` model
		:stim_am2:			list of names of stimuli defined in stim_times that should
							use the ``-stim_times_AM2`` model
		:glts:				dictionary where keys are GLT labels, and the value
					  		is a symbolic statement
		:mask:				either a mask file, or "auto", which will use "-automask"
		
		Options that are obvious:
			nfirst (default: 3), censor_file, polort (default: 'A'), tout, vout, rout, prefix
			
		opts		= list of extra things to put in the command
		
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
		self.stim_times_model = 'GAM'
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
		self.tout = True
		self.vout = True
		self.rout = True
	
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
			cmd += [opt,stim_num,self.stim_times[stim],self.stim_times_model,'-stim_label',stim_num,stim]
			if stim in self.stim_base:
				cmd += ['-stim_base',stim_num]
			stim_num += 1
		
		cmd += ['-num_glt',len(self.glts)]
		
		glt_num = 1
		for glt in self.glts:
			cmd += ['-gltsym','SYM: %s' % self.glts[glt],'-glt_label',glt_num,glt]
			glt_num += 1
		
		if self.tout:
			cmd += ['-tout']
		if self.vout:
			cmd += ['-vout']
		if self.rout:
			cmd += ['-rout']
		
		if self.prefix:
			cmd += ['-bucket', self.prefix]
		
		return cmd
	
	def command_string(self):
		'''returns the 3dDeconvolve command as as string
		
		This command can then be run in something like a shell script
		'''
		return ' '.join(self.command_list())
	
	def run(self,working_directory='.'):
		'''runs 3dDeconvolve through the neural.utils.run shortcut'''
		return neural.run(self.command_list(),working_directory=working_directory,products=self.prefix)

def qwarp_align(dset_from,dset_to,skull_strip=True,mask=None,affine_suffix='_aff',qwarp_suffix='_qwarp'):
	'''aligns ``dset_from`` to ``dset_to`` using 3dQwarp
	
	Will run ``3dSkullStrip`` (unless ``skull_strip`` is ``False``), ``3dUnifize``,
	``3dAllineate``, and then ``3dQwarp``. This method will add suffixes to the input
	dataset for the intermediate files (e.g., ``_ss``, ``_u``). If those files already
	exist, it will assume they were intelligently named, and use them as is
	
	:skull_strip:		If True/False, turns skull-stripping of both datasets on/off.
						If a string matching ``dset_from`` or ``dset_to``, will only
						skull-strip the given dataset
	:mask:				Applies the given mask to the alignment. Because of the nature
						of the alignment algorithms, the mask is **always** applied to
						the ``dset_to``. If this isn't what you want, you need to reverse
						the transform and re-apply it (e.g., using :meth:`qwarp_invert` 
						and :meth:`qwarp_apply`). If the ``dset_to`` dataset is skull-stripped,
						the mask will also be resampled to match the ``dset_to`` grid.
	:affine_suffix:		Suffix applied to ``dset_from`` to name the new dataset, as well as
						the ``.1D`` file.
	:qwarp_suffix:		Suffix applied to the final ``dset_from`` dataset. An additional file
						with the additional suffix ``_WARP`` will be created containing the parameters
						(e.g., with the default ``_qwarp`` suffix, the parameters will be in a file with
						the suffix ``_qwarp_WARP``)
	
	The output affine dataset and 1D, as well as the output of qwarp are named by adding
	the given suffixes (``affine_suffix`` and ``qwarp_suffix``) to the ``dset_from`` file
	
	If ``skull_strip`` is a string instead of ``True``/``False``, it will only skull strip the given
	dataset instead of both of them
	
	
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
	
	for dset in [dset_from,dset_to]:
		if skull_strip==True or skull_strip==dset:
			neural.run([
				'3dSkullStrip',
				'-input', dset,
				'-prefix', dset_ss(dset),
				'-niter', '400',
				'-ld', '40'
			],products=dset_ss(dset))
		
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
	
	all_cmd = [
		'3dAllineate',
		'-prefix', dset_affine,
		'-base', dset_u(dset_source(dset_to)),
		'-source', dset_u(dset_source(dset_from)),
		'-twopass',
		'-cost', 'lpa',
		'-1Dmatrix_save', dset_affine_1D,
		'-autoweight', 
		'-fineblur', '3',
		'-cmass'
	]
	
	if mask:
		all_cmd += ['-emask', mask_use]
	
	neural.run(all_cmd,products=dset_affine)
	
	warp_cmd = [
		'3dQwarp',
		'-prefix', dset_qwarp,
		'-duplo', '-useweight', '-blur', '0', '3',
		'-base', dset_u(dset_source(dset_to)),
		'-source', dset_affine
	]
	
	if mask:
		warp_cmd += ['-emask', mask_use]
	
	neural.run(warp_cmd,products=dset_qwarp)

def qwarp_apply(dset_from,dset_warp,affine=None,warp_suffix='_warp',master='WARP'):
	'''applies the transform from a previous qwarp
	
	Uses the warp parameters from the dataset listed in 
	``dset_warp`` (usually the dataset name ends in ``_WARP``) 
	to the dataset ``dset_from``. If a ``.1D`` file is given
	in the ``affine`` parameter, it will be applied simultaneously
	with the qwarp.
	
	Output dataset with have the ``warp_suffix`` suffix added to its name
	'''
	warp = [dset_warp]
	if affine:
		warp.append(affine)
	out_dset = os.path.split(suffix(dset_from,warp_suffix))[1]
	neural.run([
		'3dNwarpApply',
		'-nwarp', ' '.join(warp),
		'-source', dset_from,
		'-master',master,
		'-prefix', out_dset
	],products=out_dset)

def qwarp_invert(warp_param_dset,output_dset,affine_1Dfile=None):
	'''inverts a qwarp (defined in ``warp_param_dset``) (and concatenates affine matrix ``affine_1Dfile`` if given)
	outputs the inverted warp + affine to ``output_dset``'''
	
	cmd = ['3dNwarpCat','-prefix',output_dset,
		   '-warp1','INV(%s)' % warp_param_dset]
	if affine_1Dfile:
		cmd += ['-warp2','INV(%s)' % affine_1Dfile]
	neural.run(cmd,products=output_dset)