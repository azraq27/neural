# Color functions
colors = {
    'black':  90,
    'red':    91,
    'green':  92,
    'yellow': 93,
    'blue':   94,
    'magenta': 95,
    'cyan':   96,
    'white':  97 }

def color(mesg,col):
	return "\033[%sm%s\033[0m" %(colors[col],mesg)

def cursor_move_to(line,col):
	return "\033[%d;%dH" %(line,col)

def cursor_up(lines):
	return "\033[%dA" %(lines)

def cursor_down(lines):
	return "\033[%dB" %(lines)

def cursor_forward(cols):
	return "\033[%dC" %(cols)

def cursor_back(cols):
	return "\033[%dD" %(cols)

def cursor_clearscreen():
	return "\033[2J"

def cursor_clearline():
	return "\033[K"