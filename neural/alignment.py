import neural as nl
import os,tempfile,subprocess,shutil
from math import sqrt
from operator import add
import numpy as np

def align_epi(anatomy,epis,suffix='_al',base=3,skull_strip=True):
    '''[[currently in progress]]: a simple replacement for the ``align_epi_anat.py`` script, because I've found it to be unreliable, in my usage'''
    for epi in epis:
        nl.tshift(epi,suffix='_tshift')
        nl.affine_align(nl.suffix(epi,'_tshift'),'%s[%d]'%(epis[0],base),skull_strip=False,epi=True,cost='crM',resample='wsinc5',grid_size=nl.dset_info(epi).voxel_size[0],suffix='_al')
    ss = [anatomy] if skull_strip else False
    nl.affine_align(anatomy,'%s[%d]'%(epis[0],base),skull_strip=ss,cost='hel',grid_size=1,opts=['-interp','cubic'],suffix='_al-to-EPI')

def motion_from_params(param_file,motion_file,individual=True,rms=True):
    '''calculate a motion regressor from the params file given by 3dAllineate
    
    Basically just calculates the rms change in the translation and rotation components. Returns the 6 motion vector (if ``individual`` is ``True``) and the RMS difference (if ``rms`` is ``True``).'''
    with open(param_file) as inf:
        translate_rotate = np.array([[float(y) for y in x.strip().split()[:6]] for x in inf.readlines() if x[0]!='#'])
        motion = np.array([])
        if individual:
            motion = np.vstack((np.zeros(translate_rotate.shape[1]),np.diff(translate_rotate,axis=0)))
        if rms:
            translate = [sqrt(sum([x**2 for x in y[:3]])) for y in translate_rotate]
            rotate = [sqrt(sum([x**2 for x in y[3:]])) for y in translate_rotate]            
            translate_rotate = np.array(map(add,translate,rotate))
            translate_rotate_diff = np.hstack(([0],np.diff(translate_rotate,axis=0)))
            if motion.shape==(0,):
                motion = rms_motion
            else:
                motion = np.column_stack((motion,translate_rotate_diff))
        with open(motion_file,'w') as outf:
            outf.write('\n'.join(['\t'.join([str(y) for y in x]) for x in motion]))
    
def volreg(dset,suffix='_volreg',base=3,tshift=3,dfile_suffix='_volreg.1D'):
    '''simple interface to 3dvolreg
    
        :suffix:        suffix to add to ``dset`` for volreg'ed file
        :base:          either a number or ``dset[#]`` of the base image to register to
        :tshift:        if a number, then tshift ignoring that many images, if ``None``
                        then don't tshift
        :dfile_suffix:  suffix to add to ``dset`` to save the motion parameters to
    '''
    cmd = ['3dvolreg','-prefix',nl.suffix(dset,suffix),'-base',base,'-dfile',nl.prefix(dset)+dfile_suffix]
    if tshift:
        cmd += ['-tshift',tshift]
    cmd += [dset]
    nl.run(cmd,products=nl.suffix(dset,suffix))

def affine_align(dset_from,dset_to,skull_strip=True,mask=None,suffix='_aff',prefix=None,cost=None,epi=False,resample='wsinc5',grid_size=None,opts=[]):
    ''' interface to 3dAllineate to align anatomies and EPIs '''
    
    dset_ss = lambda dset: os.path.split(nl.suffix(dset,'_ns'))[1]
    def dset_source(dset):      
        if skull_strip==True or skull_strip==dset:
            return dset_ss(dset)
        else:
            return dset
    
    dset_affine = prefix
    if dset_affine==None:
        dset_affine = os.path.split(nl.suffix(dset_from,suffix))[1]
    dset_affine_mat_1D = nl.prefix(dset_affine) + '_matrix.1D'
    dset_affine_par_1D = nl.prefix(dset_affine) + '_params.1D'
        
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
        '-1Dmatrix_save', dset_affine_mat_1D,
        '-1Dparam_save',dset_affine_par_1D,
        '-autoweight',
        '-final',resample,
        '-cmass'
    ] + opts
    if grid_size:
        all_cmd += ['-newgrid',grid_size]
    if cost:
        all_cmd += ['-cost',cost]    
    if epi:
        all_cmd += ['-EPI']
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

def convert_coord(coord_from,matrix_file,base_to_aligned=True):
    '''Takes an XYZ array (in DICOM coordinates) and uses the matrix file produced by 3dAllineate to transform it. By default, the 3dAllineate
    matrix transforms from base to aligned space; to get the inverse transform set ``base_to_aligned`` to ``False``'''
    with open(matrix_file) as f:
        try:
            values = [float(y) for y in ' '.join([x for x in f.readlines() if x.strip()[0]!='#']).strip().split()]
        except:
            nl.notify('Error reading values from matrix file %s' % matrix_file, level=nl.level.error)
            return False
    if len(values)!=12:
        nl.notify('Error: found %d values in matrix file %s (expecting 12)' % (len(values),matrix_file), level=nl.level.error)
        return False
    matrix = np.vstack((np.array(values).reshape((3,-1)),[0,0,0,1]))
    if not base_to_aligned:
        matrix = np.linalg.inv(matrix)
    return np.dot(matrix,list(coord_from) + [1])[:3]
        

