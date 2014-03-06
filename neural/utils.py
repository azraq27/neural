''' This module contains generic helper functions

Many of these are imported into the root-level of the package to make accessing them easier '''
import neural
from notify import notify
import os,subprocess
import datetime
import hashlib

def flatten(nested_list):
	'''converts a list-of-lists to a single flat list'''
	return_list = []
	for i in nested_list:
		if isinstance(i,list):
			return_list += flatten(i)
		else:
			return_list.append(i)
	return return_list

class run_in:
	'''temporarily changes into another directory
	
	Example::	
		with run_in('another_directory'):
			do_some_stuff_there()
	'''
	def __init__(self,working_directory):
		self.working_directory = working_directory

	def __enter__(self):
		self.old_cwd = os.getcwd()
		if self.working_directory:
			os.chdir(self.working_directory)

	def __exit__(self, type, value, traceback):
		os.chdir(self.old_cwd)

def run(command,products=None,working_directory='.'):
	'''wrapper to run external programs
	
	:command:			list containing command and parameters 
						(formatted the same as subprocess; must contain only strings)
	:products:			string or list of files that are the products of this command
						if all products exist, the command will not be run, and False returned
	:working_directory:	will chdir to this directory
	
	Returns stdout of command
	'''
	with run_in(working_directory):
		if products:
			if isinstance(products,basestring):
				products = [products]
			if all([os.path.exists(x) for x in products]):
				return False
		
		command = flatten(command)
		command = [str(x) for x in command]
		if(neural.verbose):
			notify('Running %s...' % command[0])
		out = None
		try:
			out = subprocess.check_output(command)
		except subprocess.CalledProcessError, e:
			notify('''ERROR: %s returned a non-zero status

----COMMAND------------
%s
-----------------------

					
----OUTPUT-------------
%s
-----------------------
Return code: %d
''' % (command[0],' '.join(command),e.output,e.returncode))
		return out

def log(fname,msg):
	''' generic logging function '''
	with open(fname,'a') as f:
		f.write(datetime.datetime.now().strftime('%m-%d-%Y %H:%M:\n') + msg + '\n')

def hash(filename):
	'''returns MD5 hash of given filename'''
	buffer_size = 10*1024*1024
	m = hashlib.md5()
	with open(filename) as f:
		buff = f.read(buffer_size)
		while len(buff)>0:
			m.update(buff)
			buff = f.read(buffer_size)			
	return m.digest()

class simple_timer:
	'''a simple way to time a single run of a function
	
	Example::
		with simple_timer():
			do_stuff()
	'''
	def __init__(self):
		self.start_time = None
	
	def __enter__(self):
		self.start_time = datetime.datetime.now()
		print 'timer start time: %s' % self.start_time.strftime('%Y-%m-%d %H:%M:%S')
	
	def __exit__(self, type, value, traceback):
		self.end_time = datetime.datetime.now()
		print 'timer end time: %s' % self.end_time.strftime('%Y-%m-%d %H:%M:%S')
		print 'time elapsed: %s' % str(self.end_time-self.start_time)

def factor(n):
	'''return set of all prime factors for a number'''
    return set(reduce(list.__add__, ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))