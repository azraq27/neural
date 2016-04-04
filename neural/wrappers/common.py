'''simple wrappers for external programs

In general, functions are written independent of analysis package (although most of them are only implemented for AFNI right now)'''
import neural as nl
import imp,os

#: Order that packages are checked for methods
pkg_prefs = ['afni','fsl']
#: Specific methods for which the default ``pkg_prefs`` order should be overriden
method_prefs = {
    'skull_strip': 'fsl'
}
pkgs = {}
for pkg in pkg_prefs:
    try:
        source_name = os.path.dirname(__file__) + '/' + pkg+'.py'
        p = imp.load_source(pkg,source_name)
        if p.binary_available():
            pkgs[pkg] = p
    except:
        pass

def pkg_available(pkg_name,required=False):
    '''tests if analysis package is available on this machine (e.g., "afni" or "fsl"), and prints an error if ``required``'''
    if pkg_name in pkgs:
        return True
    if required:
        nl.notify('Error: could not find required analysis package %s' % pkg_name,level=nl.level.error)
    return False

def available_method(method_name):
    '''ruturn the method for earliest package in ``pkg_preferences``, if package is available (based on :meth:`pkg_available`)'''
    pkg_prefs_copy = list(pkg_prefs)
    if method_name in method_prefs:
        pkg_prefs_copy = [method_prefs[method_name]] + pkg_prefs_copy
    for pkg in pkg_prefs_copy:
        if pkg in pkgs:
            if method_name in dir(pkgs[pkg]):
                return getattr(pkgs[pkg],method_name)
    nl.notify('Error: Could not find implementation of %s on this computer' % (method_name),level=nl.level.error)

def calc(dsets,expr,prefix=None,datum=None):
    ''' returns a string of an inline ``3dcalc``-style expression

    ``dsets`` can be a single string, or list of strings. Each string in ``dsets`` will
    be labeled 'a','b','c', sequentially. The expression ``expr`` is used directly

    If ``prefix`` is not given, will return a 3dcalc string that can be passed to another
    AFNI program as a dataset. Otherwise, will create the dataset with the name ``prefix``'''
    return available_method('calc')(dsets,expr,prefix,datum)

def cdf(dset,p):
    ''' converts *p*-values to the appropriate statistic for the specified subbrick '''
    return available_method('cdf')(dset,p)

def thresh(dset,p,positive_only=False,prefix=None):
    ''' returns a string containing an inline ``3dcalc`` command that thresholds the
        given dataset at the specified *p*-value, or will create a new dataset if a
        suffix or prefix is given '''
    return available_method('thresh')(dset,p,positive_only,prefix)

def cluster(dset,min_distance,min_cluster_size,prefix=None):
    '''clusters given ``dset`` connecting voxels ``min_distance``mm away with minimum cluster size of ``min_cluster_size``
    default prefix is ``dset`` suffixed with ``_clust%d``'''
    if prefix==None:
        prefix = nl.suffix(dset,'_clust%d' % min_cluster_size)
    return available_method('cluster')(dset,min_distance,min_cluster_size,prefix)

def blur(dset,fwhm,prefix=None):
    '''blurs ``dset`` with given ``fwhm`` runs 3dmerge to blur dataset to given ``fwhm``
    default ``prefix`` is to suffix ``dset`` with ``_blur%.1fmm``'''
    if prefix==None:
        prefix = nl.suffix(dset,'_blur%.1fmm'%fwhm)
    return available_method('blur')(dset,fwhm,prefix)

def roi_stats(mask,dset):
    '''returns ROI stats on ``dset`` using ``mask`` as the ROI mask
    returns a dictionary with the structure::

        {
            ROI: {
                {keys: stat}
                    ...
            },
            ...
        }

    keys::

        :mean:
        :median:
        :mode:
        :nzmean:
        :nzmedian:
        :nzmode:
        :nzvoxels:
        :min:
        :max:
        :nzmin:
        :nzmax:
        :sigma:
        :nzsigma:
        :sum:
        :nzsum:
    '''
    return available_method('roi_stats')(mask,dset)

def tshift(dset,suffix='_tshft',initial_ignore=3):
    '''applies slice-time based interpolation of raw data'''
    return available_method('tshift')(dset,suffix,initial_ignore)

def skull_strip(dset,suffix='_ns',prefix=None,unifize=True):
    '''attempts to cleanly remove skull from ``dset``'''
    return available_method('skull_strip')(dset,suffix,prefix,unifize)

def segment(dset):
    '''segment ``dset`` into WM/GM/CSF'''
    return available_method('segment')(dset)
