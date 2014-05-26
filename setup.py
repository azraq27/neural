from distutils.core import setup
setup(
  name = 'neural',
  packages = ['neural'], # this must be the same as the name above
  version = '0.4',
  description = 'Neuroimaing Analysis Library',
  author = 'Bill Gross',
  author_email = 'bill.gross@me.com',
  url = 'https://github.com/azraq27/neural', # use the URL to the github repo
  download_url = 'https://github.com/azraq27/neural/tarball/0.4', # I'll explain this in a second
  keywords = ['neuroimaing', 'afni', 'fsl', 'fmri'], # arbitrary keywords
  classifiers = [
      'Topic :: Scientific/Engineering',
      'Intended Audience :: Science/Research',
      'Development Status :: 3 - Alpha'
  ],
)