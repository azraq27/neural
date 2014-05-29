''' generic imaging routines not specifically tied to any analysis packages '''

import nibabel as nib

class Analyze:
    ''' class to do arbitrary analyses on datasets
    
    Basically just a wrapper for NiBabel
    '''
    def __init__(self,dset=None):
        '''if ``dset`` is given, will automatically be loaded'''
        self.dset_filename = dset
        self.data = None
        self.header = None
        if dset:
            self.load(dset)
    
    def load(self,dset):
        '''load a dataset from given filename into the object'''
        self.dset_filename = dset
        self.dset = nib.load(dset)
        self.data = self.dset.get_data()
        self.header = self.dset.get_header()
    
    def voxel_loop(self):
        '''iterator that loops through each voxel and yields the coords and time series as a tuple'''
        # Prob not the most efficient, but the best I can do for now:
        for x in xrange(len(self.data)):
            for y in xrange(len(self.data[x])):
                for z in xrange(len(self.data[x][y])):
                    yield ((x,y,z),self.data[x][y][z])