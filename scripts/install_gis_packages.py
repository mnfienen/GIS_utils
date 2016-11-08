import os
import shutil
try:
    # For Python 3.0 and later
    from urllib.request import urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen
import platform
from subprocess import Popen, PIPE

cmds = []
# set up conda
cmds.append('conda config --add channels conda-forge')
cmds.append('conda config --add channels defaults')
cmds.append('conda config --set ssl_verify false')
cmds.append('conda config --set show_channel_urls true')
# create new environment for the gis packages
cmds.append('conda create -n gis python=3.4 ipython jupyter numpy matplotlib pandas=0.18 gdal fiona shapely rasterio rtree pyproj netcdf4 rasterstats pyshp basemap descartes datashader nose')

# download the DOI certificate (needed for using pip within the DOI network)
# this saves it to the current folder
url = 'http://internal.usgs.gov/oei/wp-content/itsec/DOIRootCA2.cer'
with urlopen(url) as response, open(os.path.split(url)[-1], 'wb') as out_file:
    shutil.copyfileobj(response, out_file)

# pip installs
pips = 'source activate gis &&'
pips += 'pip install https://github.com/aleaf/GIS_utils/archive/master.zip'
#pips += ' --cert={}'.format(os.path.split(url)[-1]) # use the certificate file name from url above

if platform.system() == 'Windows':
    print('Platform: {}'.format(platform.system()))
    pips = pips.replace('source', '')
    print(pips)
    cmds.append(pips)
    
elif platform.system() == 'Darwin':
    pips = '#!/bin/bash\n' + pips
    pips = pips.replace('&&', '\n')
    with open('install.sh', 'w') as input:
        input.write(pips)
    Popen(['chmod', '+x', 'install.sh'], stdout=PIPE, stderr=PIPE)
    cmds.append('./install.sh')

for cmd in cmds: 
    print(cmd)
    os.system(cmd)

