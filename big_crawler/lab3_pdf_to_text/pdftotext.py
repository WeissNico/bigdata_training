import os
import io
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage


def convert_pdf_to_txt_1(path):
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages,
                                  password=password,
                                  caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    fp.close()
    device.close()
    retstr.close()
    return text

from pywebhdfs.webhdfs import PyWebHdfsClient
hdfs = PyWebHdfsClient(host='s12m.westeurope.cloudapp.azure.com', port='50070', user_name='data', timeout=10)  # s12m.westeurope.cloudapp.azure.com   hdfs = PyWebHdfsClient(host='', port='50070', user_name='data', timeout=10)  # s12m.westeurope.cloudapp.azure.com

for root, dirs, files in os.walk("./ExxonMobil"):
    for filename in files:
        try:
            txtname = filename.split('.')[0] + '.txt'
            text = convert_pdf_to_txt_1("ExxonMobil/"+filename)
            text_file = open("text/" + txtname, 'w', encoding="utf-8")
            text_file.write(text)
            text_file.close()
            print(filename)
            
            try:
                with open('text/' + txtname, "rb") as file_data:  # UTF-8 Latin-1
                    hdfs.create_file("/user/data/txt_file/" + txtname, file_data)
                print("Upload to HDFS " + filename)
            except:
                print("Upload to HDFS Failed")

        except:
            continue
        

'''
filename = "BASF_Creating-Chemistry_07.pdf"
text = convert_pdf_to_txt_1("files/"+filename)
print(text)
text_file = open("text/" + filename.split('.')[0] + '.txt', 'w', encoding="utf-8")
text_file.write(text)
text_file.close()
print(filename)



'''
