import os
import subprocess
from configparser import ConfigParser
from subprocess import CalledProcessError

import pandas as pd
import getpass
from scipy.integrate import quad
from scipy.interpolate import interp1d
from sqlalchemy import create_engine


def getshapefilepath(filename):
    """
    Look for a shapefile in the directory of filename and return its complete path and name.
    It is assumed that there can only be one shapefile per sdh file. Otherwise an exception is raised
    """
    path = os.path.dirname(filename)
    shapefiles = [f for f in os.listdir(path) if f.endswith('.shp')]
    if shapefiles and len(shapefiles) == 1:
        return replacebackslashes(os.path.join(path, shapefiles[0]))
    else:
        raise Exception(
            'No or more than one Shapefile found in path {0}'.format(path))


def readfiles(params):
    """
    Recursively traverses searchpath for files with name==searchfilename.

    The value of the shapefile_tablename is composed as:
    geo_[Name of the floodplain]_[upr|lwr]_Q[Qmax]; Example: 'geo_lenk_lwr_q75'

    Name of the floodplain: the path-element before the one containing upr|lwr.
    upr|lwr: value is defined by the one contained in the filepath. It is assumed that only one of them is contained!
    Qmax: the path-element after the one containing upr|lwr

    Interpolation: cubic

    :return: dataframe: containing 3 columns 'qvol', 'qmax', 'shapefile_tablename' and the corresponding values for all found files
    """
    print('Scanning for SDHs und Shapefiles using params {}'.format(params))

    searchpath = params.get('searchpath')
    searchfilename = params.get('sdhfilename')

    sdh_filenames = [os.path.join(root, name)
                     for root, dirs, files in os.walk(searchpath)
                     for name in files
                     if name == searchfilename]

    dataframe_result = pd.DataFrame(columns=['qvol', 'qmax', 'shapefile_tablename', 'shapefile_path', 'floodplain_name', 'floodplain_type'])

    i = 0  # counter, needed for the locator to write rows into the dataframe
    for filename in sdh_filenames:
        print('processing file {}'.format(filename))

        filename = replacebackslashes(filename)
        parts = filename.split('/')

        if any('out' in s for s in parts):
            if any('out_upr' in s for s in parts):
                out_upr_lwr = '_upr'
            elif any('out_lwr' in s for s in parts):
                out_upr_lwr = '_lwr'
            else:
                out_upr_lwr = ''
        else:
            raise Exception(
                'The path {0} does not match the required pattern. The substring \'out\' and optionally \'lwr\' or \'upr\' must be contained in the path.'.format(filename))

        # locate the 'out...' part to set the floodplain name and the qvalue. Floodplain is the part before the out part. qvalue is the part after.
        for part in parts:
            if 'out{}'.format(out_upr_lwr) == part:
                qvalue = parts[parts.index(part) + 1]
                floodplain_name = parts[parts.index(part) - 1].lower()

        # finally look for the shapefile
        shapefile_path = getshapefilepath(filename)

        shapefile_tablename_lowercase = 'geo_{floodplain}{out_upr_lwr}_{qvalue}'.format(floodplain=floodplain_name, out_upr_lwr=out_upr_lwr,
                                                                                        qvalue=qvalue).lower()

        # Assume that there is no header, except of #-commented lines. The first col is time, the second col is q or sealevel
        if qvalue.startswith('Q'):
            dataframe = pd.read_csv(filename, sep='\\t| ', engine='python', usecols=[0, 1], names=['time', 'q'], header=None, comment='#')
            qmax, qvol = calculatePeakAndVol(dataframe)
            floodplain_type = 'river'
        elif qvalue.startswith('H'):
            qmax = qvalue[1:]  # exclude the leading H. Examople: 'H12345' means lake level 123,45 meters. The result is '12345'
            qvol = None
            floodplain_type = 'lake'
        else:
            raise Exception('The name of directories containing hydrographs have to start with either Q (for river discharge) or H (for lake level). Current directory: {0}'.format(qvalue))

        dsh_dictionary = {'qvol': qvol, 'qmax': qmax, 'shapefile_tablename': shapefile_tablename_lowercase,
                          'shapefile_path': shapefile_path, 'floodplain_name': floodplain_name, 'floodplain_type': floodplain_type}
        dataframe_result.loc[i] = dsh_dictionary
        i += 1

    return dataframe_result


def calculatePeakAndVol(dataframe):
    """
    creates a cubic interpolation function for the values provided, calculates the integral value and determines the max value.
    :param dataframe: the values to be used
    :return: maxvalue and volume
    """
    qmax = dataframe['q'].max()

    function_cubic = interp1d(dataframe['time'], dataframe['q'], kind='cubic')
    integral, err = quad(function_cubic, 0, dataframe['time'].max())
    qvol = int(round(integral))

    return qmax, qvol


def replacebackslashes(filename):
    return filename.replace('\\', '/')


def config(filename='properties.ini', section='general'):
    properties = ConfigParser()
    properties.read(filename)

    if properties.has_section(section):
        return properties[section]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))


