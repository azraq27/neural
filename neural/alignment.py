import neural as nl
import os

def volreg(dset,suffix='_volreg',base_subbrick=3,tshift=True):
    ''' simple interface to 3dvolreg (recommend looking at align_epi_anat instead of using this) '''
    cmd = ['3dvolreg','-prefix',nl.suffix(dset,suffix),'-base',base_subbrick]
    if tshift:
        cmd += ['-tshift',base_subbrick]
    cmd += [dset]
    nl.run(cmd,products=nl.suffix(dset,suffix))

def affine_align(dset_from,dset_to,skull_strip=True,mask=None,affine_suffix='_aff'):
    ''' interface to 3dAllineate to align anatomies and EPIs '''
    
    dset_ss = lambda dset: os.path.split(nl.suffix(dset,'_ns'))[1]
    def dset_source(dset):      
        if skull_strip==True or skull_strip==dset:
            return dset_ss(dset)
        else:
            return dset
    
    dset_affine = os.path.split(nl.suffix(dset_from,affine_suffix))[1]
    dset_affine_1D = nl.prefix(dset_affine) + '.1D'
        
    if os.path.exists(dset_affine):
        # final product already exists
        return
    
    for dset in [dset_from,dset_to]:
        if skull_strip==True or skull_strip==dset:
            nl.skull_strip(dset,'_ns')
        
    mask_use = mask
    if mask:
        # the mask was probably made in the space of the original dset_to anatomy,
        # which has now been cropped from the skull stripping. So the lesion mask
        # needs to be resampled to match the corresponding mask
        if skull_strip==True or skull_strip==dset_to:
            nl.run(['3dresample','-master',dset_u(dset_ss(dset)),'-inset',mask,'-prefix',nl.suffix(mask,'_resam')],products=nl.suffix(mask,'_resam'))
            mask_use = nl.suffix(mask,'_resam')
    
    all_cmd = [
        '3dAllineate',
        '-prefix', dset_affine,
        '-base', dset_source(dset_to),
        '-source', dset_source(dset_from),
        '-cost', 'lpa',
        '-1Dmatrix_save', dset_affine_1D,
        '-autoweight',
        '-cmass'
    ]
    
    if mask:
        all_cmd += ['-emask', mask_use]
    
    nl.run(all_cmd,products=dset_affine)

def affine_apply(dset_from,affine_1D,master,affine_suffix='_aff',interp='NN',inverse=False,prefix=None):
    '''apply the 1D file from a previously aligned dataset
    Applies the matrix in ``affine_1D`` to ``dset_from`` and makes the final grid look like the dataset ``master``
    using the interpolation method ``interp``. If ``inverse`` is True, will apply the inverse of ``affine_1D`` instead'''
    affine_1D_use = affine_1D
    if inverse:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(subprocess.check_output(['cat_matvec',affine_1D,'-I']))
            affine_1D_use = temp.name
    if prefix==None:
        prefix = nl.suffix(dset_from,affine_suffix)
    nl.run(['3dAllineate','-1Dmatrix_apply',affine_1D_use,'-input',dset_from,'-prefix',prefix,'-master',master,'-final',interp],products=nl.suffix(dset_from,affine_suffix))


