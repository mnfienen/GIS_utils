# suppress annoying pandas openpyxl warning
from __future__ import print_function

import warnings
warnings.filterwarnings('ignore', category=UserWarning)
import collections
import os
import time
import numpy as np
import fiona
from shapely.geometry import Point, LineString, shape, asLineString, mapping
from shapely import affinity
from shapely.ops import unary_union, transform
from functools import partial
import pyproj
import pandas as pd
import shutil
import GISio

try:
    from rtree import index
except:
    print('Warning: rtree not installed - some functions will not work')


def d8flow(array, force_flow=False, fill_single=False):
    """Quick and dirty calculation of D8 flow direction on a raster,
    similar to FlowDirection tool in ArcGIS.
    Based on code from:
    http://stackoverflow.com/questions/34336303/
    applying-functions-to-multidimensional-numpy-arrays-without-loops

    Parameters
    ----------
    array : 2D numpy array
    force_flow : bool
        Forces outward flow for all cells along the edges of the raster.
        If False, outward flow only occurs if all surrounding values are greater.
        (default False)

    Returns
    -------
    d8array : array of same shape as input, with d8 flow directions.

    Notes
    -----
    Some key differences with ArcGIS algorithm:
    * Flow direction is always assigned using np.argmax() on the negative gradient at each cell.
      For cells with multiple downgradient cells that have the same gradient,
      the receiving cell is the first one returned by argmax().
      In ArcGIS, if the cell is defined as being part of a sink, the directions indicating
      these cells are added together. (For example, equal gradients to directions 1 and 4
      would produce a value of 5). If the cell is not part of a sink, a direction is assigned
      using a lookup table from Greenlee (1987). Soil Water Balance Code treats any non-D8 values
      as closed depressions (no routing assigned). Therefore in closed depressions or flat areas,
      this algorithm will produce different flow directions from ArcGIS in a small number of cells.
    * The ArcGIS algorithm appears to assign flow directions even in flat areas (such as lakes).
      The above algorithm assigns a value of 0 (undefined direction) to all minimum gradients <=0.
    """
    # pad the outside of the array to handle edges
    if not force_flow:
        padded = np.pad(array, ((1, 1), (1, 1)), mode='edge')
    else:
        padded = np.pad(array, ((1, 1), (1, 1)), mode='constant',
                        constant_values=np.min(array) - 100)
    nrow, ncol = padded.shape

    gradient = np.empty((8, nrow - 2, ncol - 2), dtype=np.float)
    code = np.empty(8, dtype=np.int)
    for k in range(8):
        theta = -k * np.pi / 4
        code[k] = 2 ** k
        j, i = np.int(1.5 * np.cos(theta)), -np.int(1.5 * np.sin(theta))
        d = np.linalg.norm([i, j])
        gradient[k] = (padded[1 + i: nrow - 1 + i, 1 + j: ncol - 1 + j] - padded[1: nrow - 1, 1: ncol - 1]) / d
    direction = (-gradient).argmax(axis=0)
    d8 = code.take(direction)
    d8[gradient.min(axis=0) >= 0] = 0  # set cells with inward gradients to 0
    return d8

def shaded_relief(elev, altitude=np.pi/4.,
                  azimuth=np.pi/2.):
    """
    Make a shaded relief version of a numpy array.

    Parameters
    ----------
    dem : 2D numpy array
    altitude : float
        Altitude of sun (in radians)
    azimuth : float
        Direction of sun (in radians)
    """
    x, y = np.gradient(elev)

    slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
    aspect = np.arctan2(-x, y)

    shaded = np.sin(altitude) * np.sin(slope)\
        + np.cos(altitude) * np.cos(slope)\
        * np.cos((azimuth - np.pi/2.) - aspect)
    return shaded

