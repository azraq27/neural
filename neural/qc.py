'''quality control functions'''
import neural as nl
import tempfile,os,sys,shutil,re

def find_atlas(atlas=None):
    if atlas:
        return atlas
    if atlas==None:
        atlas = nl.find('TT_N27+tlrc.HEAD')
    if atlas==None:
        atlas = nl.find('TT_N27.nii.gz')
    if atlas==None:
        nl.error('Error: No atlas specified, and I can\'t find "TT_N27"',level=nl.level.error)
        return None
    return atlas

def inside_brain(stat_dset,atlas=None,p=0.001):
    '''calculates the percentage of voxels above a statistical threshold inside a brain mask vs. outside it
    
    if ``atlas`` is ``None``, it will try to find ``TT_N27``'''
    atlas = find_atlas(atlas)
    if atlas==None:
        return None
    mask_dset = nl.suffix(stat_dset,'_atlasfrac')
    nl.run(['3dfractionize','-template',nl.strip_subbrick(stat_dset),'-input',nl.calc([atlas],'1+step(a-100)',datum='short'),'-preserve','-clip','0.2','-prefix',mask_dset],products=mask_dset,quiet=True,stderr=None)
    s = nl.roi_stats(mask_dset,nl.thresh(stat_dset,p))
    return 100.0 * s[2]['nzvoxels'] / (s[1]['nzvoxels'] + s[2]['nzvoxels'])

def atlas_overlap(dset,atlas=None):
    '''aligns ``dset`` to the TT_N27 atlas and returns ``(cost,overlap)``'''
    atlas = find_atlas(atlas)
    if atlas==None:
        return None
    
    cost_func = 'crM'
    infile = os.path.abspath(dset)
    tmpdir = tempfile.mkdtemp()
    with nl.run_in(tmpdir):
        o = nl.run(['3dAllineate','-verb','-base',atlas,'-source',infile + '[0]','-NN','-final','NN','-cost',cost_func,'-nmatch','20%','-onepass','-fineblur','2','-cmass','-prefix','test.nii.gz'])
        m = re.search(r'Final\s+cost = ([\d.]+) ;',o.output)
        if m:
            cost = float(m.group(1))
        o = nl.run(['3dmaskave','-mask',atlas,'-q','test.nii.gz'],stderr=None)
        data_thresh = float(o.output) / 4
        i = nl.dset_info('test.nii.gz')
        o = nl.run(['3dmaskave','-q','-mask','SELF','-sum',nl.calc([atlas,'test.nii.gz'],'equals(step(a-10),step(b-%.2f))'%data_thresh)],stderr=None)
        overlap = 100*float(o.output) / (i.voxel_dims[0]*i.voxel_dims[1]*i.voxel_dims[2])
    try:
        shutil.rmtree(tmpdir)
    except:
        pass
    return (cost,overlap)

def outcount(dset,fraction=0.1):
    '''gets outlier count and returns ``(list of proportion of outliers by timepoint,total percentage of outlier time points)'''
    polort = nl.auto_polort(dset)
    info = nl.dset_info(dset)
    o = nl.run(['3dToutcount','-fraction','-automask','-polort',polort,dset],stderr=None,quiet=None)
    if o.return_code==0 and o.output:
        oc = [float(x) for x in o.output.split('\n') if x.strip()!='']
        binary_outcount = [x<fraction for x in oc]
        perc_outliers = 1 - (sum(binary_outcount)/float(info.reps))
        return (oc,perc_outliers)

def temporal_snr(signal_dset,noise_dset,mask=None,prefix='temporal_snr.nii.gz'):
    '''Calculates temporal SNR by dividing average signal of ``signal_dset`` by SD of ``noise_dset``.
    ``signal_dset`` should be a dataset that contains the average signal value (i.e., nothing that has
    been detrended by removing the mean), and ``noise_dset`` should be a dataset that has all possible
    known signal fluctuations (e.g., task-related effects) removed from it (the residual dataset from a 
    deconvolve works well)'''
    for d in [('mean',signal_dset), ('stdev',noise_dset)]:
        new_d = nl.suffix(d[1],'_%s' % d[0])
        cmd = ['3dTstat','-%s' % d[0],'-prefix',new_d]
        if mask:
            cmd += ['-mask',mask]
        cmd += [d[1]]
        nl.run(cmd,products=new_d)
    nl.calc([nl.suffix(signal_dset,'_mean'),nl.suffix(noise_dset,'_stdev')],'a/b',prefix=prefix)

def auto_qc(dset,inside_perc=60,atlas=None,p=0.001):
    '''returns ``False`` if ``dset`` fails minimum checks, or returns a float from ``0.0`` to ``100.0`` describing data quality'''
    with nl.notify('Running quality check on %s:' % dset):
        if not os.path.exists(dset):
            nl.notify('Error: cannot find the file!',level=nl.level.error)
            return False
        
        info = nl.dset_info(dset)
        if not info:
            nl.notify('Error: could not read the dataset!',level=nl.level.error)
        
        if any(['stat' in x for x in info.subbricks]):
            with nl.notify('Statistical results detected...'):
                inside = inside_brain(dset,atlas=atlas,p=p)
                nl.notify('%.1f significant voxels inside brain')
                if inside<inside_perc:
                    nl.notify('Warning: below quality threshold!',level=nl.level.warning)
#                    return False
                nl.notify('Looks ok')
                return inside
        
        if len(info.subbricks)>1:
            with nl.notify('Time-series detected...'):
                return_val = True
                (cost,overlap) = atlas_overlap(dset)
                if cost>0.15 or overlap<80:
                    nl.notify('Warning: does not appear to conform to brain dimensions',level=nl.level.warning)
                    return_val = False
                if len(info.subbricks)>5:
                    (oc,perc_outliers) = outcount(dset)
                    if perc_outliers>0.1:
                        nl.notify('Warning: large amount of outlier time points',level=nl.level.warning)
                        return_val = False
            if return_val:
                nl.notify('Looks ok')
                return min(100*(1-cost),overlap,100*perc_outliers)
            return False
        
        with nl.notify('Single brain image detected...'):
            (cost,overlap) = atlas_overlap(dset)
            # Be more lenient if it's not an EPI, cuz who knows what else is in this image
            if cost>0.45 or overlap<70:
                nl.notify('Warning: does not appear to conform to brain dimensions',level=nl.level.warning)
                return False
            nl.notify('Looks ok')
            return min(100*(1-cost),overlap)