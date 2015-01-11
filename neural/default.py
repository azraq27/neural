'''default functions to use, choosing my personal preferences when multiple packages offer the same function'''

# Import everything, default to AFNI for any conflicts
from neural.fsl import *
from neural.afni import *

# Specfic overrides
from neural.fsl import skull_strip