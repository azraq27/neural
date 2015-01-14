''' Provides a centralized notification function

The functions will try to detect the specific system and situation to tailor
the notification to the most appropriate method
'''
import sys,os,io
import platform
import random,string,copy
import smtplib
from email.mime.text import MIMEText
import neural.term

class SMTPServer:
    def __init__(self,from_addr,server,username=None,password=None,SSL=False):
        self.from_addr = from_addr
        self.server = server
        self.username = username
        self.password = password
        self.SSL = SSL

default_SMTP = None

def enable_email(from_email,server,username=None,password=None,SSL=False):
    global default_SMTP
    default_SMTP = SMTPServer(from_email,server,username,password,SSL)

def email(to,msg,subject='Neural notification'):
    if default_SMTP==None:
        raise RuntimeError('Email not enabled, must run ``enable_email`` first!')
    msg = MIMEText(msg)
    msg['Subject'] = subject
    msg['From'] = default_SMTP.from_addr
    msg['To'] = to
    if default_SMTP.SSL:
        s = smtplib.SMTP_SSL(default_SMTP.server)
    else:
        s = smtplib.SMTP(default_SMTP.server)
    if default_SMTP.username:
        s.login(default_SMTP.username,default_SMTP.password)
    s.sendmail(to,default_SMTP.from_addr,msg.as_string())
    s.quit()

# Log levels:
class level:
    debug, informational, warning, error, critical = range(5)

interactive_enabled = False
email_digest = None

#! variable to hold list of nested notifications
_notify_tree = []
_digest_list = []

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
        for d in _digest_list:
            if d.level==None or level>=d.level:
                d._notifications.append((copy.copy(_notify_tree),self))
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

def notify_normal(n,notify_tree=None):
    prefix = ''
    if notify_tree==None:
        notify_tree=_notify_tree
    if(len(notify_tree) > 0):
        prefix += '  '*len(notify_tree) + '- '
    n_prefixed = prefix + n.text + '\n'
    try:
        if os.isatty(sys.stderr.fileno()):
            color = 'green'
            if n.level >= level.warning:
                color = 'yellow'
            if n.level >= level.error:
                color = 'red'
            n_prefixed = neural.term.color(n_prefixed,color)
    except:
        pass
    sys.stderr.write(n_prefixed)
    sys.stderr.flush()

### Digesting methods

class collect_digest(object):
    '''generic object to collect notifications within a block and then do something with them
    when the block exits'''
    def __init__(self,level=level.warning,email=False,print_summary=False):
        self._notifications = []
        self.level = level
        self.email = email
        self.print_summary = print_summary
    
    def __enter__(self):
        _digest_list.append(self)
    
    def __exit__(self,type,value,traceback):
        if self in _digest_list:
            _digest_list[:] = [x for x in _digest_list if x!=self]
        if self.print_summary:
            if len(self._notifications)>0:
                notify('\n\nSummary of previous notifications:\n' + '-'*20 + '\n')
                old_tree = []
                for n in self._notifications:
                    new_tree = n[0]
                    for i in reversed(range(len(old_tree))):
                        try:
                            if new_tree[i]!=old_tree[i]:
                                del(old_tree[i])
                        except IndexError:
                            pass
                    for new_n in new_tree[len(old_tree):]:
                        notify_normal(new_n,old_tree)
                        old_tree.append(new_n)
                    notify_normal(n[1],old_tree)


### Email notification

class email_digest:
    def __init__(self,email_address,level=None):
        '''start an email digest
        
        Will try to capture all notifications sent within the following code block that are
        sent with ``email=True``. In addition, if ``level`` is given, will only collect notifications
        with the given level or higher'''
        pass
    
    def __enter__(self):
        pass
    
    def __exit__(self, type, value, traceback):
        pass
    

### Platform-specific methods:

if platform.system() == 'Darwin':
    if int(platform.release().split(".")[0])>=12:
        try:
            from pync import Notifier
        except ImportError: 
            pass
        else:
            def notify_mountainlion(n):
                notify_normal(n)
                return
                group_id = '%d-%s' % (os.getpid(),n.id)
                text = n.text
                if len(_notify_tree):
                    temp_tree = [x.text for x in _notify_tree] + [text]
                    text = '\n'.join(['%s%s' % ('  '*i,temp_tree[i]) for i in xrange(len(temp_tree))])
                    group_id = '%d-%s' % (os.getpid(),_notify_tree[0].id)
                    Notifier.remove(group_id)
                Notifier.notify(text,title='Jarvis',group=group_id)
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