def clip_raster(inraster, features, outraster,
                clip_feature_epsg=None, clip_feature_proj4=None,
                clip_kwargs={},
                **project_kwargs):
    """Clip a raster to feature extent(s).

    Parameters
    ----------
    clip_kwargs: dict
        Keyword arguments to rasterio.mask
    kwargs : key word arguments to project_raster
        These are only used if the clip features are
        in a different coordinate system, in which case
        the raster will be reprojected into that coordinate
        system.
    

    """
    rasterio = import_rasterio()
    from fiona.crs import to_string
    from shapely.geometry import box

    # compare coordinates references for raster and clip feature
    # (if the clip feature is a shapefile path)

    with rasterio.open(inraster) as src:
        raster_crs = to_string(src.crs)
        clip_crs = raster_crs # start with assumption of same coordinates
    if isinstance(features, str):
        with fiona.open(features) as src2:
            clip_crs = to_string(src2.crs)
    elif isinstance(features, list):
        if clip_feature_epsg is not None:
            clip_crs = '+init=epsg:{}'.format(clip_feature_epsg)
        elif clip_feature_proj4 is not None:
            clip_crs = clip_feature_proj4

    # convert the features to geojson
    geoms = _to_geojson(features)
    print('input raster crs:\n{}\n\n'.format(raster_crs),
          'clip feature crs:\n{}\n'.format(clip_crs))
    # if the coordinate systems are not the same
    # reproject the raster first before clipping
    # this could be greatly sped up by first clipping the input raster prior to reprojecting
    if raster_crs != clip_crs:
        tmpraster = 'tmp.tif'
        tmpraster2 = 'tmp2.tif'
        print('Input raster and clip feature(s) are in different coordinate systems.\n'
              'Input raster will be reprojected to the clip feature coordinate system.\n')
        # make prelim clip of raster to speed up reprojection
        xmin, xmax, ymin, ymax = _get_bounds(geoms)
        longest_side = np.max([xmax-xmin, ymax-ymin])
        bounds = box(xmin, ymin, xmax, ymax).buffer(longest_side*0.1)
        bounds = project(bounds, clip_crs, raster_crs)
        _clip_raster(inraster, [bounds], tmpraster, **clip_kwargs)
        project_raster(tmpraster, tmpraster2, clip_crs, **project_kwargs)
        inraster = tmpraster2

    _clip_raster(inraster, geoms, outraster, **clip_kwargs)

    if raster_crs != clip_crs:
        for tmp in [tmpraster, tmpraster2]:
            if os.path.exists(tmp):
                print('removing {}...'.format(tmp))
                os.remove(tmp)
    print('Done.')

def _clip_raster(inraster, features, outraster, **kwargs):

    # convert the features to geojson
    geoms = _to_geojson(features)
    rasterio = import_rasterio()  # check for rasterio
    from rasterio.mask import mask
    with rasterio.open(inraster) as src:
        print('clipping {}...'.format(inraster))

        defaults = {'crop': True,
                    'nodata': src.nodata}
        defaults.update(kwargs)

        out_image, out_transform = mask(src, geoms, **defaults)
        out_meta = src.meta.copy()

        out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})

        with rasterio.open(outraster, "w", **out_meta) as dest:
            dest.write(out_image)
            print('wrote {}'.format(outraster))

def merge_rasters(inrasters, outfile):
    """Merge a collection of rasters together into one raster.

    Parameters
    ----------
    inrasters: list
    outfile: output raster name

    Notes
    -----
    Output raster format is GeoTiff (.tif extension)

    Rasterio uses the affine package to define the raster's
    position in space and handle coordinate transformations, etc.
    Affine 1.2 apparently had an issue where rasters in geographic coordinates
    (lat-lon) would produce an error in the raster.merge.merge method because
    the determinant of the transformation matrix was very small (9e-5 x 9e-5 for a 10m dem).
    This issue appears to have been fixed in affine 2.0 (pip install affine==2.0 should resolve
    the issue).
    """
    rasterio = import_rasterio()
    from rasterio.merge import merge

    srces = []
    print('merging:')

    for file in inrasters:
        srces.append(rasterio.open(file))
        print('\t{}'.format(file))
    out_image, out_trans = merge(srces)

    out_meta = srces[0].meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_trans})
    for src in srces:
        src.close()
    with rasterio.open(outfile, "w", **out_meta) as dest:
        dest.write(out_image)
    print('wrote {}'.format(outfile))

def projectdf(df, projection1, projection2):
    """Reproject a dataframe's geometry column to new coordinate system

    Parameters
    ----------
    df: dataframe
        Contains "geometry" column of shapely geometries

    projection1: string
        Proj4 string specifying source projection
    projection2: string
        Proj4 string specifying destination projection
    """
    projection1 = str(projection1)
    projection2 = str(projection2)


    # define projections
    pr1 = pyproj.Proj(projection1, errcheck=True, preserve_units=True)
    pr2 = pyproj.Proj(projection2, errcheck=True, preserve_units=True)

    # projection function
    # (see http://toblerity.org/shapely/shapely.html#module-shapely.ops)
    project = partial(pyproj.transform, pr1, pr2)

    # do the transformation!
    newgeo = [transform(project, g) for g in df.geometry]

    return newgeo

