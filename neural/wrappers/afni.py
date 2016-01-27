import neural as nl
import subprocess

def binary_available():
    if nl.which('afni'):
        return True

def calc(dsets,expr,prefix=None,datum=None):
    if isinstance(dsets,basestring):
        dsets = [dsets]
    if prefix:
        cmd = ['3dcalc']
    else:
        cmd = ['3dcalc(']
    
    for i in xrange(len(dsets)):
        cmd += ['-%s'% chr(97+i),dsets[i]]
    cmd += ['-expr',expr]
    if datum:
        cmd += ['-datum',datum]
    
    if prefix:
        cmd += ['-prefix',prefix]
        return nl.run(cmd,products=prefix)
    else:
        cmd += [')']
        return ' '.join(cmd)

def cdf(dset,p):
    info = nl.dset_info(dset)
    if info==None:
        nl.notify('Error: Could not get info for dset %s'%dset, level=nl.level.error)
        return None
    command = ['cdf','-p2t',info.subbricks[0]['stat'],str(p)] + info.subbricks[0]['params']
    return float(subprocess.check_output(command).split()[2])

def thresh(dset,p,positive_only=False,prefix=None):
    t = cdf(dset,p)
    expr = 'step(abs(a)-%f)*a' % t
    if positive_only:
        expr = 'step(a-%f)*a' % t
    return calc(dset,expr,prefix)

def cluster(dset,min_distance,min_cluster_size,prefix):
    nl.run(['3dmerge','-1clust',min_distance,min_cluster_size,'-prefix',prefix,dset],products=prefix)

def blur(dset,fwhm,prefix):
    nl.run(['3dmerge','-1blur_fwhm',fwhm,'-prefix',prefix,dset],products=prefix)

def roi_stats(mask,dset):
    out_dict = {}
    values = [{'Med': 'median', 'Min': 'min', 'Max': 'max', 
               'NZMean': 'nzmean', 'NZSum': 'nzsum', 'NZSigma': 'nzsigma', 
               'Mean': 'mean', 'Sigma': 'sigma', 'Mod': 'mode','NZcount':'nzvoxels'},
              {'NZMod': 'nzmode', 'NZMed': 'nzmedian', 'NZMax': 'nzmax', 'NZMin': 'nzmin','Mean':'mean'}]
    options = [['-nzmean','-nzsum','-nzvoxels','-minmax','-sigma','-nzsigma','-median','-mode'],
               ['-nzminmax','-nzmedian','-nzmode']]
    for i in xrange(len(values)):
        cmd = ['3dROIstats','-1Dformat','-nobriklab','-mask',mask] + options[i] + [dset]
        out = subprocess.check_output(cmd).split('\n')
        header = [(values[i][x.split('_')[0]],int(x.split('_')[1])) for x in out[1].split()[1:]]
        for j in xrange(len(out)/2-1):
            stats = [float(x) for x in out[(j+1)*2+1][1:].split()]
            for s in xrange(len(stats)):
                roi = header[s][1]
                stat_name = header[s][0]
                stat = stats[s]
                if roi not in out_dict:
                    out_dict[roi] = {}
                out_dict[roi][stat_name] = stat
    return out_dict

def tshift(dset,suffix='_tshift',initial_ignore=3):
    nl.run(['3dTshift','-prefix',nl.suffix(dset,suffix),'-ignore',initial_ignore,dset],products=nl.suffix(dset,suffix))

def skull_strip(dset,suffix='_ns'):
    nl.run([
        '3dSkullStrip',
        '-input', dset,
        '-prefix', nl.suffix(dset,suffix),
        '-niter', '400',
        '-ld', '40'
    ],products=nl.suffix(dset,suffix))