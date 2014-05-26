from distutils.core import setup
setup(
  name = 'neural-fmri',
  packages = ['neural-fmri'], # this must be the same as the name above
  version = '0.4',
  description = 'Neuroimaging Analysis Library',
  long_description = open('README.md').read(),
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