DROP TABLE  IF EXISTS ogna_condition CASCADE;
DROP TABLE  IF EXISTS ogna_connection CASCADE;
DROP TABLE  IF EXISTS ogna_connection_conds CASCADE;
DROP TABLE  IF EXISTS ogna_connection_points CASCADE;
DROP TABLE  IF EXISTS ogna_device CASCADE;
DROP TABLE  IF EXISTS ogna_devicesensor CASCADE;
DROP TABLE  IF EXISTS ogna_devicevendor CASCADE;
DROP TABLE  IF EXISTS ogna_observation CASCADE;
DROP TABLE  IF EXISTS ogna_observationclass CASCADE;
DROP TABLE  IF EXISTS ogna_order CASCADE;
DROP TABLE  IF EXISTS ogna_pointclass CASCADE;
DROP TABLE  IF EXISTS ogna_project CASCADE;
DROP TABLE  IF EXISTS ogna_rasterdata CASCADE;
DROP TABLE  IF EXISTS ogna_singlepoint CASCADE;
DROP TABLE  IF EXISTS ogna_vectordata CASCADE;

SELECT postgis_lib_version();