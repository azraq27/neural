''' This module contains generic helper functions, not related to imaging specifically'''
import neural as nl
import os,subprocess
import datetime,random,string
import hashlib
import zlib, base64
import tempfile,shutil,re,glob,time,random
import chardet
from threading import Thread,Event
import json,time,re
import numpy as np


#! A list of archives this library understands
archive_formats = {
    'zip': {'suffix':'zip', 'command':lambda output,filename: ['unzip','-o','-d',output,filename]},
    'tarball': {'suffix':('tar.gz','tgz'), 'command':lambda output,filename: ['tar','zx','-C',output,'-f',filename]},
    'tarball-bzip': {'suffix':('tar.bz2','tbz'), 'command':lambda output,filename: ['tar','jx','-C',output,'-f',filename]},
    '7zip': {'suffix':'7z', 'command':lambda output,filename: ['7z','x','-y','-o%s' % output, filename]}
}

def is_archive(filename):
    '''returns boolean of whether this filename looks like an archive'''
    for archive in archive_formats:
        if filename.endswith(archive_formats[archive]['suffix']):
            return True
    return False

def archive_basename(filename):
    '''returns the basename (name without extension) of a recognized archive file'''
    for archive in archive_formats:
        if filename.endswith(archive_formats[archive]['suffix']):
            return filename.rstrip('.' + archive_formats[archive]['suffix'])
    return False

