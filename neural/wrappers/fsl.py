import neural as nl
import os

fsl_dir = None

def find_app(name):
    app = nl.which(name)
    if app==None:
        app = nl.which('fsl5.0-' + name)
    return app

# Try to find bet
bet2 = find_app('bet2')
fast = find_app('fast')

def segment(dset):
    nl.run([fast,dset])

def binary_available():
    if nl.which(bet2):
        return True

def skull_strip(dset,suffix='_ns',prefix=None,unifize=True):
    ''' use bet to strip skull from given anatomy '''
    # should add options to use betsurf and T1/T2 in the future
    # Since BET fails on weirdly distributed datasets, I added 3dUnifize in... I realize this makes this dependent on AFNI. Sorry, :)
    if prefix==None:
        prefix = nl.suffix(dset,suffix)
    unifize_dset = nl.suffix(dset,'_u')
    cmd = bet2 if bet2 else 'bet2'
    if unifize:
        info = nl.dset_info(dset)
        if info==None:
            nl.notify('Error: could not read info for dset %s' % dset,level=nl.level.error)
            return False
        cmd = os.path.join(fsl_dir,cmd) if fsl_dir else cmd
        cutoff_value = nl.max(dset) * 0.05
        nl.run(['3dUnifize','-prefix',unifize_dset,nl.calc(dset,'step(a-%f)*a' % cutoff_value)],products=unifize_dset)
    else:
        unifize_dset = dset
    nl.run([cmd,unifize_dset,prefix,'-w',0.5],products=prefix)
