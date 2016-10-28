'''calculate statistics off of datasets'''
import neural as nl
import subprocess
import nibabel as nib

def max(dset):
    '''max value of dataset

    Calculated by reading the dataset. If it's in the header, you can also read
    this from `dset_info`'''
    return nib.load(dset).get_data().max()

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

def mask_average(dset,mask):
    '''Returns average of voxels in ``dset`` within non-zero voxels of ``mask``'''
    o = nl.run(['3dmaskave','-q','-mask',mask,dset])
    if o:
        return float(o.output.split()[-1])

def sphere_average(dset,x,y,z,radius=1):
    '''returns a list of average values (one for each subbrick/time point) within the coordinate ``(x,y,z)`` (in RAI order) using a sphere of radius ``radius`` in ``dset``'''
    return_list = []
    if isinstance(dset,basestring):
        dset = [dset]
    for d in dset:
        return_list += [float(a) for a in subprocess.check_output(['3dmaskave','-q','-dball',str(x),str(y),str(z),str(radius),d],stderr=subprocess.PIPE).split()]
    return return_list
