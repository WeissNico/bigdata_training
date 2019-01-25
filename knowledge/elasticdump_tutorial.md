How-to transfer data between two elasticsearch servers?
=======================================================

Why?
----
Since we changed our elasticsearch database server, the transfer of data became necessary.

What do we need?
----------------
We'll be using [elasticdump](https://github.com/taskrabbit/elasticsearch-dump) so we need the newest [node.js](https://nodejs.org/en/download/)
afterwards we'll install it using npm.
    npm install elasticdump -g

`elasticdump` does not trust self signed certificates therefore the environment variable `NODE_TLS_REJECT_UNAUTHORIZED` must be set to `0`.

The necessary self-signed certificate can be retrieved using the following way:
    ibmcloud cdb deployment-cacert --save doc_store_elastic
The Server-credentials can be obtained in the following way:
    ibmcloud cdb deployment-connections doc_store_elastic -u admin

Which command?
--------------
Since our servers are tiny, we need to limit the items to 10 per batch.
To copy the data from the old db to the new db, the following command becomes necessary.
    elasticdump \
      --input=https://admin:RYZUAYORFMEGJRCT@portal-ssl223-11.bmix-lon-yp-2012af18-4749-4d32-94a6-09573ff5ee35.3259324498.composedb.com:26611 \
      --output=https://admin:RYZUAYORFMEGJRCT@a68a95ee-0079-4637-9dab-e8048174f0d1.659dc287bad647f9b4fe17c4e4c38dcc.databases.appdomain.cloud:31791 \
      --output-cert "C:\Users\j.mueller\.bluemix\plugins\cdb\cdbcerts\2e1c46d0-ce0b-11e8-b230-ced9d81cd3f4" \
      --limit 10 \
      --type=mapping
    elasticdump \
      --input=https://admin:RYZUAYORFMEGJRCT@portal-ssl223-11.bmix-lon-yp-2012af18-4749-4d32-94a6-09573ff5ee35.3259324498.composedb.com:26611 \
      --output=https://admin:RYZUAYORFMEGJRCT@a68a95ee-0079-4637-9dab-e8048174f0d1.659dc287bad647f9b4fe17c4e4c38dcc.databases.appdomain.cloud:31791 \
      --output-cert "C:\Users\j.mueller\.bluemix\plugins\cdb\cdbcerts\2e1c46d0-ce0b-11e8-b230-ced9d81cd3f4" \
      --limit 10 \
      --type=data