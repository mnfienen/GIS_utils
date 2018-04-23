## To install the python GIS tool chain

1) install the [Anaconda Python Distribution](https://www.anaconda.com/download/)   

* when prompted, **select "Add Anaconda to my PATH environment variable"**. It will say this isn't recommended, but if you don't do it, you won't be able to use Anaconda (or any of the gis packages) by calling `python` from a regular command window.
* **select "Register Anaconda as my default Python 3.6"**.

2) open a command window and type:

```
$ python install_packages.py gis.yml
```
Note that when python is called at the command line, the Anaconda version should come up (indicated by the text above the `>>>` after running `$ python `).

The `install_packages.py` script creates a separate [conda environment](https://conda.io/docs/user-guide/tasks/manage-environments.html) called `gis`, and installs the packages listed in `gis.yml` to that environment.

3) Each time you want to use the installed packages (on Windows):  

```
> activate gis
```  
or ` $ source activate gis` on OSX.

This modifies the system path for the current session, so that if `python` is called, the version associated with the `gis` environment is used.