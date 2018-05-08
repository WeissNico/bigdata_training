PIG SETUP
=========

Implement ETL job, as describe in DWH_Dellstore_Example.docx with the following adaptions:

- Use Sqoop to load data from postgres
- Sqoop store results as flatfiles
- Use pig to transform data to integration
- store transform results in ORC tables (HIVE)
- Use pig to load data to dwh layer
- store dwh data in ORC tables (HIVE)
- Don't historize data, always use TRUNCATE / Insert when loading

Other hints
-----------

To setup postgres on the cluster the following commands could be helpful:

'''
kubectl apply -f postgres_dellstore.yml

REM Take public IP from worker
bx cs workers mycluster

REM take second port of pg-dellstore-db-service
kubectl get services
'''