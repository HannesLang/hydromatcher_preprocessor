## hydromatcher_preprocessor

#### Runtime Requirements
- Python Version: 3.7

This script needs the following python libs, which are usually not contained in a standard python runtime. These must therefore be installed in the python runtime using `pip install ...`
- pandas
- sqlalchemy
- psycopg2
- scipy
- configparser

###### Further requirements
- Provide a passwordfile for postgresql in c:\Users\username\AppData\Roaming\postgresql\pgpass.conf (is needed by psql!).
    - This file must contain one line for each db that is used by psql. The format is: <host:port:db:user:password>. For example: `mobidb.giub.unibe.ch:5432:entwicklung:jlang:PASSWORD`
- shp2pgsql and psql must be in the path (both are installed as a part of postgresql and postgis)
- the db-script in subfolder sql must be executed in the postgresql-database used for the hydrograph matching. For this to work a db user with the grants to create tables and sequences is needed.

#### Naming Conventions
- Each floodplain has a unique name
- The directory structure has to be as follows: `.../<floodplain>/out<_lwr/_upr>/<Qmax>/`. This folder must contain the SDH-hydrograph named 'hydrograph.txt' as well as the corresponding shapefile.
There can only be one shapefile. Otherwise an exception is raised. The path-element before the out-element must correspond exactly to the name of the floodplain, the element after the out-element says if it is a lake or a river.
- SDH: 'hydrograph.txt'
- Shapefile: '*.shp'
- example: .../Luetschine/verlue/out_lwr/Q150/; here the floodplain is called 'verlue', the hydrograph is processed as a river, and the resulting shapefile-tablename will be 'geo_verlue_lwr_q150'
- example: .../thun/out/H55671/: in this case the floodplain is `thun`, it is processed as lake, and the shapefile-name will be `geo_thun_h55671`.
- Lakes: The directory containing the sdh and shape is named with a leading 'H' instead of 'Q'. followed by the lake level in centimeters. For example 'H56213', where 56213 stands for max lake level 562,13 meters.
    - There is no need to calculate the volume. And the max level can be taken from the directory name. Therefore it is not necessary to read the sdh file.
    - Lakes and some rivers have no upr or lwr. The corresponding directory is named 'out'.
    - We use the same t_sdh_metadata table as with rivers and just leave the qvol column empty (null).

#### What this preprocessor does
- It loads the results of the simulations into the database to provide the basis for the prediction of floods in case of precipitation events.
- The SDHs are parsed, then qmax and qvol is calculated/determined and, together with the shapefilename, written to table t_sdh_metadata.
- The shapefilename is the foreignKey to the matching shapefile-Table
- The shapefiles are persisted using shp2pgsql and psql into tables named geo_<shapefiletablename>.
- All tables are dropped before creation if they already exist (`create or replace ...`). The execution of this script is therefore idempotent.
