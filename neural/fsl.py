''' wrapper functions for FSL programs '''
import neural as nl

def skull_strip(dset,suffix='_ns'):
    ''' use bet to strip skull from given anatomy '''
    # should add options to use betsurf and T1/T2 in the future
    out_dset = nl.afni.suffix(dset,suffix)
    nl.run(['bet2',dset,out_dset],products=out_dset)