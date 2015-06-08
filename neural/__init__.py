'''NeurAL -- Neuroimaging Analysis Library

Library to provide helper functions to make analyzing
neuroimaging data in python a little easier'''

version = '1.1'

#! flag to indicate whether most functions should be verbose or not
verbose = True

from notification import level,notify

from utils import *

import wrappers
import wrappers.common
from wrappers.common import *
import decon
from decon import *
import alignment
from alignment import *
import dicom
from dicom import *
import dsets
from dsets import *
import preprocess
from preprocess import *
import stats
from stats import *

import eprime
import general
import notification
import freesurfer

# Check for update
import xmlrpclib
try:
    pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
    latest = pypi.package_releases('neural-fmri')
    if latest:
        if latest[0]!=version:
            notify('## Update to neural available on PyPI (current version: %s; latest version: %s)' % (version,latest[0]),level=level.debug)
except:
    pass
    

# user customization
import personality
personality.display('greeting')
personality.set_goodbye()