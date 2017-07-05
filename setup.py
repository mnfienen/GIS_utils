from setuptools import setup


def run():
    setup(name="GIS_utils",
          version="0.1",
          description="Convenience functions for working with common GIS formats",
          author="Andy Leaf",
          author_email='jlawhead@geospatialpython.com',
          url='https://github.com/GeospatialPython/pyshp',
          download_url='https://github.com/GeospatialPython/pyshp/archive/1.2.10.tar.gz',
          py_modules=['GISio', 'GISops'],
          zip_safe=False
          )
          
if __name__ == "__main__":
    run()