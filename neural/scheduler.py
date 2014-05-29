'''methods to implement lightweight job distribution across multiple machines

All of these functions are made on the assumption that all clients' filesystems
are identical, for example on a shared folder'''
import zmq
import json,time
from datetime import datetime
import neural as nl

default_port = 8765
packet_expire = 60.0 # seconds
_key = 'scheduler'
info = None

class Server:
    def __init__(self,name=None,address='localhost',port=default_port,password=None):
        self.name = name
        self.address = address
        self.port = port
        self.password = password
    
    def start_server(self):
        c = zmq.Context()
        sock = c.socket(zmq.REP)
        sock.bind('tcp://*:%s' % self.port)
        
        try:
            while True:
                msg = sock.recv()
                try:
                    obj = json.loads(msg)
                    if 'key' not in obj or obj['key']!=_key:
                        raise ValueError
                    if self.password:
                        if 'password' not in obj or 'time' not in obj:
                            raise ValueError
                        if nl.hash_str(self.password + str(obj['time']))!= obj['password']:
                            raise ValueError
                except ValueError:
                    # not a valid packet
                    sock.send('ERR')
                    continue
                else:
                    if 'task' in obj:
                        if obj['task']=='info':
                            sock.send(json.dumps({'name':self.name,'address':self.address,'port':self.port}))
                            continue
                    
                        if obj['task']=='job':
                            print 'Being asked to run command: ' + str(obj['command'])
                            cmd = [obj['command'],None,'.']
                            if 'products' in obj:
                                cmd[1] = obj['products']
                            if 'working_directory' in obj:
                                cmd[2] = obj['working_directory']
                            output = nl.run(*cmd)
                            sock.send(json.dumps({'output':output.__dict__()}))
                            continue
                
                    sock.send('OK')
        except KeyboardInterrupt:
            c.destroy()

def _send_raw(msg,address='localhost',port=default_port):
    c = zmq.Context()
    sock = c.socket(zmq.REQ)
    sock.connect('tcp://%s:%s' % (address,port))
    sock.send(msg)
    return sock.recv()  

def server_info(address='localhost',port=default_port):
    info_req = json.dumps({'key':_key,'task':'info'})
    rep = _send_raw(info_req,address,port)
    info = ServerInfo()
    try:
        rep_dict = json.loads(rep)
        for key in rep_dict:
            setattr(info,key,rep_dict[key])
    except (ValueError,KeyError):
        return None
    return info

class Job:
    def __init__(self,command=[],products=None,working_directory='.'):
        self.command = command
        self.working_directory = working_directory
        self.products = products
        self.result = None

def send_job(job,address='localhost',port=default_port,password=None):
    job_req_dict = dict({'key':_key,'task':'job','time':time.time()}.items() + job.__dict__.items())
    if password:
        job_req_dict['password'] = nl.hash_str(password + str(job_req_dict['time']))
    job_req = json.dumps(job_req_dict)
    rep = _send_raw(job_req,address,port)
    try:
        rep_dict = json.loads(rep)
        for key in rep_dict:
            if key=='output':
                output = nl.utils.RunResult()
                for okey in output:
                    setattr(output,okey,output[okey])
                job.output = output
            else:
                setattr(job,key,rep_dict[key])
    except (ValueError,KeyError):
        return None
    return job

class Scheduler:
    def __init__(self):
        self.servers = [{'address':'local'}]
    
    def add_server(self,address,port=default_port,password=None,speed=None,valid_times=None,invalid_times=None):
        '''
        :address:           remote address of server, or special string ``local`` to
                            run the command locally
        :valid_times:       times when this server is available, given as a list
                            of tuples of 2 strings of form "HH:MM" that define the
                            start and end times. Alternatively, a list of 7 lists can
                            be given to define times on a per-day-of-week basis
        E.g.,::
        
            [('4:30','14:30'),('17:00','23:00')]
            # or
            [
                [('4:30','14:30'),('17:00','23:00')],       # S
                [('4:30','14:30'),('17:00','23:00')],       # M
                [('4:30','14:30'),('17:00','23:00')],       # T
                [('4:30','14:30'),('17:00','23:00')],       # W
                [('4:30','14:30'),('17:00','23:00')],       # R
                [('4:30','14:30'),('17:00','23:00')],       # F
                [('4:30','14:30'),('17:00','23:00')]        # S
            ]
        
        :invalid_times:     uses the same format as ``valid_times`` but defines times
                            when the server should not be used
        '''
        for t in [valid_times,invalid_times]:
            if t:
                if not (self._is_list_of_tuples(t) or self._is_list_of_tuples(t,True)):
                    raise ValueError('valid_times and invalid_times must either be lists of strings or lists')
        self.servers.append({
            'address':address,
            'port':port,
            'password':password,
            'speed':speed,
            'valid_times':valid_times,
            'invalid_times':invalid_times
        })
    
    def _is_list_of_tuples(self,l,is_list=False):
        if not isinstance(l,list):
            return False
        for x in l:
            if is_list:
                if not isinstance(x,list):
                    return False
                for y in x:
                    if not isinstance(y,tuple):
                        return False
                    for z in y:
                        if not isinstance(z,basestring):
                            return False
            else:
                if not isinstance(x,tuple):
                    return False
                for z in x:
                    if not isinstance(z,basestring):
                        return False
        return True
    
    def _time_is_inbetween(self,t,tt):
        tt_from = [int(x) for x in tt[0].split(':')]
        tt_to = [int(x) for x in tt[1].split(':')]
        if ((t.hour>tt_from[0] or (t.hour==tt_from[0] and t.minute>tt_from[1])) and
            (t.hour<tt_to[0] or (t.hour==tt_to[0] and t.minute<tt_to[1]))):
            return True
        return False
    
    def choose_server(self):
        valid_servers = []
        now = datetime.now()
        for server in self.servers:
            valid = True
            if 'valid_times' in server and server['valid_times']:
                times = server['valid_times']
                if self._is_list_of_tuples(times,is_list=True):
                    wday = (now.weekday() + 1) % 7  # Make Sunday==0
                    times = server['valid_times'][wday]
                valid = False
                for t in times:
                    if self._time_is_inbetween(now,t):
                        valid = True
                        break
            if 'invalid_times' in server and server['invalid_times']:
                times = server['invalid_times']
                if self._is_list_of_tuples(times,is_list=True):
                    wday = (now.weekday() + 1) % 7  # Make Sunday==0
                    times = server['valid_times'][wday]
                for t in times:
                    if self._time_is_inbetween(now,t):
                        valid = False
                        break
            if valid:
                valid_servers.append(server)
        sorted_servers = sorted(valid_servers,key=lambda x: x['speed'] if 'speed' in x and x['speed'] else 0)
        return sorted_servers[-1]

scheduler = Scheduler()

def _new_run(command,products=None,working_directory='.',force_local=False):
    server = scheduler.choose_server()
    if force_local or server['address']=='local':
        return nl.utils.run(command,products,working_directory,force_local)
    else:
        job = Job(command,products,working_directory)
        if 'password' in server:
            job_return = send_job(job,server['address'],server['port'],server['password'])
        else:
            job_return = send_job(job,server['address'],server['port'])
        return job_return.output

nl.run = _new_run