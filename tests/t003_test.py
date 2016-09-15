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
from GISio import get_values_at_points

#inraster = 'D:/ATLData/USFS/GreatDivide/dem/dem_utm_ft'
inraster = 'data/dem.tif'
outpath = 'temp/'

if not os.path.isdir('temp'):
    os.makedirs('temp')

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

def test_get_values_at_points():
    points = [(627794.58, 5185709.21),
              (629230.86, 5184331.56)]
    vals = [797.91, 996.01]
    vals2 = get_values_at_points('data/dem.tif', points)
    for v1, v2 in zip(vals, vals2):
        assert np.abs(v1 - v2) < 0.01

if __name__ == '__main__':
    #test_clip()
    test_get_values_at_points()