def qwarp_align(dset_from,dset_to,skull_strip=True,mask=None,affine_suffix='_aff',suffix='_qwarp',prefix=None):
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
    :suffix:            Suffix applied to the final ``dset_from`` dataset. An additional file
                        with the additional suffix ``_WARP`` will be created containing the parameters
                        (e.g., with the default ``_qwarp`` suffix, the parameters will be in a file with
                        the suffix ``_qwarp_WARP``)
    :prefix:            Alternatively to ``suffix``, explicitly give the full output filename
    
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
    dset_qwarp = prefix
    if dset_qwarp==None:
        dset_qwarp = os.path.split(nl.suffix(dset_from,suffix))[1]
    
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

def qwarp_apply(dset_from,dset_warp,affine=None,warp_suffix='_warp',master='WARP',interp=None,prefix=None):
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
    out_dset = prefix
    if out_dset==None:
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


def qwarp_epi(dset,align_subbrick=5,suffix='_qwal',prefix=None):
    '''aligns an EPI time-series using 3dQwarp
    
    Very expensive and not efficient at all, but it can produce pretty impressive alignment for EPI time-series with significant
    distortions due to motion'''
    info = nl.dset_info(dset)
    if info==None:
        nl.notify('Error reading dataset "%s"' % (dset),level=nl.level.error)
        return False
    if prefix==None:
        prefix = nl.suffix(dset,suffix)
    dset_sub = lambda x: '_tmp_qwarp_epi-%s_%d.nii.gz' % (nl.prefix(dset),x)
    try:
        align_dset = nl.suffix(dset_sub(align_subbrick),'_warp')
        nl.calc('%s[%d]' % (dset,align_subbrick),expr='a',prefix=align_dset,datum='float')
        for i in xrange(info.reps):
            if i != align_subbrick:
                nl.calc('%s[%d]' % (dset,i),expr='a',prefix=dset_sub(i),datum='float')
                nl.run([
                    '3dQwarp', '-nowarp', 
                    '-workhard', '-superhard', '-minpatch', '9', '-blur', '0',
                    '-pear', '-nopenalty',
                    '-base', align_dset,
                    '-source', dset_sub(i),
                    '-prefix', nl.suffix(dset_sub(i),'_warp')
                ],quiet=True)
        cmd = ['3dTcat','-prefix',prefix]
        if info.TR:
            cmd += ['-tr',info.TR]
        if info.slice_timing:
            cmd += ['-tpattern',info.slice_timing]
        cmd += [nl.suffix(dset_sub(i),'_warp') for i in xrange(info.reps)]
        nl.run(cmd,quiet=True)
    except Exception as e:
        raise e
    finally:
        for i in xrange(info.reps):
            for suffix in ['','warp']:
                try:
                    os.remove(nl.suffix(dset_sub(i),suffix))
                except:
                    pass

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

def skullstrip_template(dset,template,prefix=None,suffix=None,dilate=0):
    '''Takes the raw anatomy ``dset``, aligns it to a template brain, and applies a templated skullstrip. Should produce fairly reliable skullstrips as long
    as there is a decent amount of normal brain and the overall shape of the brain is normal-ish'''
    if suffix==None:
        suffix = '_sstemplate'
    if prefix==None:
        prefix = nl.suffix(dset,suffix)
    if not os.path.exists(prefix):
        with nl.notify('Running template-based skull-strip on %s' % dset):
            dset = os.path.abspath(dset)
            template = os.path.abspath(template)
            tmp_dir = tempfile.mkdtemp()
            cwd = os.getcwd()
            with nl.run_in(tmp_dir):
                nl.affine_align(template,dset,skull_strip=None,cost='mi',opts=['-nmatch','100%'])
                nl.run(['3dQwarp','-minpatch','20','-penfac','10','-noweight','-source',nl.suffix(template,'_aff'),'-base',dset,'-prefix',nl.suffix(template,'_qwarp')],products=nl.suffix(template,'_qwarp'))
                info = nl.dset_info(nl.suffix(template,'_qwarp'))
                max_value = info.subbricks[0]['max']    
                nl.calc([dset,nl.suffix(template,'_qwarp')],'a*step(b-%f*0.05)'%max_value,prefix)
                shutil.move(prefix,cwd)
            shutil.rmtree(tmp_dir)