def insert_floodplains_into_db(dataframe, dbproperties):
    """ Connect to the PostgreSQL database server and insert the floodplains """
    try:
        print('Connecting to the PostgreSQL database with params from {}'.format(dbproperties))
        engine = create_engine(
            'postgresql://{user}:{password}@{host}:{port}/{database}'.format(user=dbproperties.get('user'), password=dbproperties.get('password'),
                                                                             host=dbproperties.get('host'), port=dbproperties.get('port'),
                                                                             database=dbproperties.get('database')))

        tablename = dbproperties.get('floodplain_tablename')

        print('Inserting DataFrame into {} ...'.format(tablename))
        # only columns floodplain_name and floodplain_type must be inserted here. Therefore make a copy of the dataframe without all other cols
        floodplains_dataframe = dataframe[['floodplain_name', 'floodplain_type']].copy()
        floodplains_dataframe.drop_duplicates(inplace=True)
        floodplains_dataframe.to_sql(tablename, engine, if_exists='append', index=False)
        print('DataFrame is inserted into {}.'.format(tablename))

    except (Exception) as error:
        print(error)


def getFloodplainsFromDB(dbproperties):
    """ Read the floodplains from DB """
    try:
        print('Connecting to the PostgreSQL database with params from {}'.format(dbproperties))
        engine = create_engine(
            'postgresql://{user}:{password}@{host}:{port}/{database}'.format(user=dbproperties.get('user'), password=dbproperties.get('password'),
                                                                             host=dbproperties.get('host'), port=dbproperties.get('port'),
                                                                             database=dbproperties.get('database')))

        tablename = dbproperties.get('floodplain_tablename')

        print('Reading floodplains from {} ...'.format(tablename))
        floodplains_dataframe = pd.read_sql_table(tablename, engine)
        return floodplains_dataframe

    except (Exception) as error:
        print(error)


def insert_sdh_into_db(dataframe, dbproperties, floodplains):
    """ Connect to the PostgreSQL database server and insert the content of the dataframe using sqlalchemy """
    try:
        print('Connecting to the PostgreSQL database with params from {}'.format(dbproperties))
        engine = create_engine(
            'postgresql://{user}:{password}@{host}:{port}/{database}'.format(user=dbproperties.get('user'), password=dbproperties.get('password'),
                                                                             host=dbproperties.get('host'), port=dbproperties.get('port'),
                                                                             database=dbproperties.get('database')))

        tablename = dbproperties.get('sdh_metadata_tablename')

        if dbproperties.getboolean('truncate_sdh_table'):
            print('Truncate table {} and reset Index ...'.format(tablename))
            engine.connect().execute('TRUNCATE {tablename} RESTART IDENTITY;'.format(tablename=tablename))
            print('Table {} truncated'.format(tablename))

        # get the floodplain_id and write it to the dataframe
        dataframe['floodplain_id'] = 0
        for index, row in floodplains.iterrows():
            dataframe.loc[dataframe.floodplain_name == row['floodplain_name'], 'floodplain_id'] = int(row['id'])

        print('Inserting DataFrame into {} ...'.format(tablename))
        # column shapefile_path must not be inserted here. Therefore make a copy of the dataframe without this col
        sdh_meta_dataframe = dataframe[['qvol', 'qmax', 'shapefile_tablename', 'floodplain_id']].copy()
        sdh_meta_dataframe.to_sql(tablename, engine, if_exists='append', index=False)
        print('DataFrame is inserted into {}.'.format(tablename))

    except (Exception) as error:
        print(error)


def insert_shapefile_into_db(dataframe, dbproperties):
    for row in dataframe.itertuples():
        print('Inserting Shapefile {file} to Database-Table {table}'.format(file=getattr(row, 'shapefile_path'),
                                                                            table=getattr(row, 'shapefile_tablename')))
        cmd = 'shp2pgsql -s 21781 -d {shapefilename} {tablename} | psql -q -h {host} -d {database} -U {user}'.format(
            shapefilename=getattr(row, 'shapefile_path'), tablename=getattr(row, 'shapefile_tablename'), user=dbproperties.get('user'),
            pwd=dbproperties.get('password'),
            host=dbproperties.get('host'), database=dbproperties.get('database'))
        print('Command: {}'.format(cmd))
        try:
            subprocess.check_call(cmd, shell=True)
        except (CalledProcessError) as error:
            print('Command returned with an error and code {}'.format(error.returnCode))
            raise error


def main():
    # get properties
    generalproperties = config(section='general')
    dbproperties = config(section=generalproperties.get('db'))

    if not dbproperties.get('user'):
        dbusername = input("Enter database-username: ")
        dbproperties['user'] = str(dbusername)

    # if password is not provided in property file, then get it from the commandline via user input
    if not dbproperties.get('password'):
        password = getpass.getpass()
        dbproperties['password'] = password

    dataframe = readfiles(generalproperties)
    if dataframe.size > 0:
        insert_floodplains_into_db(dataframe, dbproperties)
        # Read the inserted floodplains from db because we need the sequence-ids, that are generated while inserting the rows.
        # They are needed as foreign keys for the metadata table
        floodplains = getFloodplainsFromDB(dbproperties)
        insert_sdh_into_db(dataframe, dbproperties, floodplains)
        insert_shapefile_into_db(dataframe, dbproperties)
    else:
        print('No Hydrographs and Shapefiles found. Therefore no processing executed.')


main()
