import neural as nl
import subprocess

def create_censor_file(input_dset,out_prefix=None,fraction=0.1,clip_to=0.1,max_exclude=0.3):
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
    '''
    polort = nl.auto_polort(input_dset)
    info = nl.dset_info(input_dset)
    outcount = [float(x) for x in subprocess.check_output(['3dToutcount','-fraction','-automask','-polort',str(polort),str(input_dset)]).split('\n') if len(x.strip())>0]
    binary_outcount = [x<fraction for x in outcount]
    perc_outliers = 1 - (sum(binary_outcount)/float(info.reps))
    if max_exclude and perc_outliers > max_exclude:
        nl.notify('Error: Found %f outliers in dset %s' % (perc_outliers,input_dset),level=nl.level.error)
        return False
    if clip_to:
        while perc_outliers > clip_to:
            best_outlier = min([(outcount[i],i) for i in range(len(outcount)) if binary_outcount[i]])
            binary_outcount[best_outlier[1]] = False
            perc_outliers = sum(binary_outcount)/float(info.reps)
    if not out_prefix:
        out_prefix = nl.prefix(input_dset) + '.1D'
    with open(out_prefix,'w') as f:
        f.write('\n'.join([str(int(x)) for x in binary_outcount]))