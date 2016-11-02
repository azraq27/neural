import neural as nl
import subprocess

def create_censor_file(input_dset,out_prefix=None,fraction=0.1,clip_to=0.1,max_exclude=0.3,motion_file=None,motion_exclude=1.0):
    '''create a binary censor file using 3dToutcount

    :input_dset:        the input dataset
    :prefix:            output 1D file (default: ``prefix(input_dset)`` + ``.1D``)
    :fraction:          censor a timepoint if proportional of outliers in this
                        time point is greater than given value
    :clip_to:           keep the number of time points censored under this proportion
                        of total reps. If more time points would be censored,
                        it will only pick the top ``clip_to*reps`` points
    :max_exclude:       if more time points than the given proportion of reps are excluded for the
                        entire run, throw an exception -- something is probably wrong
    :motion_file:       optional filename of a "motion" file with multiple columns and rows corresponding to reps.
                        It doesn't really matter what the values are, as long as they are appropriate relative to ``motion_exclude``
    :motion_exclude:    Will exclude any reps that have a value greater than this in any column of ``motion_file``
    '''
    (outcount,perc_outliers) = nl.qc.outcount(input_dset,fraction)
    info = nl.dset_info(input_dset)
    binarize = lambda o,f: [oo<f for oo in o]
    perc_outliers = lambda o: 1.-(sum(o)/float(info.reps))

    if motion_file:
        with open(motion_file,'Ur') as f:
            motion = [max([float(y) for y in x.strip().split()]) for x in f.read().split('\n') if len(x.strip())>0 and x.strip()[0]!='#']
            motion_1D = [x for x in binarize(motion,motion_exclude)]
            if perc_outliers(motion_1D) > max_exclude:
                nl.notify('Error: Too many points excluded because of motion (%.2f) in dset %s' % (perc_outliers(motion_1D),input_dset),level=nl.level.error)
                return False
            outcount = [outcount[i] if motion_1D[i] else 1. for i in range(len(outcount))]

    binary_outcount = binarize(outcount,fraction)

    if max_exclude and perc_outliers(binary_outcount) > max_exclude:
        nl.notify('Error: Found %.1f%% outliers in dset %s' % (100*perc_outliers(outcount),input_dset),level=nl.level.error)
        return False
    if clip_to:
        while perc_outliers(binary_outcount) > clip_to:
            best_outlier = min([(outcount[i],i) for i in range(len(outcount)) if not binary_outcount[i]])
            binary_outcount[best_outlier[1]] = True
    if not out_prefix:
        out_prefix = nl.prefix(input_dset) + '.1D'
    with open(out_prefix,'w') as f:
        f.write('\n'.join([str(int(x)) for x in binary_outcount]))
    return True
