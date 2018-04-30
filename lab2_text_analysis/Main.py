# -*- coding: utf8 -*-
from pyspark import SparkContext, SparkConf
from pyspark.sql import Row
from pyspark.sql.functions import regexp_replace, col, udf
from langdetect import detect
from spacy.lemmatizer import Lemmatizer
from spacy.lang.en import LOOKUP as enlook
from spacy.lang.de import LOOKUP as delook
from pyspark.sql.types import StringType
from pyspark.ml.feature import Tokenizer, StopWordsRemover
from pyspark.sql.functions import explode
from pyspark.sql import HiveContext
import pyspark.sql.functions as func

conf = SparkConf().setAppName('MyFirstStandaloneApp')
sc = SparkContext(conf=conf)
#sqlContext = sql.SQLContext(sc)
hiveContext = HiveContext(sc)
hiveContext.setConf("hive.metastore.uris", "thrift://s12m.westeurope.cloudapp.azure.com:9083");

class WordCount:
    def __init__(self, dataframe):
        self.dataframe = dataframe

    def transform(self):
        df2 = self.dataframe.withColumn("_2", regexp_replace(col("_2"), "[\"'./§$&+,:;=?@#–|'<>.^*()%!-]", ""))
        df = df2.withColumn("_2", regexp_replace(col("_2"), "\\s{2,}", ""))

        language_detect = udf(lambda x: detect(x), returnType=StringType())
        df3 = df.withColumn("lang", language_detect('_2'))

        lemmatizer = Lemmatizer(lookup=delook)
        lemmatizer1 = Lemmatizer(lookup=enlook)
        tokenizer = Tokenizer(inputCol="_2", outputCol="words")
        tokenized = tokenizer.transform(df3)
        # print(tokenized)

        lemma = udf(lambda x, lang: True if lang == "de" " ".join([lemmatizer.lookup(i) for i in x]) else " ".join(
            [lemmatizer1.lookup(i) for i in x]), returnType=StringType())

        lemmatized = tokenized.withColumn("stemmed", lemma(col('words'), col('lang'))).drop('words').drop('_2')
        tokenizer = Tokenizer(inputCol="stemmed", outputCol="words")
        tokenized = tokenizer.transform(lemmatized)
        remover = StopWordsRemover(inputCol="words", outputCol="filtered")
        stopwords = remover.loadDefaultStopWords("german") + remover.loadDefaultStopWords("english")
        remover = remover.setStopWords(stopwords)
        newDataSet = remover.transform(tokenized)

        test = newDataSet.withColumn("filtered", explode(col("filtered"))) \
            .groupBy("_1", "filtered") \
            .agg(func.count(func.lit(1)).alias("count")) \
            .sort(col("count").desc())

        return test


text_file = sc.wholeTextFiles("hdfs:/user/zeppelin/wackerdetxt").toDF()
wc = WordCount(text_file)
test = wc.transform()

test.write.mode("overwrite").saveAsTable("detest")
#sqlContext.refreshTable("wordCount1")
test.show()

