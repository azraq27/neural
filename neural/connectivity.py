'''methods to aide in functional connectivity analyses'''
import neural as nl
import tempfile,os

def connectivity_map(dset,prefix,x,y,z,radius=2):
    '''Will perform connectivity analysis on ``dset`` using seed point ``(x,y,z)`` (in RAI order) with a sphere of radius ``radius``.
    Does not perform any preprocessing of ``dset``. This should be already motion corrected, noise-regressed, residualized, etc.'''
    seed_series = nl.sphere_average(dset,x,y,z,radius)
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write('\n'.join([str(x) for x in seed_series]))
    decon = nl.Decon()
    decon.input_dsets = dset
    decon.stim_files = {'seed':temp.name}
    decon.prefix = prefix
    decon.run()
    try:
        os.remove(temp.name)
    except:
        pass
    