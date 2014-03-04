'''methods to analyze DICOM format images'''

import subprocess,re,os,multiprocessing

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
	
	:addr:		tuple of (group,element) tags in hex
	:label: 	description
 	:offset: 	offset of data
 	:size:		size of data
	:value:		data value
	'''
	
	def __init__(self,frames=[],sex_info={},slice_times=[]):
		self.raw_frames = frames	#! list of dictionaries containing information on each frame
		self.sex_info = sex_info	#! dictinary with Siemen's extra info fields
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
	out = subprocess.check_output([_dicom_hdr,'-sexinfo',filename])
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

def scan_dir(dirname,tags=None):
	'''scans a directory tree and returns a dictionary with files and key DICOM tags
	
	return value is a dictionary absolute filenames as keys and with dictionaries of tags/values
	as values
	
	the param ``tags`` is the list of DICOM tags (given as tuples of hex numbers) that 
	will be obtained for each file. If not given,
	the default list is:
	
	:0008 0022:		Acquisition date
	:0008 0032:		Acquisition time
	:0008 0033:		Image time
	:0008 103E:		Series description
	:0008 0080:		Institution name
	:0010 0020:		Patient ID
	:0028 0010:		Image rows
	:0028 0011:		Image columns
	'''
	if tags==None:
		tags = [
			(0x0008, 0x0022),
			(0x0008, 0x0032),
			(0x0008, 0x0033),
			(0x0008, 0x103E),
			(0x0008, 0x0080),
			(0x0010, 0x0020),
			(0x0028, 0x0010),
			(0x0028, 0x0011),
		]
	
	filenames = []
	
	for root,dirs,files in os.walk(dirname):
		for filename in files:
			fullname = os.path.join(root,filename)
			if is_dicom(fullname):
				filenames.append(fullname)
	
	pool = multiprocessing.Pool(processes=4)
	dinfos = pool.map(_scan_dir_helper,filenames)
	
	return_dict = {}
	for f in dinfos:
		filename = f[0]
		dinfo = f[1]
		for tag in tags:
			tag_value = dinfo.addr(tag)
			if tag_value:
				return_dict[filename][tag] = tag_value['value']
	return return_dict

def _scan_dir_helper(filename):
	'''called by :meth:`scan_dir` to help with multiprocessing'''
	dinfo = info(filename)
	return [filename,dinfo]

def cluster_files(file_dict):
	'''takes output from :meth:`scan_dir` and organizes into lists of files with the same tags'''
	return_dict = {}
	for filename in file_dict:
		if file_dict[filename] not in return_dict:
			return_dict[file_dict[filename]] = []
		return_dict[file_dict[filename]].append(filename)
	return return_dict
