''' This module contains generic helper functions

Many of these are imported into the root-level of the package to make accessing them easier '''
import neural
#from notify import notify
import os,subprocess
import datetime,random,string
import hashlib
import zlib, base64
import tempfile,shutil,re,glob

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
        if self.working_directory:
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

def run(command,products=None,working_directory='.',force_local=False,stderr=True):
    '''wrapper to run external programs
    
    :command:           list containing command and parameters 
                        (formatted the same as subprocess; must contain only strings)
    :products:          string or list of files that are the products of this command
                        if all products exist, the command will not be run, and False returned
    :working_directory: will chdir to this directory
    :force_local:       when used with `neural.scheduler`, setting to ``True`` will disable
                        all job distribution functions
    :stderr:            forward stderr into the output
    
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
        with neural.notify('Running %s...' % command[0]):
            out = None
            returncode = 0
            try:
                if stderr:
                    out = subprocess.check_output(command,stderr=subprocess.STDOUT)
                else:
                    out = subprocess.check_output(command)                    
            except subprocess.CalledProcessError, e:
                neural.notify('''ERROR: %s returned a non-zero status

----COMMAND------------
%s
-----------------------

                    
----OUTPUT-------------
%s
-----------------------
Return code: %d
''' % (command[0],' '.join(command),e.output,e.returncode),level=neural.level.error)
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

def dset_copy(dset,to_dir):
    '''robust way to copy a dataset (including AFNI briks)'''
    if neural.afni.is_afni(dset):
        dset_strip = re.sub(r'\.(HEAD|BRIK)?(\.(gz|bz))?','',dset)
        for dset_file in [dset_strip + '.HEAD'] + glob.glob(dset_strip + '.BRIK*'):
            if os.path.exists(dset_file):
                shutil.copy(dset_file,to_dir)
    else:
        if os.path.exists(dset):
            shutil.copy(dset,to_dir)
        else:
            neural.notify('Warning: couldn\'t find file %s to copy to %s' %(dset,to_dir),level=nl.level.warning)

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
                dset_copy(file,self.tmp_dir)
            except (OSError,IOError):
                pass
        os.chdir(self.tmp_dir)
        return self
    
    def __exit__(self, type, value, traceback):
        if not isinstance(self.products,list):
            self.products = [self.products]
        for file in self.products:
            try:
                dset_copy(file,self.cwd)
            except (OSError,IOError):
                pass
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp_dir,True)

def random_string(length):
    '''Returns random string of letters'''
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(length))