.. NeurAL documentation master file, created by
   sphinx-quickstart on Thu Feb 20 10:37:29 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to NeurAL's documentation!
==================================

This library is designed to provide easy *shortcut* methods for processing neuroimaging data
with Python. The functions are simply meant as wrappers for different command line programs
and simple functions to replace common scripts.

For a more comprehensive analysis library, see the NIPy project: http://nipy.org

This library is written to try to be generic, wrapping multiple neuroimaging packages, although (because of author bias) it's
currently dominated by AFNI functions.


Usage Example:
===============

Just a quick example of how you might use it::

	import neural as nl
	
	with nl.run_in('data_dir/subject1'):
		nl.calc(['dataset.nii.gz','mask.nii.gz'],'a*step(b)',prefix='dataset_masked.nii.gz')
		nl.thresh('dataset_masked.nii.gz',p=0.005,prefix='dataset_masked_p0.005.nii.gz')
		
		nl.affine_align('anatomy.nii.gz','TT_N27.nii.gz',skull_strip='anatomy.nii.gz')
		nl.affine_apply('dataset_masked_p0.005.nii.gz','anatomy_aff.1D')


General Structure
====================

The library contains several groups of functions, organized into several modules. When using the functions, you can pretty much ignore the
module hierchy (just call :meth:`neural.func` rather than :meth:`neural.module.func`. The modules are primarily there for
conceptual organization and keeping the documentation simple. All of the following modules are imported into the main level,
and don't need to be referred to in code:

:mod:`neural.wrappers`, :mod:`neural.utils`, :mod:`neural.dsets`, :mod:`neural.decon`, :mod:`neural.alignment`,
:mod:`neural.dicom`, :mod:`neural.preprocess`, :mod:`neural.stats`

For example, to call the method :meth:`neural.wrappers.calc`, you just need to call :meth:`neural.calc`

Modules:
======================

Wrapper Functions
--------------------

Wrappers for simple generic functions can be found in the module :mod:`neural.wrappers`. Calling these functions will try
to find an analysis package to implement the function (based on the preferences you set).

Useful Utilities
-------------------

Generic, non-imaging specific methods for useful functions are located in :mod:`neural.utils`. Simple dataset identification and manipulation methods can be found in :mod:`neural.dsets`.

Simple Analysis
------------------

Methods to implement simple analyses are organized by topic. Linear and non-linear alignment methods can be found in :mod:`neural.alignment`. DICOM image manipulation and dataset creation methods are in :mod:`neural.dicom`. Simple preprocessing and dataset statistic methods are in :mod:`neural.preprocess` and :mod:`neural.stats`. Functional connectivity analyses can be found in :mod:`neural.connectivity`.

Other Related Modules
-----------------------

The :mod:`neural.eprime` module can be used to parse E-Prime data files, a program commonly used to present stimuli in fMRI experiments

The :mod:`neural.freesurfer` module has methods to interact with Freesurfer

:mod:`neural.driver` contains methods to control the AFNI GUI. Particularly useful if you want to automate doing things like taking screenshots

Contents
=========

.. toctree::
   :maxdepth: 2
   
   wrappers
   utils
   dsets
   decon
   alignment
   dicom
   preprocess
   stats
   eprime
   freesurfer
   connectivity
   driver
   

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

