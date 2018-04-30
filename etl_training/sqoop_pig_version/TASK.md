Implement ETL job, as describe in DWH_Dellstore_Example.docx with the following adaptions:

Use Sqoop to load data from postgres
  - store results as flatfiles

Use pig to transform data to integration
   - store results in ORC tables (HIVE)

Use pig to load data to dwh layer
   - store results in ORC tables (HIVE)
  
Don't historize data, always use TRUNCATE / Insert when loading