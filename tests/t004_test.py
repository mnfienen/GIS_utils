"""Test shapely functionality"""

import cartopy
import fiona
import os
import shapely
from shapely.geos import geos_version



def test_buffer():
    from shapely.geometry import Polygon
    crds = [[45., 571.],
            [144., 669.],
            [225., 596.],
            [234., 594.],
            [552., 576.],
            [567., 807.],
            [960., 789.],
            [939., 407.],
            [419., 49.],
            [314., 56.],
            [296., 102.],
            [252., 240.],
            [243., 263.],
            [230., 283.],
            [196., 329.],
            [166., 376.],
            [138., 413.],
            [109., 445.],
            [73., 496.],
            [54., 542.],
            [45., 571.]]
    result = Polygon(crds).buffer(1000)
    assert result.is_valid

if __name__ == '__main__':
    if not os.path.isdir('temp'):
        os.makedirs('temp')
    try:
        print(cartopy.__version__)
    except:
        pass
    print(fiona.__version__)
    print(shapely.__version__)
    print(geos_version)
    test_buffer()