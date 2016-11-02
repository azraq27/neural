'''NeurAL -- Neuroimaging Analysis Library

Library to provide helper functions to make analyzing
neuroimaging data in python a little easier'''

version = '1.2.5'

#! flag to indicate whether most functions should be verbose or not
verbose = True

from notification import level,notify

from utils import *

import wrappers
import wrappers.common
from wrappers.common import *
import wrappers.afni as afni
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
import connectivity
from connectivity import *
import qc
from qc import *

import eprime
import general
import notification
import freesurfer
import driver

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
import sys
if sys.stdout.isatty():
    import personality
    personality.display('greeting')
    personality.set_goodbye()
