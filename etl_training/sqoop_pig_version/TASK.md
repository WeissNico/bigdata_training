Implement ETL job, as describe in DWH_Dellstore_Example.docx with the following adaptions:

Use Sqoop to load data from postgres
  - store results as flatfiles

Use pig to transform data to integration
   - store results in ORC tables (HIVE)

Use pig to load data to dwh layer
   - store results in ORC tables (HIVE)
  
Don't historize data, always use TRUNCATE / Insert when loading

---------------------

To setup postgres on the cluster the following commands could be helpful:

kubectl apply -f postgres_dellstore.yml

REM Take public IP from worker
bx cs workers mycluster   

REM take second port of pg-dellstore-db-service
kubectl get services


OK
ID                                                 Public IP         Private IP       Machine Type   State    Status   Zone    Version
kube-mil01-pa0045ac56bb9c4e9ba690ba8d6963673f-w1   159.122.175.139   10.144.181.108   free           normal   Ready    mil01   1.9.7_1510