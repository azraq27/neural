''' Provides a centralized notification function

The functions will try to detect the specific system and situation to tailor
the notification to the most appropriate method
'''
import sys
import platform

def notify(text):
	sys.stderr.write(text + '\n')
	sys.stderr.flush()

### Platform-specific methods:

if platform.system() == 'Darwin':
	if platform.release().split(".")[0]=='12':
		try:
			from pync import Notifier
		except ImportError: 
			pass
		else:
			def notify_mountainlion(text):
				Notifier.notify(text,title='Jarvis')	
			notify = notify_mountainlion