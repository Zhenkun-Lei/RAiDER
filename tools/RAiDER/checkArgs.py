#!/usr/bin/env python3
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Author: Jeremy Maurer, Raymond Hogenson & David Bekaert
# Copyright 2019, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged.
#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np
import os
from RAiDER.util import gdal_trans
from RAiDER.llreader import readLL

def modelName2Module(model_name):
    """Turn an arbitrary string into a module name.

    Takes as input a model name, which hopefully looks like ERA-I, and
    converts it to a module name, which will look like erai. I doesn't
    always produce a valid module name, but that's not the goal. The
    goal is just to handle common cases.
    Inputs: 
       model_name  - Name of an allowed weather model (e.g., 'era-5')
    Outputs: 
       module_name - Name of the module 
       wmObject    - callable, weather model object
    """
    import importlib
    module_name = 'RAiDER.models.' + model_name.lower().replace('-', '')
    model_module = importlib.import_module(module_name)
    wmObject = getattr(model_module, model_name.upper().replace('-', ''))
    return module_name,wmObject 


def checkArgs(args, p):
    '''
    Helper fcn for checking argument compatibility and returns the 
    correct variables
    '''
    from datetime import datetime as dt
    import RAiDER.models.allowed as am

    if args.heightlvs is not None and args.outformat != 'hdf5':
       raise ValueError('HDF5 must be used with height levels')
    if args.area is None and args.bounding_box is None and args.wmnetcdf is None and args.station_file is None:
       raise ValueError('You must specify one of the following: \n \
             (1) lat/lon files, (2) bounding box, (3) weather model files, or\n \
             (4) station file containing Lat and Lon columns')
    if args.time is None and args.wmnetcdf is None:
       p.error('You must specify either the weather model file (--wmnetcdf) or time (--time)')
    if args.model not in am.AllowedModels():
       raise NotImplementedError('Model {} is not an implemented model type'.format(args.model))
    if args.model == 'WRF' and args.wrfmodelfiles is None:
       p.error('Argument --wrfmodelfiles required with --model WRF')


    # Line of sight
    if args.lineofsight is not None:
        los = ('los', args.lineofsight)
    elif args.statevectors is not None:
        los = ('sv', args.statevectors)
    else:
        from RAiDER.constants import Zenith
        los = Zenith

    # Area
    if args.area is not None:
        lat, lon = readLL(*args.area)
    elif args.bounding_box is not None:
        lat, lon = readLL(*args.bounding_box)
    elif args.station_file is not None:
        lat, lon = readLL(args.station_file)
    else:
        lat = lon = None

    # write the lats/lons to a local file
    lonFileName = '{}_Lon_{}.dat'.format(args.model.lower().replace('-',''), 
                      dt.strftime(args.time, '%Y_%m_%d_T%H_%M_%S'))
    latFileName = '{}_Lat_{}.dat'.format(args.model.lower().replace('-',''), 
                      dt.strftime(args.time, '%Y_%m_%d_T%H_%M_%S'))

    #TODO
    #gdal_trans(lat, os.path.join(args.out, 'geom', latFileName), 'VRT')
    #gdal_trans(lon, os.path.join(args.out, 'geom', lonFileName), 'VRT')


    # DEM
    if args.dem is not None:
        heights = ('dem', args.dem)
    elif args.heightlvs is not None:
        heights = ('lvs', args.heightlvs)
    else:
        heights = ('download', None)

    # Weather
    model_module_name, model_obj = modelName2Module(args.model)
    if args.model == 'WRF':
       weathers = {'type': 'wrf', 'files': args.wrfmodelfiles,
                   'name': 'wrf'}
    elif args.model=='pickle':
        import pickle
        weathers = {'type':'pickle', 'files': args.pickleFile, 'name': 'pickle'}
    elif args.wmnetcdf is not None:
        weathers = {'type': model_obj(), 'files': args.wmnetcdf,
                    'name': args.model}
    else:
        weathers = {'type': model_obj(), 'files': None,
                    'name': args.model}

    if args.wmLoc is not None:
       wmLoc = args.wmLoc
    else:
       wmLoc = os.path.join(args.out, 'weather_files')

    # zref
    zref = args.zref
    
    # output file format
    if args.outformat is None:
       if args.heightlvs is not None: 
          args.outformat = 'hdf5'
       elif args.station_file is not None: 
          args.outformat = 'netcdf'
       else:
          args.outformat = 'ENVI'
   

    if args.heightlvs is not None: 
       if args.outformat.lower() != 'hdf5':
          print("WARNING: input arguments require HDF5 output file type; changing outformat to HDF5")
       outformat = 'hdf5'
    elif args.station_file is not None:
       if args.outformat.lower() != 'netcdf':
          print("WARNING: input arguments require HDF5 output file type; changing outformat to HDF5")
       outformat = 'netcdf'
    else:
       if args.outformat.lower() == 'hdf5':
          print("WARNING: output require raster output file; changing outformat to ENVI")
          outformat = 'ENVI'
       else:
          outformat = args.outformat.lower()

    # parallelization
    parallel = True if not args.no_parallel else False

    # other
    time = args.time
    out = args.out
    download_only = args.download_only
    verbose = args.verbose

    if args.area is not None:
       flag = 'files'
    elif args.bounding_box is not None:
       flag = 'bounding_box'
    elif args.station_file is not None:
       flag = 'station_file'
    else: 
       flag = None

    return los, lat, lon, heights, flag, weathers, wmLoc, zref, outformat, time, out, download_only, parallel, verbose


def output_format(outformat):
    """
        Reduce the outformat strings users can specifiy to a select consistent set that can be used for filename extensions.
    """
    # convert the outformat to lower letters
    outformat = outformat.lower()

    # capture few specific cases:
    outformat_dict = {}
    outformat_dict['hdf5'] = 'h5'
    outformat_dict['hdf'] = 'h5'
    outformat_dict['h5'] = 'h5'
    outformat_dict['envi'] = 'envi'

    try:
        outformat = outformat_dict[outformat]
    except:
        raise NotImplemented
    return outformat
