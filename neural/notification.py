''' Provides a centralized notification function

The functions will try to detect the specific system and situation to tailor
the notification to the most appropriate method
'''
import sys,os
import platform
import random,string
import smtplib
from email.mime.text import MIMEText

from_addr = None
smtp_server = None
smtp_username = None
smtp_password = None
smtp_SSL = None

def enable_email(from,server,username=None,password=None,SSL=False):
    from_addr = from
    smtp_server = server
    smtp_username = username
    smtp_password = password
    smtp_SSL = SSL

def email(to,msg,subject='Neural notification'):
    if smtp_server==None:
        raise RuntimeError('Email not enabled, must run ``enable_email`` first!')
    msg = MIMEText(msg)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to
    if smtp_SSL:
        s = smtplib.SMTP_SSL(smtp_server)
    else:
        s = smtplib.SMTP(smtp_server)
    if smtp_username:
        s.login(smtp_username,smtp_password)
    s.sendmail(to,from_addr,msg.as_string())
    s.quit()

# Log levels:
class level:
    debug, informational, warning, error, critical = range(5)

interactive_enabled = False

#! variable to hold list of nested notifications
_notify_tree = []

class notify:
    def __init__(self,text,log=False,email=False,level=level.informational):
        '''notify user or log information
    
        :text:      the content of the message
        :log:       if ``True``, will save the message
        :email:     add to email digests
        :level:     priority of message, should be '''
        self.text = text
        self.log = log
        self.email = email
        self.level = level
        self.id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        if interactive_enabled:
            notify_interactive(self)
        else:
            notify_normal(self)
        return
    
    def __enter__(self):
        _notify_tree.append(self)
    
    def __exit__(self, type, value, traceback):
        _notify_tree.pop()

def notify_interactive(n):
    pass

def notify_normal(n):
    prefix = ''
    if(len(_notify_tree) > 0):
        prefix += '  '*len(_notify_tree) + '- '
    sys.stderr.write(prefix + n.text + '\n')
    sys.stderr.flush()

### Platform-specific methods:

if platform.system() == 'Darwin':
    if int(platform.release().split(".")[0])>=12:
        try:
            from pync import Notifier
        except ImportError: 
            pass
        else:
            def notify_mountainlion(n):
                group_id = '%d-%s' % (os.getpid(),n.id)
                text = n.text
                if len(_notify_tree):
                    temp_tree = [x.text for x in _notify_tree] + [text]
                    text = '\n'.join(['%s%s' % ('  '*i,temp_tree[i]) for i in xrange(len(temp_tree))])
                    group_id = '%d-%s' % (os.getpid(),_notify_tree[0].id)
                    Notifier.remove(group_id)
                Notifier.notify(text,title='Jarvis',group=group_id)
                notify_normal(n)
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