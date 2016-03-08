'''Control AFNI GUI'''
import neural as nl

def driver_send(command,hostname=None):
    '''Send a command (or ``list`` of commands) to AFNI at ``hostname`` (defaults to local host)
    Requires plugouts enabled (open afni with ``-yesplugouts`` or set ``AFNI_YESPLUGOUTS = YES`` in ``.afnirc``)'''
    cmd = ['plugout_drive']
    if hostname:
        cmd += ['-host',hostname]
    if isinstance(command,basestring):
        command = [command]
    cmd += [['-com',x] for x in command] + ['-quit']
    nl.run(cmd,quiet=None,stderr=None)

def save_image(filename,view='axial',type='png',hostname=None):
    '''Save currently open AFNI view ``view`` to ``filename`` using ``type`` (``png`` or ``jpeg``)'''
    driver_send("SAVE_%s %simage %s" % (type.upper(),view.lower(),filename),hostname=hostname)

def set_thresh(thresh,p=False,hostname=None):
    '''Sets the level of the threshold slider.
    If ``p==True`` will be interpreted as a _p_-value'''
    driver_send("SET_THRESHNEW %s *%s" % (str(thresh),"p" if p else ""),hostname=hostname)

class coord:
    '''enum of coordinate types'''
    dicom = 'DICOM_XYZ'
    rai = 'DICOM_XYZ'
    spm = 'SPM_XYZ'
    ijk = 'IJK'

def set_coord(x,y,z,type=coord.dicom):
    driver_send("SET_%s %f %f %f" % (type,x,y,z))

class xhairs:
    '''enum of xhairs modes'''
    pass
for v in ["OFF", "SINGLE", "MULTI", "LR_AP", "LR_IS", "AP_IS", "LR", "AP", "IS"]:
    setattr(xhairs,v,v)
    setattr(xhairs,v.lower(),v)

def set_xhairs(value=xhairs.off):
    driver_send("SET_XHAIRS A.%s" % value)
