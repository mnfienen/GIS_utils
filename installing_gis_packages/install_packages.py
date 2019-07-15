import sys
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

# yml file input argument
try:
    ymlfile = sys.argv[1]
except:
    print('Usage is >python install_packages.py environment.yml')
    quit()

# get the name of the environment from yml file
envname = ymlfile[:-4]
with open(ymlfile) as input:
    for line in input:
        if 'name' in line.lower():
            envname = line.strip().split(':')[-1].strip()
            print('\nCreating environment: {}\n'.format(envname))
            break

cmds = []
# set up conda
cmds.append('conda config --set ssl_verify false')
cmds.append('conda update conda -y')
cmds.append('conda config --set show_channel_urls true')
cmds.append('conda env create -f {}'.format(ymlfile))

for cmd in cmds:
    print(cmd)
    os.system(cmd)


exeloc = {'Windows': 'python',
          'Darwin': os.path.join('bin', 'python')}

# get the path for the python executable for the gis environment
def get_gis_env_path(envname):
    p = Popen(['conda', 'info', '-e'], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    pth = [s for s in out.decode().split() if s.endswith('{}{}'.format(os.path.sep, envname))]
    if len(pth) > 0:
        return os.path.join(pth[0], exeloc[platform.system()])

python_path = get_gis_env_path(envname)
assert python_path is not None, print('Could not find python executable for {} environment'.format(envname))

def run_and_print(cmds):
    print(' '.join(cmds))
    p = Popen(cmds, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    out = out.decode().split(os.linesep)
    err = err.decode().split(os.linesep)
    for line in out:
        print(line)
    if len(err) > 0:
        for line in err:
            print(line)

# install GIS_utils
os.chdir('..')
cmds = [python_path, 'setup.py', 'install']
print('\nexecuting: {}'.format(' '.join(cmds)))
run_and_print(cmds)
os.chdir('installing_gis_packages')

print('\nRunning gis tests...')
cmds = [python_path, '-m', 'nose', '-v', '-w', '..{}tests'.format(os.path.sep)]
run_and_print(cmds)
