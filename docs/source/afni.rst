neural.afni - Wrapper methods for AFNI functions
==================================================

.. automodule:: neural.afni
	
Generic Utilities
------------------------
.. automethod:: neural.afni.prefix

.. automethod:: neural.afni.suffix

.. automethod:: neural.afni.subbrick

.. automethod:: neural.afni.calc

.. automethod:: neural.afni.cdf

.. automethod:: neural.auto_polort

.. automethod:: neural.afni.thresh_at

.. automethod:: neural.afni.voxel_count

.. automethod:: neural.afni.dset_info

.. autoclass:: neural.afni.DsetInfo
	:members:	

.. automethod:: neural.afni.afni_copy

.. automethod:: neural.afni.nifti_copy

.. autoclass:: neural.afni.temp_afni_copy
	:members:
	
.. autoclass:: neural.afni.skull_strip

Deconvolution Helpers
----------------------------
	
.. autoclass:: neural.afni.Decon
	:members:

Alignment Helpers
--------------------------
	
.. automethod:: neural.afni.align_epi_anat

.. automethod:: neural.afni.qwarp_align	

.. automethod:: neural.afni.qwarp_apply

.. automethod:: neural.afni.qwarp_invert

.. automethod:: neural.afni.volreg

.. automethod:: neural.afni.affine_align

.. automethod:: neural.afni.tshift


Simple Analyses
------------------

.. automethod:: neural.afni.create_censor_file