def project(geom, projection1, projection2):
    """Reproject a shapely geometry object to new coordinate system

    Parameters
    ----------
    geom: shapely geometry object, list of shapely geometry objects, 
          list of (x, y) tuples, or (x, y) tuple.
    projection1: string
        Proj4 string specifying source projection
    projection2: string
        Proj4 string specifying destination projection
    """
    # check for x, y values instead of shapely objects
    if isinstance(geom, tuple):
        return np.squeeze([projectXY(geom[0], geom[1], projection1, projection2)])

    if isinstance(geom, collections.Iterable):
        geom = list(geom) # in case it's a generator
        geom0 = geom[0]
    else:
        geom0 = geom

    if isinstance(geom0, tuple):
        a = np.array(geom)
        x = a[:, 0]
        y = a[:, 1]
        return np.squeeze([projectXY(x, y, projection1, projection2)])

    # transform shapely objects
    # enforce strings
    projection1 = str(projection1)
    projection2 = str(projection2)

    # define projections
    pr1 = pyproj.Proj(projection1, errcheck=True, preserve_units=True)
    pr2 = pyproj.Proj(projection2, errcheck=True, preserve_units=True)

    # projection function
    # (see http://toblerity.org/shapely/shapely.html#module-shapely.ops)
    project = partial(pyproj.transform, pr1, pr2)

    # do the transformation!
    if isinstance(geom, collections.Iterable):
        return [transform(project, g) for g in geom]
    return transform(project, geom)

def projectXY(x, y, projection1, projection2):
    """Project x and y coordinates to different crs
    
    Parameters
    ----------
    x: scalar or 1-D array
    x: scalar or 1-D array
    projection1: string
        Proj4 string specifying source projection
    projection2: string
        Proj4 string specifying destination projection
    """
    projection1 = str(projection1)
    projection2 = str(projection2)

    # define projections
    pr1 = pyproj.Proj(projection1, errcheck=True, preserve_units=True)
    pr2 = pyproj.Proj(projection2, errcheck=True, preserve_units=True)

    return pyproj.transform(pr1, pr2, x, y)


def project_raster(src_raster, dst_raster, dst_crs,
                   resampling=1, resolution=None, num_threads=2,
                   driver='GTiff', extention='tif'):
    """Reproject a raster from one coordinate system to another using Rasterio
    code from: https://github.com/mapbox/rasterio/blob/master/docs/reproject.rst

    Parameters
    ----------
    src_raster : str
        Filename of source raster.
    dst_raster : str
        Filename of reprojected (destination) raster.
    dst_crs : str
        Coordinate system of reprojected raster.
        Examples:
            'EPSG:26715'
    resampling : int (see rasterio source code: https://github.com/mapbox/rasterio/blob/master/rasterio/enums.py)
        nearest = 0
        bilinear = 1
        cubic = 2
        cubic_spline = 3
        lanczos = 4
        average = 5
        mode = 6
        gauss = 7
        max = 8
        min = 9
        med = 10
        q1 = 11
        q3 = 12
    resolution : tuple of floats (len 2)
        cell size of the output raster
        (x resolution, y resolution)
    driver : str
        GDAL driver/format to use for writing dst_raster. Default is GeoTIFF.
    extention : str
        Should go with the driver (default 'tif')
    """
    rasterio = import_rasterio() # check for rasterio
    from rasterio.warp import calculate_default_transform, reproject

    with rasterio.open(src_raster) as src:
        print('reprojecting {}...\nfrom:\n{}, res: {:.2e}, {:.2e}\n'.format(
                src_raster,
                src.crs.to_string(),
                src.res[0], src.res[1],
                dst_crs), end='')
        affine, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=resolution)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': affine,
            'affine': affine,
            'width': width,
            'height': height,
            'driver': driver
        })
        with rasterio.open(dst_raster, 'w', **kwargs) as dst:
            print('to:\n{}, res: {:.2e}, {:.2e}...'.format(dst.crs.to_string(), *dst.res))
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.affine,
                    src_crs=src.crs,
                    dst_transform=affine,
                    dst_crs=dst_crs,
                    resampling=resampling,
                    num_threads=num_threads)
    print('wrote {}.'.format(dst_raster))

