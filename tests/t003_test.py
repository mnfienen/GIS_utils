"""
Test raster functionality
"""
import sys
sys.path.insert(0, '..')
import os
import numpy as np
import fiona
from shapely.geometry import mapping, shape, box
from GISops import clip_raster

#inraster = 'D:/ATLData/USFS/GreatDivide/dem/dem_utm_ft'
inraster = 'data/dem.tif'
outpath = 'temp/'


def test_clip():
    import rasterio

    with fiona.open('data/test_area.shp') as shp:
        geoms = [feature['geometry'] for feature in shp]
    clip_raster(inraster, geoms, outpath + 'clipped.tif')
    clip_raster(inraster, 'data/test_area.shp', outpath + 'clipped2.tif')
    with rasterio.open(outpath + 'clipped.tif') as src1:
        a1 = src1.read(1)
        with rasterio.open(outpath + 'clipped2.tif') as src2:
            a2 = src2.read(1)
            assert np.array_equal(a1, a2)

if __name__ == '__main__':
    if not os.path.isdir('temp'):
        os.makedirs('temp')
    test_imports()
    test_clip()


