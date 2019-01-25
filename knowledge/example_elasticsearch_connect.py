""" EXAMPLE-SCRIPT for connecting a production elasticsearch-db. """
import elasticsearch as es
import ssl

ES_HOST = ("a68a95ee-0079-4637-9dab-e8048174f0d1"
           ".659dc287bad647f9b4fe17c4e4c38dcc.databases.appdomain.cloud")
ES_PORT = 31791
ES_AUTH = ("sherlock", "sherlockpw")
CA_FILE = ("C:\\Users\\j.mueller\\.bluemix\\plugins\\cdb\\cdbcerts\\"
           "2e1c46d0-ce0b-11e8-b230-ced9d81cd3f4")

# create an ssl context for the self-signed certificate.
# this only works if the file is directly referenced.
context = ssl.create_default_context(cafile=CA_FILE)

# This is how it works
client = es.Elasticsearch(host=ES_HOST, port=ES_PORT, http_auth=ES_AUTH,
                          use_ssl=True, ssl_context=context)

client.put_script(id="similarity", body={
    "script": {
        "lang": "painless",
        "source": ("doc['fingerprint'].value - params.fingerprint"),
    }
})