def qwarp_align(dset_from,dset_to,skull_strip=True,mask=None,affine_suffix='_aff',qwarp_suffix='_qwarp'):
    '''aligns ``dset_from`` to ``dset_to`` using 3dQwarp
    
    Will run ``3dSkullStrip`` (unless ``skull_strip`` is ``False``), ``3dUnifize``,
    ``3dAllineate``, and then ``3dQwarp``. This method will add suffixes to the input
    dataset for the intermediate files (e.g., ``_ss``, ``_u``). If those files already
    exist, it will assume they were intelligently named, and use them as is
    
    :skull_strip:       If True/False, turns skull-stripping of both datasets on/off.
                        If a string matching ``dset_from`` or ``dset_to``, will only
                        skull-strip the given dataset
    :mask:              Applies the given mask to the alignment. Because of the nature
                        of the alignment algorithms, the mask is **always** applied to
                        the ``dset_to``. If this isn't what you want, you need to reverse
                        the transform and re-apply it (e.g., using :meth:`qwarp_invert` 
                        and :meth:`qwarp_apply`). If the ``dset_to`` dataset is skull-stripped,
                        the mask will also be resampled to match the ``dset_to`` grid.
    :affine_suffix:     Suffix applied to ``dset_from`` to name the new dataset, as well as
                        the ``.1D`` file.
    :qwarp_suffix:      Suffix applied to the final ``dset_from`` dataset. An additional file
                        with the additional suffix ``_WARP`` will be created containing the parameters
                        (e.g., with the default ``_qwarp`` suffix, the parameters will be in a file with
                        the suffix ``_qwarp_WARP``)
    
    The output affine dataset and 1D, as well as the output of qwarp are named by adding
    the given suffixes (``affine_suffix`` and ``qwarp_suffix``) to the ``dset_from`` file
    
    If ``skull_strip`` is a string instead of ``True``/``False``, it will only skull strip the given
    dataset instead of both of them
    
    # TODO: currently does not work with +tlrc datasets because the filenames get mangled
    '''
    
    dset_ss = lambda dset: os.path.split(nl.suffix(dset,'_ns'))[1]
    dset_u = lambda dset: os.path.split(nl.suffix(dset,'_u'))[1]
    def dset_source(dset):      
        if skull_strip==True or skull_strip==dset:
            return dset_ss(dset)
        else:
            return dset
    
    dset_affine = os.path.split(nl.suffix(dset_from,affine_suffix))[1]
    dset_affine_1D = nl.prefix(dset_affine) + '.1D'
    dset_qwarp = os.path.split(nl.suffix(dset_from,qwarp_suffix))[1]
    
    if os.path.exists(dset_qwarp):
        # final product already exists
        return
    
    affine_align(dset_from,dset_to,skull_strip,mask,affine_suffix)
      
    for dset in [dset_from,dset_to]:  
        nl.run([
            '3dUnifize',
            '-prefix', dset_u(dset_source(dset)),
            '-input', dset_source(dset)
        ],products=[dset_u(dset_source(dset))])
    
    mask_use = mask
    if mask:
        # the mask was probably made in the space of the original dset_to anatomy,
        # which has now been cropped from the skull stripping. So the lesion mask
        # needs to be resampled to match the corresponding mask
        if skull_strip==True or skull_strip==dset_to:
            nl.run(['3dresample','-master',dset_u(dset_ss(dset)),'-inset',mask,'-prefix',nl.suffix(mask,'_resam')],products=nl.suffix(mask,'_resam'))
            mask_use = nl.suffix(mask,'_resam')
    
    warp_cmd = [
        '3dQwarp',
        '-prefix', dset_qwarp,
        '-duplo', '-useweight', '-blur', '0', '3',
        '-iwarp',
        '-base', dset_u(dset_source(dset_to)),
        '-source', dset_affine
    ]
    
    if mask:
        warp_cmd += ['-emask', mask_use]
    
    nl.run(warp_cmd,products=dset_qwarp)

