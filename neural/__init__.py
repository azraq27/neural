'''NeurAL -- Neuroimaging Analysis Library

Library to provide helper functions to make analyzing
neuroimaging data in python a little easier'''

version = 0.4

#! flag to indicate whether most functions should be verbose or not
verbose = True

from utils import *

import afni
import fsl
import eprime
import dicom

# functions that are useful/general enough to be on top-level, not in a specific module:
from afni import dset_info,subbrick,cdf,voxel_count,prefix,suffix
