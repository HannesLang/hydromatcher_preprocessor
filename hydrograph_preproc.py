import os
import subprocess
from configparser import ConfigParser
from subprocess import CalledProcessError

import pandas as pd
import psycopg2
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
            'Shapefile not found in path {0}'.format(path))


def readfiles():
    """
    Recursively traverses searchpath for files with name==searchfilename.

    The value of the shapefile_tablename is composed as:
    [Name of the floodplain]_[upr|lwr]_Q[Qmax]; Example: 'Lenk_lwr_Q75'

    Name of the floodplain: the path-element before the one containing upr|lwr.
    upr|lwr: value is defined by the one contained in the filepath. It is assumed that only one of them is contained!
    Qmax: the path-element after the one containing upr|lwr

    Interpolation: cubic

    :return:
    dataFrame: DataFrame containing 3 columns 'qvol', 'qmax', 'shapefile_tablename' and the corresponding values for all found files
    """
    params = config(filename='properties.ini', section='properties')
    print('Scanning for SDHs und Shapefiles using params {}'.format(params))

    searchpath = params.get('searchpath')
    searchfilename = params.get('sdhfilename')

    sdh_filenames = [os.path.join(root, name)
                     for root, dirs, files in os.walk(searchpath)
                     for name in files
                     if name == searchfilename]

    dataframe_result = pd.DataFrame(columns=['qvol', 'qmax', 'shapefile_tablename', 'shapefile_path'])

    i = 0  ## counter, needed for the locator to write rows into the dataframe
    for filename in sdh_filenames:
        print('processing file {}'.format(filename))
        dataframe = pd.read_csv(filename, sep='\\t| ', engine='python', usecols=[0, 1], names=['time', 'q'],
                                header=0)
        function_cubic = interp1d(dataframe['time'], dataframe['q'], kind='cubic')
        integral, err = quad(function_cubic, 0, dataframe['time'].max())
        qmax = dataframe['q'].max()
        qvol = int(round(integral))

        filename = replacebackslashes(filename)
        parts = filename.split('/')
        if any('upr' in s for s in parts):
            upperlower = 'upr'
        elif any('lwr' in s for s in parts):
            upperlower = 'lwr'
        else:
            raise Exception(
                'Path {0} does not match the required pattern. One of the substrings \'lwr\' or \'upr\' must be contained in path.'.format(filename))

        for part in parts:
            if upperlower in part:
                qvalue = parts[parts.index(part) + 1]
                floodplain_name = parts[parts.index(part) - 1]

        ## finally look for the shapefile
        shapefile_path = getshapefilepath(filename)

        shapefile_tablename_lowercase = '{floodplain}_{upperlower}_{qvalue}'.format(floodplain=floodplain_name, upperlower=upperlower,
                                                                                    qvalue=qvalue).lower()
        dsh_dictionary = {'qvol': qvol, 'qmax': qmax, 'shapefile_tablename': shapefile_tablename_lowercase,
                          'shapefile_path': shapefile_path}
        dataframe_result.loc[i] = dsh_dictionary
        i += 1

    return dataframe_result


def replacebackslashes(filename):
    return filename.replace('\\', '/')


def config(filename, section):

    parser = ConfigParser()
    parser.read(filename)

    # create a dictionary
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


def insert_sdh_into_db(dataframe):
    """ Connect to the PostgreSQL database server and insert the content of the dataframe """
    try:
        params = config(filename='properties.ini', section='postgresql')

        print('Connecting to the PostgreSQL database with params {}'.format(params))
        engine = create_engine(
            'postgresql://{user}:{password}@{host}:{port}/{database}'.format(user=params.get('user'), password=params.get('password'),
                                                                             host=params.get('host'), port=params.get('port'),
                                                                             database=params.get('database')))

        tablename = params.get('sdh_metadata_tablename')

        if params.get('truncate_sdh_table') == 'True':
            print('Truncate table {} and reset Index ...'.format(tablename))
            engine.connect().execute('TRUNCATE public."{}" RESTART IDENTITY;'.format(tablename))
            print('Table {} truncated'.format(tablename))

        print('Inserting DataFrame into {} ...'.format(tablename))
        ## column shapefile_path must not be inserted here. Therefore make a copy of the dataframe without this col
        sdh_meta_dataframe = dataframe[['qvol', 'qmax', 'shapefile_tablename']].copy()
        sdh_meta_dataframe.to_sql(tablename, engine, if_exists='append', index=False)
        print('DataFrame is inserted into {}.'.format(tablename))

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


def insert_shapefile_into_db(dataframe):
    params = config(filename='properties.ini', section='postgresql')
    for row in dataframe.itertuples():
        print('Inserting Shapefile {file} to Database-Table {table}'.format(file=getattr(row, 'shapefile_path'),
                                                                            table=getattr(row, 'shapefile_tablename')))
        cmd = 'shp2pgsql -s 21781 -d {shapefilename} {tablename} | psql -q -h {host} -d {database} -U {user}'.format(
            shapefilename=getattr(row, 'shapefile_path'), tablename=getattr(row, 'shapefile_tablename'), user=params.get('user'),
            pwd=params.get('password'),
            host=params.get('host'), database=params.get('database'))
        print('Command: {}'.format(cmd))
        try:
            subprocess.check_call(cmd, shell=True)
        except (CalledProcessError) as error:
            print('Command returned with an error and code {}'.format(error.returnCode))
            raise error


if __name__ == '__main__':
    dataframe = readfiles()
    if dataframe.size > 0:
        insert_sdh_into_db(dataframe)
        insert_shapefile_into_db(dataframe)
    else:
        print('No Hydrographs and Shapefiles found. Therefore no processing executed.')
