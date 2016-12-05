import os
import glob

# prepare the pip installs to run in a single command (after activating env)
cmds = ''
for whl in glob.glob('*.whl'):
	cmds += 'pip install {} && '.format(whl)
cmds += 'pip install https://github.com/aleaf/GIS_utils/archive/master.zip &&'
cmds += 'pip install pyshp &&'
cmds += 'pip install descartes &&'
cmds += 'pip install mplleaflet &&'
cmds += 'pip install rasterstats'

os.system(cmds)


