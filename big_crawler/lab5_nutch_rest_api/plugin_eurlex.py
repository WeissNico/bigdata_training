from bs4 import BeautifulSoup
import requests
import time
from datetime import datetime, timedelta
from lxml import html


def get_new_documents():
    timestamp = millis = int(round(time.time() * 1000))
    documents = []

    condition = True
    page = 1
    while condition:
        print('page: '+str(page))
        url = "https://eur-lex.europa.eu/search.html?lang=de&qid=" + str(
            timestamp) + "&type=quick&scope=EURLEX&sortOneOrder=desc&sortOne=DD&page=" + str(page)
        res = requests.get(url)
        html_string = res.content
        soup = BeautifulSoup(html_string, 'lxml')

        celex_numbers_unformatted = soup.find('table', attrs={'class': 'documentTable'}).findAll("li",
                                                                                          attrs={"directTextAccess"})

        for li in celex_numbers_unformatted:
            url = "https://eur-lex.europa.eu/legal-content/DE/ALL/?uri="+("https://eur-lex.europa.eu"+li.findAll('a')[0]['href'][1:]).split('?uri=')[1].split('&')[0] #
            link =  "https://eur-lex.europa.eu"+li.findAll('a')[0]['href'][1:]

            date_string = li.parent.parent.parent.find('td', attrs={'rightMetadata'}).next_element.next_element.next_sibling.text.replace('Date of document: ','')
            date = datetime.strptime(date_string, "%d/%m/%Y")

            document = {"url": url,  "date": date, "link":link} #"author": author, "form": form, "celex_number": celex_number
            if date <= datetime.strptime((datetime.today()- timedelta(days=1)).strftime('%Y-%m-%d'), '%Y-%m-%d'):
                condition = False
                break
            documents.append(document)

        print('new or modifyed documents:'+str(len(documents)))
        for document in documents:
            res = requests.get(document['url'])

            tree = html.fromstring(res.content)
            document_number = tree.xpath('//*[@id="content"]/div/div[2]/div[1]/h2')[0].text
            title = tree.xpath('//*[@id="translatedTitle"]/strong')[0].text

            document['document_number'] = document_number
            document['title'] = title


            if (tree.xpath('//*[@id="multilingualPoint"]/div[4]/div[2]/ul/li')):
                for i in range(1, len(tree.xpath('//*[@id="multilingualPoint"]/div[4]/div[2]/ul/li'))+1):
                    name, value = tree.xpath('//*[@id="multilingualPoint"]/div[4]/div[2]/ul/li['+str(i)+']')[0].text.split(': ')
                    document[name] = value
                    #name_date_be_effective, value_date_be_effective = tree.xpath('//*[@id="multilingualPoint"]/div[4]/div[2]/ul/li[2]')[0].text.split(': ')

            if (tree.xpath('//*[@id="multilingualPoint"]/div[5]/div[2]/ul/li')):
                for i in range(1, len(tree.xpath('//*[@id="multilingualPoint"]/div[5]/div[2]/ul/li'))+1):
                    name = tree.xpath(('//*[@id="multilingualPoint"]/div[5]/div[2]/ul/li['+str(i)+']'))[0].text.split(': ')[0]
                    value = tree.xpath(('//*[@id="multilingualPoint"]/div[5]/div[2]/ul/li['+str(i)+']'))[0][0].text
                    document[name] = value

            if (tree.xpath('//*[@id="documentView"]/div[3]/div[2]/ul/li[4]/a')):
                linked_name = 'linked_source'#tree.xpath('//*[@id="documentView"]/div[3]/div[2]/ul/li[4]/a')[0].text
                linked_value = tree.xpath('//*[@id="documentView"]/div[3]/div[2]/ul/li[4]/a')[0].attrib['href']
                document[linked_name] = linked_value
        page = page + 1

    return documents