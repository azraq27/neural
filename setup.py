from distutils.core import setup
setup(
  name = 'neural-fmri',
  packages = ['neural'], # this must be the same as the name above
  version = '0.4.6',
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
  download_url = 'https://github.com/azraq27/neural/tarball/0.4.5',
  keywords = ['neuroimaging', 'afni', 'fsl', 'fmri'],
  classifiers = [
      'Topic :: Scientific/Engineering',
      'Intended Audience :: Science/Research',
      'Development Status :: 3 - Alpha'
  ],
)