def qwarp_apply(dset_from,dset_warp,affine=None,warp_suffix='_warp',master='WARP',interp=None):
    '''applies the transform from a previous qwarp
    
    Uses the warp parameters from the dataset listed in 
    ``dset_warp`` (usually the dataset name ends in ``_WARP``) 
    to the dataset ``dset_from``. If a ``.1D`` file is given
    in the ``affine`` parameter, it will be applied simultaneously
    with the qwarp.
    
    If the parameter ``interp`` is given, will use as interpolation method,
    otherwise it will just use the default (currently wsinc5)
    
    Output dataset with have the ``warp_suffix`` suffix added to its name
    '''
    out_dset = os.path.split(nl.suffix(dset_from,warp_suffix))[1]
    dset_from_info = nl.dset_info(dset_from)
    dset_warp_info = nl.dset_info(dset_warp)
    if(dset_from_info.orient!=dset_warp_info.orient):
        # If the datasets are different orientations, the transform won't be applied correctly
        nl.run(['3dresample','-orient',dset_warp_info.orient,'-prefix',nl.suffix(dset_from,'_reorient'),'-inset',dset_from],products=nl.suffix(dset_from,'_reorient'))
        dset_from = nl.suffix(dset_from,'_reorient')
    warp_opt = str(dset_warp)
    if affine:
        warp_opt += ' ' + affine
    cmd = [
        '3dNwarpApply',
        '-nwarp', warp_opt]
    cmd += [
        '-source', dset_from,
        '-master',master,
        '-prefix', out_dset
    ]
    
    if interp:
        cmd += ['-interp',interp]
    
    nl.run(cmd,products=out_dset)

def qwarp_invert(warp_param_dset,output_dset,affine_1Dfile=None):
    '''inverts a qwarp (defined in ``warp_param_dset``) (and concatenates affine matrix ``affine_1Dfile`` if given)
    outputs the inverted warp + affine to ``output_dset``'''
    
    cmd = ['3dNwarpCat','-prefix',output_dset]
    
    if affine_1Dfile:
        cmd += ['-warp1','INV(%s)' % affine_1Dfile, '-warp2','INV(%s)' % warp_param_dset]
    else:
        cmd += ['-warp1','INV(%s)' % warp_param_dset]
            
    nl.run(cmd,products=output_dset)

def align_epi_anat(anatomy,epi_dsets,skull_strip_anat=True):
    ''' aligns epis to anatomy using ``align_epi_anat.py`` script
    
    :epi_dsets:       can be either a string or list of strings of the epi child datasets
    :skull_strip_anat:     if ``True``, ``anatomy`` will be skull-stripped using the default method
    
    The default output suffix is "_al"
    '''
    
    if isinstance(epi_dsets,basestring):
        epi_dsets = [epi_dsets]
    
    if len(epi_dsets)==0:
        nl.notify('Warning: no epi alignment datasets given for anatomy %s!' % anatomy,level=nl.level.warning)
        return
    
    if all(os.path.exists(nl.suffix(x,'_al')) for x in epi_dsets):
        return
    
    anatomy_use = anatomy
    
    if skull_strip_anat:
        nl.skull_strip(anatomy,'_ns')
        anatomy_use = nl.suffix(anatomy,'_ns')
    
    inputs = [anatomy_use] + epi_dsets
    dset_products = lambda dset: [nl.suffix(dset,'_al'), nl.prefix(dset)+'_al_mat.aff12.1D', nl.prefix(dset)+'_tsh_vr_motion.1D']
    products = nl.flatten([dset_products(dset) for dset in epi_dsets])
    with nl.run_in_tmp(inputs,products): 
        if nl.is_nifti(anatomy_use):
            anatomy_use = nl.afni_copy(anatomy_use)
        epi_dsets_use = []
        for dset in epi_dsets:
            if nl.is_nifti(dset):
                epi_dsets_use.append(nl.afni_copy(dset))
            else:
                epi_dsets_use.append(dset)
        cmd = ["align_epi_anat.py", "-epi2anat", "-anat_has_skull", "no", "-epi_strip", "3dAutomask","-anat", anatomy_use, "-epi_base", "5", "-epi", epi_dsets_use[0]]
        if len(epi_dsets_use)>1:
            cmd += ['-child_epi'] + epi_dsets_use[1:]
            out = nl.run(cmd)
        
        for dset in epi_dsets:
            if nl.is_nifti(dset):
                dset_nifti = nl.nifti_copy(nl.prefix(dset)+'_al+orig')
                if dset_nifti and os.path.exists(dset_nifti) and dset_nifti.endswith('.nii') and dset.endswith('.gz'):
                    nl.run(['gzip',dset_nifti])