def unarchive(filename,output_dir='.'):
    '''unpacks the given archive into ``output_dir``'''
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for archive in archive_formats:
        if filename.endswith(archive_formats[archive]['suffix']):
            return subprocess.call(archive_formats[archive]['command'](output_dir,filename))==0
    return False

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

    If the directory name you pass doesn't exist, but matches the current directory
    you are in, it will silently ignore your silliness. Otherwise, it will raise an
    ``OSError``. If the argument ``create`` is True, it will create the directory instead
    of raising an error.

    Example::
        with run_in('another_directory'):
            do_some_stuff_there()
    '''
    def __init__(self,working_directory,create=False):
        self.working_directory = working_directory
        self.create = create

    def __enter__(self):
        self.old_cwd = os.getcwd()
        if self.working_directory and self.working_directory!='.':
            if os.path.exists(self.working_directory):
                os.chdir(self.working_directory)
            elif self.old_cwd.endswith(self.working_directory.rstrip('/')):
                # Silly, we're already in that directory
                pass
            else:
                if self.create:
                    os.makedirs(self.working_directory)
                    os.chdir(self.working_directory)
                else:
                    raise IOError('Attempting to run_in the non-existent directory "%s"' % self.working_directory)

    def __exit__(self, type, value, traceback):
        os.chdir(self.old_cwd)

class RunResult:
    '''result of calling :meth:`run`

    when used as a string, will try to reasonably return the filename of the primary output
    of the command (if known)'''
    def __init__(self,output=None,return_code=None,output_filename=None):
        self.output_filename = output_filename
        self.output = output
        self.return_code = return_code

    def __str__(self):
        return self.output_filename

def run(command,products=None,working_directory='.',force_local=False,stderr=True,quiet=False):
    '''wrapper to run external programs

    :command:           list containing command and parameters
                        (formatted the same as subprocess; must contain only strings)
    :products:          string or list of files that are the products of this command
                        if all products exist, the command will not be run, and False returned
    :working_directory: will chdir to this directory
    :force_local:       when used with `neural.scheduler`, setting to ``True`` will disable
                        all job distribution functions
    :stderr:            forward ``stderr`` into the output
                        ``True`` will combine ``stderr`` and ``stdout``
                        ``False`` will return ``stdout`` and let ``stderr`` print to the console
                        ``None`` will return ``stdout`` and suppress ``stderr``
    :quiet:             ``False`` (default) will print friendly messages
                        ``True`` will suppress everything but errors
                        ``None`` will suppress all output

    Returns result in form of :class:`RunResult`
    '''
    with run_in(working_directory):
        if products:
            if isinstance(products,basestring):
                products = [products]
            if all([os.path.exists(x) for x in products]):
                return False

        command = flatten(command)
        command = [str(x) for x in command]
        quiet_option = False if quiet==False else True
        with nl.notify('Running %s...' % command[0],level=nl.level.debug,quiet=quiet_option):
            out = None
            returncode = 0
            try:
                if stderr:
                    # include STDERR in STDOUT output
                    out = subprocess.check_output(command,stderr=subprocess.STDOUT)
                elif stderr==None:
                    # dump STDERR into nothing
                    out = subprocess.check_output(command,stderr=subprocess.PIPE)
                else:
                    # let STDERR show through to the console
                    out = subprocess.check_output(command)
            except subprocess.CalledProcessError, e:
                if quiet!=None:
                    nl.notify('''ERROR: %s returned a non-zero status

    ----COMMAND------------
    %s
    -----------------------


    ----OUTPUT-------------
    %s
    -----------------------
    Return code: %d
    ''' % (command[0],' '.join(command),e.output,e.returncode),level=nl.level.error)
                out = e.output
                returncode = e.returncode
            result = RunResult(out,returncode)
            if products and returncode==0:
                result.output_filename = products[0]
            return result

def log(fname,msg):
    ''' generic logging function '''
    with open(fname,'a') as f:
        f.write(datetime.datetime.now().strftime('%m-%d-%Y %H:%M:\n') + msg + '\n')

def hash(filename):
    '''returns string of MD5 hash of given filename'''
    buffer_size = 10*1024*1024
    m = hashlib.md5()
    with open(filename) as f:
        buff = f.read(buffer_size)
        while len(buff)>0:
            m.update(buff)
            buff = f.read(buffer_size)
    dig = m.digest()
    return ''.join(['%x' % ord(x) for x in dig])

def hash_str(string):
    '''returns string of MD5 hash of given string'''
    m = hashlib.md5()
    m.update(string)
    dig = m.digest()
    return ''.join(['%x' % ord(x) for x in dig])

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

def compress(data, level=9):
    ''' return compressed, ASCII-encoded string '''
    return base64.encodestring(zlib.compress(data,9))

def decompress(data):
    ''' return uncompressed string '''
    return zlib.decompress(base64.decodestring(data))

def which(program):
    '''returns full path to program name or ``None`` if not found
    taken from: http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python'''
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def find(file):
    '''tries to find ``file`` using OS-specific searches and some guessing'''
    # Try MacOS Spotlight:
    mdfind = which('mdfind')
    if mdfind:
        out = run([mdfind,'-name',file],stderr=None,quiet=None)
        if out.return_code==0 and out.output:
                for fname in out.output.split('\n'):
                    if os.path.basename(fname)==file:
                        return fname

    # Try UNIX locate:
    locate = which('locate')
    if locate:
        out = run([locate,file],stderr=None,quiet=None)
        if out.return_code==0 and out.output:
            for fname in out.output.split('\n'):
                if os.path.basename(fname)==file:
                    return fname

    # Try to look through the PATH, and some guesses:
    path_search = os.environ["PATH"].split(os.pathsep)
    path_search += ['/usr/local/afni','/usr/local/afni/atlases','/usr/local/share','/usr/local/share/afni','/usr/local/share/afni/atlases']
    afni_path = which('afni')
    if afni_path:
        path_search.append(os.path.dirname(afni_path))
    if nl.wrappers.fsl.bet2:
        path_search.append(os.path.dirname(nl.wrappers.fsl.bet2))
    for path in path_search:
        path = path.strip('"')
        try:
            if file in os.listdir(path):
                return os.path.join(path,file)
        except:
            pass

class run_in_tmp:
    '''creates a temporary directory to run the code block in'''
    def __init__(self,inputs=[],products=[]):
        self.tmp_dir = tempfile.mkdtemp()
        self.cwd = None
        self.inputs = inputs
        self.products = products

    def __enter__(self):
        if not isinstance(self.inputs,list):
            self.inputs = [self.inputs]
        self.cwd = os.getcwd()
        for file in self.inputs:
            try:
                nl.dset_copy(file,self.tmp_dir)
            except (OSError,IOError):
                pass
        os.chdir(self.tmp_dir)
        return self

    def __exit__(self, type, value, traceback):
        if not isinstance(self.products,list):
            self.products = [self.products]
        for file in self.products:
            try:
                nl.dset_copy(file,self.cwd)
            except (OSError,IOError):
                pass
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp_dir,True)

def random_string(length):
    '''Returns random string of letters'''
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(length))

def universal_read(fname):
    '''Will open and read a file with universal line endings, trying to decode whatever format it's in (e.g., utf8 or utf16)'''
    with open(fname,'rU') as f:
        data = f.read()
    enc_guess = chardet.detect(data)
    return data.decode(enc_guess['encoding'])

