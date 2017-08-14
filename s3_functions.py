from io import StringIO
import pandas as pd
import numpy as np
import utm
import re
import shapefile
from shp_functions import create_polygon
import json

def read_outflw1(year, month, s3, bucket):
    #create the key
    outflw1_key = 'data/{}/{}/outflw1'.format(year, month)
    #open the file as binary
    outflw1_file = s3.open('{}/{}'.format(bucket, outflw1_key), mode='rb')
    #skip the first 5 lines
    for i in range(5):
        next(outflw1_file)

    #create a blank dictionary for StringIO
    sio = {}
    init = 0

    #go through every line in the file
    for ln in outflw1_file:
        #skip blank lines
        if not ln.strip():
            init = 1
            continue
        else:
            #need to decode the binary for StringIO to work
            s = ln.decode('utf-8').split()
            #first time through need to initialize StringIO objects
            #this block just writes the date in the correct format
            if init == 0:
                sio[s[3]] = StringIO()
                sio[s[3]].write('{}-{}-{} {}:00:00,'.format(year, s[0], s[1], s[2].split('.')[0]))
            else:
                sio[s[3]].write('{}-{}-{} {}:00:00,'.format(year, s[0], s[1], s[2].split('.')[0]))
            #this line writes the tide, elev, depth, and velocity
            sio[s[3]].write(','.join(s[4:8]) + ',')
            #when direction degress goes over 100 it merges with the direction string, need special case to parse
            if len(s) == 11:
                sio[s[3]].write(','.join(s[9:]) + '\n')
            else:
                sio[s[3]].write(','.join([s[8][2:],s[9]]) + '\n')
            continue
    #close the outflw1 object
    outflw1_file.close()

    #create a blank dictionary for outflw1
    outflw1 = {}
    #loop through the keys in sio
    for k in list(sio.keys()):
        #go back to the beginning (currently at the end)
        sio[k].seek(0)
        #read sio as a csv (I LOVE PYTHON!!!!)
        outflw1[k] = pd.read_csv(sio[k], parse_dates=True, index_col=0,
                                names=['tide', 'elevation', 'depth', 'velocity', 'direction', 'salinity'])
        outflw1[k].index.name = 'Date'

    #decompose the velocity and direction into u and v components
    for k in outflw1:
        outflw1[k]['u'] = -1 * outflw1[k]['velocity'] * np.sin(np.deg2rad(outflw1[k]['direction']))
        outflw1[k]['v'] = -1 * outflw1[k]['velocity'] * np.cos(np.deg2rad(outflw1[k]['direction']))

    return outflw1

def read_coords(zone_number, zone_letter, extent, s3, bucket):
    #only needed to call this once so harcoding year and month
    year = '1993'
    month = '0401'
    #create the key and open the file
    input_key = 'data/{}/{}/input'.format(year, month)
    input_file = s3.open('{}/{}'.format(bucket, input_key), mode='rb')

    #first find how many nodes in the model (NN)
    s = input_file.readline()
    while s.split()[0] != b'NN':
        s = input_file.readline()
    s = input_file.readline()
    nn = int(s[:5])

    #next read the utm coords (easting and northing) from the input file
    while s.split()[0] != b'NODAL':
        s = input_file.readline()
    easting = np.zeros(nn)
    northing = np.zeros(nn)
    for i in range(nn):
        s = input_file.readline().split()
        easting[i] = float(s[1])
        northing[i] = float(s[2])

    #convert easting and northing to lat and lon in decimal degrees
    lat_deg, lon_deg = utm.to_latlon(easting, northing, zone_number, zone_letter)
    #create a blank dataframe for coords then put in the lat/lon
    coords = pd.DataFrame(np.nan, index=range(1, nn+1, 1), columns=['lat', 'lon'])
    coords['lat'] = lat_deg
    coords['lon'] = lon_deg

    #clip the coords to within the extent
    coords_clipped_nodes = coords[
        (coords['lon'] > extent[0]) &
        (coords['lon'] < extent[1]) &
        (coords['lat'] > extent[2]) &
        (coords['lat'] < extent[3])
    ].index.tolist()
    coords_clipped = coords.iloc[coords_clipped_nodes]

    #return coords, coords_clipped
    return coords_clipped

def read_avesalD(year, month, s3, bucket):
    #create the key and open the file
    avesalD_key = 'data/{}/{}/avesalD.w'.format(year, month)
    avesalD_file = s3.open('{}/{}'.format(bucket, avesalD_key), mode='rb')

    #start a StringIO instance to read the data
    s = StringIO()
    #mergedLine will be the average salinity for a single day for all nodes
    mergedLine = None
    init = 0

    #loop through all lines in file
    for ln in avesalD_file:
        #decode the binary line
        ln = ln.decode('utf-8')
        #skip blank lines
        if not ln.strip():
            continue

        #lines that start with Average contain the date but no data
        if ln.split()[0] == 'Average':
            if init != 0:
                mergedLine = mergedLine[:-1]
                mergedLine += '\n'
                s.write(mergedLine)
            date = str(pd.datetime(int(ln.split()[4]), int(ln.split()[6]), int(ln.split()[8])))
            mergedLine = date + ','
            init = 1
            continue

        #skip unneccesary header lines
        elif re.search('[a-zA-Z]', ln):
            continue

        #this handles the data lines
        else:
            mergedLine += ','.join(ln.split()).replace('\n', '', 1)
            mergedLine += ','
            continue

    #make sure there's a line break at the end of each line for pandas to read it
    mergedLine = mergedLine[:-1]
    mergedLine += '\n'
    s.write(mergedLine)
    #go back to the beginning
    s.seek(0)
    #read the data in the StringIO object
    avesalD = pd.read_csv(s, parse_dates=True, index_col=0, header=None)
    avesalD.index.name = 'Date'

    # avesalD_nodes = coords[
    #     (coords['lon'] > extent[0]) &
    #     (coords['lon'] < extent[1]) &
    #     (coords['lat'] > extent[2]) &
    #     (coords['lat'] < extent[3])
    # ].index.tolist()
    #
    # avesalD = avesalD[avesalD_nodes]
    # avesalD_coords = coords.iloc[avesalD_nodes]

    return avesalD#, avesalD_coords


def read_shapefile(s3, bucket):
    shp_key = 'data/shapefile/CBclosed.shp'
    dbf_key = 'data/shapefile/CBclosed.dbf'
    shx_key = 'data/shapefile/CBclosed.shx'
    shp_file = s3.open('{}/{}'.format(bucket, shp_key), mode='rb')
    dbf_file = s3.open('{}/{}'.format(bucket, dbf_key), mode='rb')
    shx_file = s3.open('{}/{}'.format(bucket, shx_key), mode='rb')
    r = shapefile.Reader(shp=shp_file, dbf=dbf_file, shx=shx_file)

    geoms = []
    for i in range(r.numRecords):
        geoms.append(create_polygon(r.shape(i)))

    max_area = 0
    max_area_id = 0
    for i in range(len(geoms)):
        if geoms[i].area > max_area:
            max_area = geoms[i].area
            max_area_id = i
            polygon = geoms[i]
    return r, polygon, geoms


def read_mask(s3, bucket):
    '''
    this comment for reading
    mask_list = mask.tolist()

    json.dump(
        mask_list,
        codecs.open(file_path, 'w', encoding='utf-8'),
        separators=(',', ':'),
        sort_keys=True, indent=4,
    )
    '''
    mask_file = s3.open('{}/data/shapefile/mask.json'.format(bucket), mode='rb').read().decode('utf-8')
    return np.array(json.loads(mask_file))
