# -*- coding: utf-8 -*-
"""
Created on Fri May 25 19:28:37 2018

@author: j.ischebeck
"""

#%%
import os
os.chdir('C:\\Users\\f.hiekel\\BlueReply\\ambari\\bigdata_training\\big_crawler\\lab7_data_transform_and_load')
#%%
import PyPDF2 

def get_text_from_pdf(filename):
    pdfReader = PyPDF2.PdfFileReader(filename)
    num_pages = pdfReader.numPages
    count = 0
    text = ""
    while count < num_pages:
        pageObj = pdfReader.getPage(count)
        count +=1
        text += pageObj.extractText()
    return text
   
# %%
  
import pdfminer.high_level
import io

def get_text_from_pdf_2(filename):
    outp = io.StringIO()
    with open(filename, "rb") as fp:
        pdfminer.high_level.extract_text_to_fp(fp,outp, output_type='text')
    text = outp.getvalue()
    outp.close()
    return text
# %%

# prepare PDF to text conversion
import os

training_data = []
training_categories = []

path= os.path.join(os.getcwd(),'training_data')
for dirname in os.listdir(path):
    subdir = os.path.join(path,dirname)
    print("scanning files in %s" % dirname)
    for fname in os.listdir(subdir):      
        #print("convert file %s"% fname)
        text = get_text_from_pdf_2(os.path.join(subdir,fname))
        training_categories.append(dirname)
        training_data.append (text)
#%%
print("\n".join(training_data[1].split("\x0c")[:2]))
#%%
print("\n".join(training_data[21].split("\x0c")[:5]))
#%%        

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
# build pipeline - counting
classify = Pipeline([('vect', CountVectorizer(stop_words='english')), 
                     ('tfidf', TfidfTransformer()), 
                     ('clf', MultinomialNB())])

classify = classify.fit(training_data, training_categories)
#%%
z = classify.predict(['''eiterte Fassung) vor. Diese Online-Fassung enthält  neben dem Anhang als Teil 
                des  Bayer-Konzernabschlusses  weiterführende Informatio-nen  zum Lagebericht.
                Den „Geschäftsbericht 2017 – Erweiterte  Fassung“ finden Sie unter www.bayer.de/GB17
 A Zusammengefasster LageberichtFehler! Kein Text mit angegebener Formatvorlage im Dokument.
 Bayer-Geschäftsbericht 2017 1EBITDAvor Sondereinflüssen KonzernergebnisUmsatzLieferantenmanagement
 Investitionen in Forschung und EntwicklungBereinigtesErgeb'''])
print(z)
#%%
z = classify.predict([training_data[21]])
print(z)
   
#%% 
import numpy as np
z = classify.predict(training_data)
print(z)    
print(training_categories)
np.mean(z == training_categories)
#%%
from sklearn.linear_model import SGDClassifier
classify2 = Pipeline([('vect', CountVectorizer()), 
                      ('tfidf', TfidfTransformer()),
                      ('clf-svm', SGDClassifier(loss='hinge', penalty='l2',alpha=1e-3, max_iter=5, random_state=42))])

classify2 = classify2.fit(training_data, training_categories)
#%%
z = classify2.predict([training_data[21]])
print(z)
   
#%% 
import numpy as np
z = classify2.predict(training_data)
print(z)    
print(training_categories)
np.mean(z == training_categories)
#%%
z = classify2.predict(['''eiterte Fassung) vor. Diese Online-Fassung enthält  neben dem Anhang als Teil 
                des  Bayer-Konzernabschlusses  weiterführende Informatio-nen  zum Lagebericht.
                Den „Geschäftsbericht 2017 – Erweiterte  Fassung“ finden Sie unter www.bayer.de/GB17
 A Zusammengefasster Lagebericht
 Bayer-Geschäftsbericht 2017 1EBITDAvor Sondereinflüssen KonzernergebnisUmsatzLieferantenmanagement
 Investitionen in Forschung und EntwicklungBereinigtesErgeb'''])
print(z)
#%%
import pickle
filename = 'text_model.sav'
pickle.dump(classify2, open(filename, 'wb'))
#%%