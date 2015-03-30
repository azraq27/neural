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


General Structure
====================

The library contains several groups of functions, organized into several modules. The modules are primarily there for
conceptual organization and keeping the documentation simple. All of the following modules are imported into the main level,
and don't need to be referred to in code:

	* :mod:`neural.wrappers`
	* :mod:`neural.utils`
	* :mod:`neural.dsets`
	* :mod:`neural.decon`
	* :mod:`neural.alignment`
	* :mod:`neural.dicom`
	* :mod:`neural.preprocess`
	* :mod:`neural.stats`

For example, to call the method :meth:`neural.wrappers.calc`, you just need to call :meth:`neural.calc`

Wrapper Functions
--------------------

Wrappers for simple generic functions can be found in the module :mod:`neural.wrappers`. Calling these functions will try
to find an analysis package to implement the function (based on the preferences you set).

Useful Utilities
-------------------

Generic, non-imaging specific methods for useful functions are located in :mod:`neural.utils`. Simple dataset identification and manipulation methods can be found in :mod:`neural.dsets`.

Simple Analysis
------------------

Methods to implement simple analyses are organized by topic. Linear and non-linear alignment methods can be found in :mod:`neural.alignment`. DICOM image manipulation and dataset creation methods are in :mod:`neural.dicom`. Simple preprocessing and dataset statistic methods are in :mod:`neural.preprocess` and :mod:`neural.stats`

Other Related Modules
-----------------------

The :mod:`neural.eprime` module can be used to parse E-Prime data files, a program commonly used to present stimuli in fMRI experiments

Contents
=========

.. toctree::
   :maxdepth: 2
   
   top_level
   wrappers
   utils
   dsets
   decon
   alignment
   dicom
   preprocess
   stats
   eprime
   

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

