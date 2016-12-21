import os
import glob

use_DOI_cert = False # only set to True if you are on the DOI network

# modify certificate argument if use_DOI_cert
cert_arg = ''
if use_DOI_cert:
	cert_arg = '--cert DOIRootCA2.cer' # or wherever you have it saved

# prepare the pip installs to run in a single command (after activating env)
cmds = ''
for whl in glob.glob('wheels/*.whl'):
	if 'Cartopy' not in whl:
		cmds += 'pip install {} && '.format(whl)
#cmds += 'pip install https://github.com/aleaf/GIS_utils/archive/master.zip &&'
cmds += 'python ..\setup.py install&&'
cmds += 'pip install pyshp {0}&&'
cmds += 'pip install descartes {0} &&'
cmds += 'pip install mplleaflet {0}&&'
cmds += 'pip install rasterstats {0}'

cmds = cmds.format(cert_arg)

cartopy_whl = [w for w in glob.glob('wheels/*.whl') if 'Cartopy' in w]
if len(cartopy_whl) > 0:
	cmds += '&&pip install {}'.format(cartopy_whl[0])

os.system(cmds)
