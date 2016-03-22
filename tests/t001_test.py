import sys
sys.path.insert(0, '..')
import os
import numpy as np
import pandas as pd
from shapely.geometry import Point
from GISio import shp_properties
from GISio import df2shp, shp2df

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
    df2shp(df, 'temp/junk.dbf')
    df = shp2df('temp/junk.dbf', true_values='True', false_values='False')
    assert [d.name for d in df.dtypes] == ['bool', 'object', 'int64', 'float64']
    assert df.isTrue.sum() == 50

    # test with geometry
    df = pd.DataFrame({'reach': np.arange(1, 101, dtype=int), 'value': np.arange(100, dtype=float),
                       'name': ['stuff{}'.format(i) for i in np.arange(100)],
                       'geometry': [Point([i, i]) for i in range(100)]})
    original_columns = df.columns.tolist()
    df2shp(df, 'temp/junk.shp')
    df = shp2df('temp/junk.shp')
    assert df.geometry[0] == Point([0.0, 0.0])
    assert np.array_equal(df.index.values, np.arange(100)) # check ordering of rows
    assert df.columns.tolist() == original_columns # check column order

    # test datetime handling and retention of index
    df.index = pd.date_range('2016-01-01 1:00:00', '2016-01-01 1:01:39', freq='s')
    df.index.name = 'datetime'
    df2shp(df, 'temp/junk.shp', index=True)
    df = shp2df('temp/junk.shp')
    assert 'datetime' in df.columns
    assert df.datetime[0] == '2016-01-01 01:00:00'

def test_integer_dtypes():

    # verify that pandas is recasting numpy ints as python ints when converting to dict
    # (numpy ints invalid for shapefiles)
    d = pd.DataFrame(np.ones((3, 3)), dtype=int).astype(object).to_dict(orient='records')
    for i in range(3):
        assert isinstance(d[i][0], int)

if __name__ == '__main__':
    if not os.path.isdir('temp'):
        os.makedirs('temp')
    test_shp_properties()
    test_shp_read_and_write()
    test_integer_dtypes()