class ThreadSafe(object):
    '''wrapper class to handle starting and stopping for the :meth:`thread_safe` method of :class:`Beacon`'''
    def __init__(self,beacon):
        self.beacon = beacon

    def __enter__(self):
        self.beacon.write_packet()
        self.beacon.start()

    def __exit__(self, type, value, traceback):
        self.beacon.stop()

class Beacon(Thread):
    '''Class to easily handle running multiple threads simultaneously. Communicates through a lockfile in an
    arbitrary file path, so communicating across different computers that have shared file systems is relatively
    easy (just choose a file path on the shared drive).

    Options:

        :app_name:      Arbitrary name of the script. Will use script filename if ``None``
        :instance_name: Arbitrary name of this instance (e.g., subject #)
        :packet_path:   Path to put the lock file in (defaults to the system temp directory)
        :poll_time:     How often (in seconds) to ping the lock file

    Example of usage::

        b = Beacon('my_analysis','subject_4')
        if not b.exists():
            # there are no "my_analysis" scripts running "subject_4" right now
            with b.thread_safe():
                # lock this, so other scripts will fail when they run b.exists() on this subject
                # do the analysis here...
        '''
    def __init__(self,app_name=None,instance_name=None,packet_path=None,poll_time=0.5):
        Thread.__init__(self)
        self.stop_event = Event()
        self.app_name = app_name
        if app_name==None:
            self.app_name = os.path.basename(__file__)
        self.instance_name = instance_name
        self.filename = self.app_name
        if instance_name:
            self.filename += '_' + instance_name
        self.filename += '.lock'
        self.packet_path = packet_path
        if packet_path==None:
            self.packet_path = tempfile.gettempdir()
        self.poll_time = poll_time

    def exists(self):
        '''Returns a ``bool`` of whether this analysis is already running somewhere else'''
        return not self.check_packet()

    def thread_safe(self):
        '''Use in a ``with`` statement to run code within a thread-safe context. When the ``with`` statement
        enters, this will create the lock file, and it will automatically stop and delete it when the ``with``
        block finishes'''
        return ThreadSafe(self)

    def packet(self):
        return {
            'app_name':self.app_name,
            'instance_name':self.instance_name,
            'poll_time':self.poll_time,
            'last_time':time.time()
        }

    def packet_file(self):
        return os.path.join(self.packet_path,self.filename)

    def write_packet(self):
        with open(self.packet_file(),'w') as f:
            f.write(json.dumps(self.packet()))

    def check_packet(self):
        '''is there a valid packet (from another thread) for this app/instance?'''
        if not os.path.exists(self.packet_file()):
            # No packet file, we're good
            return True
        else:
            # There's already a file, but is it still running?
            try:
                with open(self.packet_file()) as f:
                    packet = json.loads(f.read())
                if time.time() - packet['last_time'] > 3.0*packet['poll_time']:
                    # We haven't heard a ping in too long. It's probably dead
                    return True
                else:
                    # Still getting pings.. probably still a live process
                    return False
            except:
                # Failed to read file... try again in a second
                time.sleep(random.random()*2)
                return self.check_packet()

    def run(self):
        while not self.stop_event.wait(self.poll_time):
            self.write_packet()
        if os.path.exists(self.packet_file()):
            try:
                os.remove(self.packet_file())
            except:
                pass

    def stop(self):
        self.stop_event.set()

def strip_rows(array,invalid=None):
    '''takes a ``list`` of ``list``s and removes corresponding indices containing the
    invalid value (default ``None``). '''
    array = np.array(array)
    none_indices = np.where(np.any(np.equal(array,invalid),axis=0))
    return tuple(np.delete(array,none_indices,axis=1))

def numberize(string):
    '''Turns a string into a number (``int`` or ``float``) if it's only a number (ignoring spaces), otherwise returns the string.
    For example, ``"5 "`` becomes ``5`` and ``"2 ton"`` remains ``"2 ton"``'''
    if not isinstance(string,basestring):
        return string
    just_int = r'^\s*[-+]?\d+\s*$'
    just_float = r'^\s*[-+]?\d+\.(\d+)?\s*$'
    if re.match(just_int,string):
        return int(string)
    if re.match(just_float,string):
        return float(string)
    return string
