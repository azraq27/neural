'''calculate statistics off of datasets'''
import neural as nl
import subprocess

def voxel_count(dset,p=None,positive_only=False,mask=None,ROI=None):
    ''' returns the number of non-zero voxels
    
    :p:             threshold the dataset at the given *p*-value, then count
    :positive_only: only count positive values
    :mask:          count within the given mask
    :ROI:           only use the ROI with the given value (or list of values) within the mask
                    if ROI is 'all' then return the voxel count of each ROI
                    as a dictionary
    '''
    if p:
        dset = nl.thresh(dset,p,positive_only)
    else:
        if positive_only:
            dset = nl.calc(dset,'step(a)')
    
    count = 0
    devnull = open(os.devnull,"w")
    if mask:
        cmd = ['3dROIstats','-1Dformat','-nomeanout','-nobriklab', '-nzvoxels']
        cmd += ['-mask',str(mask),str(dset)]
        out = subprocess.check_output(cmd,stderr=devnull).split('\n')
        if len(out)<4:
            return 0
        rois = [int(x.replace('NZcount_','')) for x in out[1].strip()[1:].split()]
        counts = [int(x.replace('NZcount_','')) for x in out[3].strip().split()]
        count_dict = None
        if ROI==None:
            ROI = rois
        if ROI=='all':
            count_dict = {}
            ROI = rois
        else:
            if not isinstance(ROI,list):
                ROI = [ROI]
        for r in ROI:
            if r in rois:
                roi_count = counts[rois.index(r)]
                if count_dict!=None:
                    count_dict[r] = roi_count
                else:
                    count += roi_count
    else:
        cmd = ['3dBrickStat', '-slow', '-count', '-non-zero', str(dset)]
        count = int(subprocess.check_output(cmd,stderr=devnull).strip())
    if count_dict:
        return count_dict
    return count

def temporal_snr(signal_dset,noise_dset,mask=None,prefix='temporal_snr.nii.gz'):
    '''Calculates temporal SNR by dividing average signal of ``signal_dset`` by SD of ``noise_dset``.
    ``signal_dset`` should be a dataset that contains the average signal value (i.e., nothing that has
    been detrended by removing the mean), and ``noise_dset`` should be a dataset that has all possible
    known signal fluctuations (e.g., task-related effects) removed from it (the residual dataset from a 
    deconvolve works well)'''
    for d in [('mean',signal_dset), ('stdev',noise_dset)]:
        new_d = suffix(d[1],'_%s' % d[0])
        cmd = ['3dTstat','-%s' % d[0],'-prefix',new_d]
        if mask:
            cmd += ['-mask',mask]
        cmd += [d[1]]
        nl.run(cmd,products=new_d)
    nl.calc([suffix(signal_dset,'_mean'),suffix(noise_dset,'_stdev')],'a/b',prefix=prefix)