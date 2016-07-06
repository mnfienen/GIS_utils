import sys
sys.path.insert(0, '..')
import os
import time
import numpy as np
import pandas as pd
from shapely.geometry import Point
from GISio import shp_properties
from GISio import df2shp, shp2df


def test_imports():
    import fiona
    import rasterio

def test_shp_properties():
    df = pd.DataFrame({'reach': [1], 'value': [1.0], 'name': ['stuff']}, index=[0])
    assert [d.name for d in df.dtypes] == ['object', 'int64', 'float64']
    assert shp_properties(df) == {'name': 'str', 'reach': 'int', 'value': 'float'}

def test_shp_read_and_write():

    if not os.path.isdir('output'):
        os.makedirs('output')

    # test without geometry
    df = pd.DataFrame({'reach': np.arange(10000001, 10000100, dtype=int), 'value': np.arange(1, 100, dtype=float),
                       'name': ['stuff{}'.format(i) for i in np.arange(1, 100)],
                       'isTrue': [True, False] * 49 + [True]})
    cols = ['reach', 'value', 'name', 'isTrue']
    df1 = df[cols] #designate a column order
    ta = time.time()
    df2shp(df1, 'temp/junk.dbf', retain_order=True)
    print("wrote shapefile in {:.6f}s\n".format(time.time() - ta))
    ta = time.time()
    df2 = shp2df('temp/junk.dbf', true_values='True', false_values='False')
    print("read shapefile in {:.6f}s\n".format(time.time() - ta))
    #assert list(df2.columns) == cols
    assert [d.name for d in df2.dtypes] == ['int64', 'float64', 'object', 'bool']
    assert df2.isTrue.sum() == 50

    # test with geometry
    df1 = pd.DataFrame({'reach': np.arange(1, 101, dtype=int), 'value': np.arange(100, dtype=float),
                       'name': ['stuff{}'.format(i) for i in np.arange(100)],
                       'geometry': [Point([i, i]) for i in range(100)]})
    cols = ['reach', 'value', 'name', 'geometry'] # geometry is placed in last column when shp is read in
    df1 = df1[cols]
    df2shp(df1, 'temp/junk.shp', retain_order=True)
    df2 = shp2df('temp/junk.shp')
    assert df2.geometry[0] == Point([0.0, 0.0])
    assert np.array_equal(df2.index.values, np.arange(100)) # check ordering of rows
    assert df2.columns.tolist() == cols # check column order

    # test datetime handling and retention of index
    df.index = pd.date_range('2016-01-01 1:00:00', '2016-01-01 1:01:38', freq='s')
    df.index.name = 'datetime'
    df2shp(df, 'temp/junk.dbf', index=True)
    df = shp2df('temp/junk.dbf')
    assert 'datetime' in df.columns
    assert df.datetime[0] == '2016-01-01 01:00:00'

def test_integer_dtypes():

    # verify that pandas is recasting numpy ints as python ints when converting to dict
    # (numpy ints invalid for shapefiles)
    d = pd.DataFrame(np.ones((3, 3)), dtype=int).astype(object).to_dict(orient='records')
    for i in range(3):
        assert isinstance(d[i][0], int)

def test_large_integers():

    # (e.g. USGS GW site numbers)
    df = pd.DataFrame({'site_no': [424825088223301, 424825088223302, 424825088223303]})
    df2shp(df, 'temp/junk.dbf')
    df = pd.read_csv('../examples/data/gw_field_sites.csv')
    df2shp(df, 'temp/junk.dbf')

if __name__ == '__main__':
    if not os.path.isdir('temp'):
        os.makedirs('temp')
    test_shp_properties()
    test_shp_read_and_write()
    test_integer_dtypes()
    test_large_integers()