def build_rtree_index(geom):
    """Builds an rtree index. Useful for multiple intersections with same index.

    Parameters
    ==========
    geom : list
        list of shapely geometry objects
    Returns
        idx : rtree spatial index object
    """
    from rtree import index

    # build spatial index for items in geom1
    print('\nBuilding spatial index...')
    ta = time.time()
    idx = index.Index()
    for i, g in enumerate(geom):
        idx.insert(i, g.bounds)
    print("finished in {:.2f}s".format(time.time() - ta))
    return idx

def projectdf_XY(df, xcolin, ycolin, xcoltrans, ycoltrans, projection1, projection2):
    """

    :param df: dataframe containing X and Y data to transform. NB - new columns will be written in place!
    :param xcolin: column of df with X coordinate in projection1
    :param ycolin: column of df with Y cordinate in projection1
    :param xcoltrans: column of df THAT WILL BE WRITTEN with X projected to projection2
    :param ycoltrans: column of df THAT WILL BE WRITTEN with Y projected to projection2
    :param projection1: (string) Proj4 string specifying source projection
    :param projection2: (string) Proj4 string specifying destination projection
    """
    projection1 = str(projection1)
    projection2 = str(projection2)

    # define projections
    pr1 = pyproj.Proj(projection1, errcheck=True, preserve_units=True)
    pr2 = pyproj.Proj(projection2, errcheck=True, preserve_units=True)


    df[xcoltrans], df[ycoltrans] = pyproj.transform(pr1, pr2, df[xcolin].tolist(), df[ycolin].tolist())




def intersect_rtree(geom1, geom2):
    """Intersect features in geom1 with those in geom2. For each feature in geom2, return a list of
     the indices of the intersecting features in geom1.

    Parameters:
    ----------
    geom1 : list or rtree spatial index object
        list of shapely geometry objects
    geom2 : list
        list of shapely polygon objects to be intersected with features in geom1
    index :
        use an index that has already been created

    Returns:
    -------
    A list of the same length as geom2; containing for each feature in geom2,
    a list of indicies of intersecting geometries in geom1.
    """
    if isinstance(geom1, list):
        idx = build_rtree_index(geom1)
    else:
        idx = geom1
    isfr = []
    print('\nIntersecting {} features...'.format(len(geom2)))
    ta = time.time()
    for pind, poly in enumerate(geom2):
        print('\r{}'.format(pind + 1), end='')
        # test for intersection with bounding box of each polygon feature in geom2 using spatial index
        inds = [i for i in idx.intersection(poly.bounds)]
        # test each feature inside the bounding box for intersection with the polygon geometry
        inds = [i for i in inds if geom1[i].intersects(poly)]
        isfr.append(inds)
    print("\nfinished in {:.2f}s\n".format(time.time() - ta))
    return isfr

def intersect_brute_force(geom1, geom2):
    """Same as intersect_rtree, except without spatial indexing. Fine for smaller datasets,
    but scales by 10^4 with the side of the problem domain.

    Parameters:
    ----------
    geom1 : list
        list of shapely geometry objects
    geom2 : list
        list of shapely polygon objects to be intersected with features in geom1

    Returns:
    -------
    A list of the same length as geom2; containing for each feature in geom2,
    a list of indicies of intersecting geometries in geom1.
    """

    isfr = []
    ngeom1 = len(geom1)
    print('Intersecting {} features...'.format(len(geom2)))
    for i, g in enumerate(geom2):
        print('\r{}'.format(i+1), end='')
        intersects = np.array([r.intersects(g) for r in geom1])
        inds = list(np.arange(ngeom1)[intersects])
        isfr.append(inds)
    print('')
    return isfr


def dissolve(inshp, outshp, dissolve_attribute=None):
    df = GISio.shp2df(inshp)
    
    df_out = dissolve_df(df, dissolve_attribute)
    
    # write dissolved polygons to new shapefile
    GISio.df2shp(df_out, outshp, prj=inshp[:-4]+'.prj')


