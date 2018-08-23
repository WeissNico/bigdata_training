from bs4 import BeautifulSoup
import requests
import time
import logging
import re
from datetime import date, datetime, timedelta
from lxml import html


# setup the logger:
logging.basicConfig(format="[%(asctime)s]%(levelname)s: %(message)s",
                    level=logging.DEBUG)


def _date_from_datetime(date_and_time):
    """Strips the time from a `datetime.datetime`-object.

    Args:
        date_and_time (`datetime.datetime`): the given date and time:

    Returns:
        datetime.date: the contained date.
    """
    return date(date_and_time.year, date_and_time.month, date_and_time.day)


def _retry_connection(url, method, max_retries=10, **kwargs):
    """Repeats the connection with increasing pauses until an answer arrives.

    This should ease out of the 10054 Error, that windows throws.

    Args:
        url (str): the destination url.
        method (str): a valid HTTP verb.
        max_retries (int): the number of maximum retries.
        kwargs (dict): keyword arguments for requests.

    Returns:
        `requests.Response`: the response from the website.
    """
    retry = 0
    response = None

    while response is None and retry < max_retries:
        try:
            with requests.Session() as s:
                logging.info(f"Try to {method} to '{url}'.")
                response = s.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as connErr:
            # sleep increasing (exponential time intervals)
            logging.info("Detected an Error while connecting... "
                         f"retry ({retry})")
            time.sleep(2 ** retry)
    return response


def get_new_documents():
    """Retrieves new documents using the EURLex search.

    Compares the hashes to the older versions in the database and finds the
    point to stop crawling, when a previously seen document is found.

    Returns:
        list: a list of documents (dicts).
    """
    timestamp = int(round(time.time() * 1000))
    exp_date = date.today() - timedelta(days=1)
    url_tmpl = ("https://eur-lex.europa.eu/search.html?lang=de&qid="
                f"{timestamp}&type=quick&scope=EURLEX&sortOneOrder=desc"
                "&sortOne=DD&page={}")
    documents = []

    has_unseen_documents = True
    page = 1
    while has_unseen_documents:
        search_url = url_tmpl.format(page)
        logging.info(f"Crawling page '{search_url}' (page {page})")
        res = _retry_connection(search_url, "get")
        html_string = res.content
        soup = BeautifulSoup(html_string, "lxml")

        celex_nums_unformatted = (soup.find("table",
                                            attrs={"class": "documentTable"})
                                  .findAll("li", attrs={"directTextAccess"}))

        for li in celex_nums_unformatted:
            link = "https://eur-lex.europa.eu"+li.findAll('a')[0]['href'][1:]
            url = ("https://eur-lex.europa.eu/legal-content/DE/ALL/?uri=" +
                   re.search(r"\?uri=([^&]+)&", link)[1])

            date_string = (li.parent.parent.parent
                           .find('td', attrs={'rightMetadata'})
                           .next_element.next_element.next_sibling.text
                           .replace('Date of document: ', ''))
            doc_datetime = datetime.strptime(date_string, "%d/%m/%Y")
            doc_date = _date_from_datetime(doc_datetime)

            # "author": author, "form": form, "celex_number": celex_number
            document = {"url": url, "date": date, "link": link}
            logging.debug(f"Document date: {doc_date}, "
                          f"Expiration date: {exp_date}")
            if doc_date <= exp_date:
                has_unseen_documents = False
                break
            documents.append(document)
        page = page + 1

    logging.info(f"Found {len(documents)} new or potentially modified docs.")

    # extract additional metadata
    for index, document in enumerate(documents):
        logging.info(f"Processing document number {index}...")

        res = _retry_connection(document["url"], "get")

        tree = html.fromstring(res.content)
        document_num = (tree.xpath('//*[@id="content"]/div/div[2]/div[1]/h2')
                        [0].text)
        title = tree.xpath('//*[@id="translatedTitle"]/strong')[0].text

        document['document_number'] = document_num
        document['title'] = title

        if tree.xpath('//*[@id="multilingualPoint"]/div[4]/div[2]/ul/li'):
            for i in range(1, len(tree.xpath('//*[@id="multilingualPoint"]'
                                             '/div[4]/div[2]/ul/li'))+1):
                name, value = (tree.xpath('//*[@id="multilingualPoint"]/div[4]'
                                          f'/div[2]/ul/li[{i}]')[0]
                               .text.split(': '))
                document[name] = value
                # name_date_be_effective, value_date_be_effective =
                # tree.xpath('//*[@id="multilingualPoint"]/div[4]/div[2]/ul'
                #            '/li[2]')[0].text.split(': ')

        if (tree.xpath('//*[@id="multilingualPoint"]/div[5]/div[2]/ul/li')):
            for i in range(1, len(tree.xpath('//*[@id="multilingualPoint"]'
                                             '/div[5]/div[2]/ul/li'))+1):
                name = tree.xpath(('//*[@id="multilingualPoint"]/div[5]/div[2]'
                                   f'/ul/li[{i}]'))[0].text.split(': ')[0]
                value = tree.xpath(('//*[@id="multilingualPoint"]/div[5]'
                                    '/div[2]/ul/li['+str(i)+']'))[0][0].text
                document[name] = value

        if (tree.xpath('//*[@id="documentView"]/div[3]/div[2]/ul/li[4]/a')):
            linked_name = 'linked_source'
            # tree.xpath('//*[@id="documentView"]/div[3]/div[2]/ul/li[4]/a')
            linked_value = tree.xpath('//*[@id="documentView"]/div[3]/div[2]'
                                      '/ul/li[4]/a')[0].attrib['href']
            document[linked_name] = linked_value

    return documents
