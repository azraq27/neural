'''quality control functions'''
import neural as nl

def inside_brain(stat_dset,atlas=None,p=0.001):
    '''calculates the percentage of voxels above a statistical threshold inside a brain mask vs. outside it
    
    if ``atlas`` is ``None``, it will try to find ``TT_N27``'''
    if atlas==None:
        atlas = nl.find('TT_N27+tlrc.HEAD')
    if atlas==None:
        atlas = nl.find('TT_N27.nii.gz')
    if atlas==None:
        nl.error('Error: No atlas specified, and I can\'t find "TT_N27"',level=nl.level.error)
        return None
    mask_dset = nl.suffix(stat_dset,'_atlasfrac')
    nl.run(['3dfractionize','-template',nl.strip_subbrick(stat_dset),'-input',nl.calc([atlas],'1+step(a-100)',datum='short'),'-preserve','-clip','0.2','-prefix',mask_dset],products=mask_dset,quiet=True,stderr=None)
    s = nl.roi_stats(mask_dset,nl.thresh(stat_dset,p))
    return s[2]['nzvoxels'] / (s[1]['nzvoxels'] + s[2]['nzvoxels'])