def dissolve_df(in_df, dissolve_attribute=None):

    if dissolve_attribute is not None:
        print("dissolving DataFrame on {}".format(dissolve_attribute))
        # unique attributes on which to make the dissolve


        dissolved_items = list(np.unique(in_df[dissolve_attribute]))

        # go through unique attributes, combine the geometries, and populate new DataFrame
        df_out = pd.DataFrame()
        length = len(dissolved_items)
        knt = 0
        for item in dissolved_items:
            df_item = in_df[in_df[dissolve_attribute] == item]
            geometries = list(df_item.geometry)
            dissolved = unary_union(geometries)
            dict = {dissolve_attribute: item, 'geometry': dissolved}
            df_out = df_out.append(dict, ignore_index=True)
            knt +=1
            print('\r{:d}%'.format(100*knt/length))
    else:
        dissolved = unary_union(in_df.geometry.values)
        df_out = pd.DataFrame([{'geometry': dissolved}])
    return df_out

def contour2shp(contours, outshape='contours.shp', 
                add_fields={},
                **kwargs):
    """Convert matplotlib contour plot object to shapefile.

    Parameters
    ----------
    contours : matplotlib.contour.QuadContourSet or list of them
        (object returned by matplotlib.pyplot.contour)
    outshape : str
        path of output shapefile
    add_fields : dict of lists or 1D arrays
        Add fields (keys=fieldnames), with attribute data (values=lists) to shapefile. 
        Attribute data must be of the same length, and in the same order as the
        total number of contour objects x number of levels in each object.
    **kwargs : key-word arguments to GISio.df2shp

    Returns
    -------
    df : dataframe of shapefile contents
    """
    from GISio import df2shp

    if not isinstance(contours, list):
        contours = [contours]

    geoms = []
    level = []
    for ctr in contours:
        levels = ctr.levels
        for i, c in enumerate(ctr.collections):
            paths = c.get_paths()
            geoms += [LineString(p.vertices) for p in paths]
            level += list(np.ones(len(paths)) * levels[i])
    
    d = {'geometry': geoms, 'level': level}
    d.update(add_fields)
    df = pd.DataFrame(d)
    df2shp(df, outshape, **kwargs)
    return df


def join_csv2shp(shapefile, shp_joinfield, csvfile, csv_joinfield, out_shapefile, how='outer'):
    '''
    add attribute information to shapefile from csv file
    shapefile: shapefile to add attributes to
    shp_joinfield: attribute name in shapefile on which to make join
    csvfile: csv file with information to be added to shapefile
    csv_joinfield: column in csv with entries matching those in shp_joinfield
    out_shapefile: output; original shapefile is not modified
    type: pandas join type; see http://pandas.pydata.org/pandas-docs/dev/generated/pandas.DataFrame.join.html
    '''

    shpdf = GISio.shp2df(shapefile, index=shp_joinfield, geometry=True)

    csvdf = pd.read_csv(csvfile, index_col=csv_joinfield)

    print('joining to {}...'.format(csvfile))
    joined = shpdf.join(csvdf, how='inner', lsuffix='L', rsuffix='R')

    # write to shapefile
    GISio.df2shp(joined, out_shapefile, 'geometry', shapefile[:-4]+'.prj')


def rotate_coords(coords, rot, origin):
    """
    Rotates a set of coordinates (wrapper for shapely)
    coords: sequence point tuples (x, y)
    """
    ur = LineString(unrotated)
    r = affinity.rotate(ur, rot, origin=ur[0])

    return list(zip(r.coords.xy[0], r.coords.xy[1]))


def import_rasterio():
    try:
        import rasterio
        from rasterio.warp import calculate_default_transform, reproject
        return rasterio
    except:
        print('This function requires rasterio.')


def _to_geojson(features):
    """convert input features to list of geojson geometries."""

    if isinstance(features, str): # features are in a shapefile
        with fiona.open(features, "r") as shp:
            geoms = [feature["geometry"] for feature in shp]
    elif isinstance(features, list):
        if isinstance(features[0], dict): # features are geo-json
            try:
                shape(features[0])
                geoms = features
            except:
                raise TypeError('Unrecognized feature type')
        else: # features are shapely geometries
            try:
                mapping(features[0])
                geoms = [mapping(f) for f in features]
            except:
                raise TypeError('Unrecognized feature type')
    return geoms

def _get_bounds(geojsoncollection):
    xmin, xmax = 0, 0
    ymin, ymax = 0, 0
    for feature in geojsoncollection:
        for crds in feature['coordinates']:
            a = np.array(crds)
            x, y = a[:, 0], a[:, 1]
            xmin, xmax = np.min(x, xmin), np.max(x, xmax)
            ymin, ymax = np.min(y, ymin), np.max(y, ymax)
    return xmin, xmax, ymin, ymax