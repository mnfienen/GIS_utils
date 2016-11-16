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
cmds.append('conda config --set ssl_verify false')
cmds.append('conda update conda -y')
cmds.append('conda config --add channels conda-forge')
cmds.append('conda config --add channels defaults')
cmds.append('conda config --set show_channel_urls true')
# create new environment for the gis packages
cmds.append('conda create -n gis2 python=3.4 ipython jupyter numpy matplotlib pandas=0.18 gdal fiona shapely rasterio rtree pyproj netcdf4 rasterstats pyshp basemap descartes datashader nose -y')

for cmd in cmds: 
    print(cmd)
    os.system(cmd)

# download the DOI certificate (needed for using pip within the DOI network)
# this saves it to the current folder
# (won't work outside of the DOI network)
try:
    url = 'http://internal.usgs.gov/oei/wp-content/itsec/DOIRootCA2.cer'
    with urlopen(url) as response, open(os.path.split(url)[-1], 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print('saved {}\nto {}'.format(url, os.path.split(url)[-1]))
except:
    pass

exeloc = {'Windows': 'python',
          'Darwin': os.path.join('bin', 'python')}

# get the path for the pip command for the gis environment
def get_gis_env_path():
    p = Popen(['conda', 'info', '-e'], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    pth = [s.decode() for s in out.split() if 'envs' in s.decode() and 'gis' in s.decode()]
    if len(pth) > 0:
        return os.path.join(pth[0], exeloc[platform.system()])

# pip installs
url = 'http://internal.usgs.gov/oei/wp-content/itsec/DOIRootCA2.cer'
pips = [get_gis_env_path(), '-m']
pips += ['pip', 'install']
pips += ['https://github.com/aleaf/GIS_utils/archive/master.zip']
pips += ["""--cert={}""".format(os.path.split(url)[-1])] # use the certificate file name from url above

p = Popen(pips, stdout=PIPE, stderr=PIPE)
out, err = p.communicate()
print(out)

# An error will occur if there is no certificate 
# or if the script is run outside of the DOI network
# (in which case the certificate isn't needed)
if len(err) > 0:
    pips.pop(-1)
    p = Popen(pips, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out)
