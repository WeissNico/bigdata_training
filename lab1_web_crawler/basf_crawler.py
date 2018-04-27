from bs4 import BeautifulSoup
import requests
import urllib.request as urllib
import os.path
import io
from pywebhdfs.webhdfs import PyWebHdfsClient
from pprint import pprint

# port 8020, 50070, 50075

#urllist = ['https://www.basf.com/de/company/investor-relations/calendar-and-publications/publication-finder.html']
urllist = ['https://www.basf.com/de/company/investor-relations/calendar-and-publications/publication-finder/_jcr_content/par/overviewcontainer_32/publicationoverview_.0.10......html']  #first number counter, index -> 20.10 -> ab stelle 20 die nächsten 10
url = "https://www.basf.com"


hdfs = PyWebHdfsClient(host='s12m.westeurope.cloudapp.azure.com', port='50070', user_name='data', timeout=10)  # s12m.westeurope.cloudapp.azure.com   hdfs = PyWebHdfsClient(host='', port='50070', user_name='data', timeout=10)  # s12m.westeurope.cloudapp.azure.com


res = requests.get(urllist[0])
html_string = res.content
soup = BeautifulSoup(html_string, 'lxml')

urls = []
names = []


data = soup.findAll('div',attrs={'class':'resultbucket'})
for div in data:
    links = div.findAll('a')
    for i, link in enumerate(links):
        _FULLURL = url + link.get('href')
        if _FULLURL.endswith('.pdf') and _FULLURL.startswith("https://www.basf.com/documents/"):
            urls.append(_FULLURL)
            names.append(link.get('href').rsplit('/', 1)[-1])

names_urls = zip(names, urls)


for name, url in names_urls:
    if not os.path.isfile("files/" + name):
        rq = urllib.Request(url)
        try:
            res = urllib.urlopen(rq)
            pdf = open("files/" + name, 'wb')
            pdf.write(res.read())
            pdf.close()
            print("Download: "+url)


        except:
            continue



    else:
        print(url)

    try:
        with open('files/'+name, "rb") as file_data:  # UTF-8 Latin-1
            hdfs.create_file("/user/data/"+name, file_data)
        print("Upload to HDFS "+ name)
    except:
        print("Upload to HDFS Failed")


