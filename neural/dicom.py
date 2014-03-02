'''methods to analyze DICOM format images'''

import subprocess,re

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