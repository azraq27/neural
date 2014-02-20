'''Provides functions to parse the text-file logs produced by E-Prime experiments'''

def read_header(filename):
	''' returns a dictionary of values in the header of the given file '''
	header = {}
	in_header = False
	with open(filename,'rU') as f:
		lines = [x.strip() for x in f.read().split('\n')]
		for line in lines:
			if line=="*** Header Start ***":
				in_header=True
				continue
			if line=="*** Header End ***":
				return header
			fields = line.split(": ")
			if len(fields)==2:
				header[fields[0]] = fields[1]

def parse_frames(filename):
	''' quick and dirty eprime txt file parsing - doesn\'t account for nesting 
	
	**Example usage**::
	
		for frame in neural.eprime.parse_frames("experiment-1.txt"):
			trial_type = frame['TrialSlide.Tag']
			trial_rt = float(frame['TrialSlide.RT'])
			print '%s: %fms' % (trial_type,trial_rt)
	'''
	frames = []
	with open(filename,'rU') as f:
		frame = {}
		lines = [x.strip() for x in f.read().split('\n')]
		for line in lines:
			if line == '*** LogFrame Start ***':
				frame = {}
			if line == '*** LogFrame End ***':
				frames.append(frame)
				yield frame
			fields = line.split(": ")
			if len(fields)==2:
				frame[fields[0]] = fields[1]
	#return frames