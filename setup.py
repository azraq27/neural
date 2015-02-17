from distutils.core import setup

version = '0.7.1'

setup(
  name = 'neural-fmri',
  packages = ['neural'], # this must be the same as the name above
  version = version,
  description = 'Neuroimaging Analysis Library',
  long_description = '''NeurAL - a neuroimaging analysis library
-------------------------------------------------------

**Documentation and examples:**
http://azraq27.github.com/neural

This library contains helper functions for doing analyses on fMRI data in Python.

In comparison to other Python libraries designed to interact with fMRI data
(e.g., NIPY and PyNIfTI), this library is not intended to interact directly with
the data in any way, just to provide helpful wrapper functions and shortcut methods to
make your life easier.

Since the author uses primarily AFNI, most of the functions are written that way, 
but don't specifically have to be that way...

''',
  author = 'Bill Gross',
  author_email = 'bill.gross@me.com',
  url = 'https://github.com/azraq27/neural',
  download_url = 'https://github.com/azraq27/neural/tarball/'+version, 
  keywords = ['neuroimaging', 'afni', 'fsl', 'fmri'],
  classifiers = [
      'Topic :: Scientific/Engineering',
      'Intended Audience :: Science/Research',
      'Development Status :: 3 - Alpha'
  ],
  install_requires=[
      'pydicom',
      'fuzzywuzzy',
      'python-Levenshtein'
  ]
)
