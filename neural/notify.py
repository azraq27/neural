''' Provides a centralized notification function

The functions will try to detect the specific system and situation to tailor
the notification to the most appropriate method
'''
import sys
import platform

level_interactive = 0	#! Only notify to an interactive system
level_normal = 1		#! Print things out to the active user
level_log = 2			#! Don't print now, but add to the log, notify per schedule
level_important = 3		#! Print, and try to add it to the list of significant events for this run
level_critical = 4		#! Try to alert user by all means necessary

interactive_enabled = False

def notify(text,level=level_normal):
	if level==level_interactive:
		notify_interactive(text)
		return
	if level==level_normal:
		if interactive_enabled:
			notify_interactive(text)
		else:
			notify_normal(text)
		return

def notify_interactive(text):
	pass

def notify_normal(text):
	sys.stderr.write(text + '\n')
	sys.stderr.flush()

def notify_log(text):
	pass

def notify_critical(text):
	pass

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
			notify_interactive = notify_mountainlion
			interactive_enabled = True

try:
	in_ipython = isinstance(sys.stdout,IPython.kernel.zmq.iostream.OutStream)
except NameError:
	pass
else:
	if in_ipython:
		# We're inside iPython Notebook
		try:
			import IPython.display
		except ImportError:
			pass
		else:
			def notify_ipython_html(text):
				html = IPython.display.HTML( '<b>:: %s</b>' % text)
				IPython.display.display_html(html)
			notify_interactive = notify_ipython_html
			interactive_enabled = True