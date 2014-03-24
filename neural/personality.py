import sys,time,random
import zlib, base64

version_string = "Jarvis v0.1"

def compress(data, level=9):
	''' return compressed, ASCII-encoded string '''
	return base64.encodestring(zlib.compress(data,9))

def decompress(data):
	''' return uncompressed data '''
	return zlib.decompress(base64.decodestring(data))

def notify(msg):
	print msg

typing_speed = 100 #wpm
def slow_type(t):
	for l in t:
		sys.stdout.write(l)
		sys.stdout.flush()
		time.sleep(random.random()*10.0/typing_speed)
	print ''

try:
	from pyfiglet import Figlet
except ImportError:
	pass

def banner():
	try:
		return Figlet().renderText(version_string)
	except NameError:
		return version_string

def greet():
	notify('Hello there, sir.')

def goodbye():
	notify('All done.')


_unic_z = 'eNpVT8ENwzAI/DPFpR+SSIZnpczQDULqRRi+gGNVsSx8HBycCfMITaQ8oWoimcBN9U3ZgBeMsoAdO8GxZruViKUnk2+EwSBGarVw495aE2zYSPA4hzD5k4o1XnsqyO2UB/K6hQj2TcO98TGs50IfdQ5jMVqhNwGz1BhsDR/jp6mwqRgpPguWf4azX8Gd3ekHgEMzrA=='
_unic_bub_z = 'eNplUEEOgzAMu+cVZtIUmNTkOIk37Adk6yN2zeOXtFQTEFCp49Y2IYwSGjtloB5qUKpQnMqSlMY57l94YjfVZ+BLJRv6NxjyPRoppRAe8cQpBHTMzSPVwVKzk99Yss8Cph7JuHAtpQgWLCRH11WY/JLbm1tbZB8B951jZI+89sk0tfDaZ5CG3nmOXwjpiLo3YJZ3DDZHjjGy0Bg3OsRrwvRH2Oo7elt1+gFE3UfM'
_unic_bub_z_maxchars = 16

def _unic_bub_print(msg):
	if len(msg)>_unic_bub_z_maxchars:
		msg = msg[:_unic_bub_z_maxchars]
	msg = msg + ' '*(_unic_bub_z_maxchars - len(msg))
	msg = decompress(_unic_bub_z) % msg
	print msg		

if __name__ == "__main__":
	notify = _unic_bub_print
	greet()