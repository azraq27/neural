''' wrapper functions for FSL programs '''
import neural as nl

fsl_dir = None
bet2 = None

def skull_strip(dset,suffix='_ns'):
    ''' use bet to strip skull from given anatomy '''
    # should add options to use betsurf and T1/T2 in the future
    out_dset = nl.afni.suffix(dset,suffix)
    cmd = bet2 if bet2 else 'bet2'
    cmd = os.path.join(fsl_dir,cmd) if fsl_dir else cmd
    nl.run([cmd,dset,out_dset],products=out_dset)