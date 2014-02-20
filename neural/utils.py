''' This module contains generic helper functions

Many of these are imported into the root-level of the package to make accessing them easier '''
import neural
from notify import notify
import os,subprocess
import datetime

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
			if isinstance(products,str):
				products = [products]
			if all([os.path.exists(x) for x in products]):
				return False
		
		command = flatten(command)
		command = [str(x) for x in command]
		if(neural.verbose):
			notify('Running %s...' % command[0])
		return subprocess.check_output(command)

def log(fname,msg):
	''' generic logging function '''
	with open(fname,'a') as f:
		f.write(datetime.datetime.now().strftime('%m-%d-%Y %H:%M:\n') + msg + '\n')