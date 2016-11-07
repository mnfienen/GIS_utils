import os
import glob

cmds = []

cmds.append('conda config --add channels conda-forge')
cmds.append('conda config --add channels defaults')
cmds.append('conda config --set ssl_verify false')
cmds.append('conda config --set show_channel_urls true')

cmds.append('conda create -n gis python=3.4 ipython jupyter numpy matplotlib pandas=0.18 gdal fiona shapely rasterio rtree pyproj netcdf4 rasterstats pyshp basemap descartes datashader nose')

pips = 'activate gis &&'
pips += 'pip install https://github.com/aleaf/GIS_utils/archive/master.zip'

cmds.append(pips)

for cmd in cmds: 
    print(cmd)
    os.system(cmd)

