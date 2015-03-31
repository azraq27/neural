'''NeurAL -- Neuroimaging Analysis Library

Library to provide helper functions to make analyzing
neuroimaging data in python a little easier'''

version = '1.0'

#! flag to indicate whether most functions should be verbose or not
verbose = True

from notification import level,notify

from utils import *

from .wrappers import *
from decon import *
from alignment import *
from dicom import *
from dsets import *
from preprocess import *
from stats import *

import eprime
import general
import notification

# user customization
import personality
personality.display('greeting')
personality.set_goodbye()