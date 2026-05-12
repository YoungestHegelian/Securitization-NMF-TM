import nltk
import pandas as pd
from typing import List

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.stem.cistem import Cistem
from collections import defaultdict

from gensim import corpora



lemmatizer = WordNetLemmatizer()
german_stemmer = Cistem()

def _full_stopword_list() -> List[str]:
    filename = "abgeordnete_namen.txt"
    stop_words = stopwords.words('german')
    with open(filename,'r') as f:
        names = f.readlines()

    for name in names:
        full_name = name.strip().split(" ")
        stop_words.append(full_name[0].lower())
        stop_words.append(full_name[1].lower())

    with open("custom_stopwords.txt",'r') as f:
        custom_stop_words = f.read()

    custom_stop_words = custom_stop_words.split("\n")

    for w in custom_stop_words:
        stop_words.append(w)

    return set(stop_words)

stop_words = _full_stopword_list()

def preprocess(raw_content):
    tokens = word_tokenize(raw_content.lower())
    tokens = [w for w in tokens if w.isalpha()]
    tokens = [w for w in tokens if w not in stop_words]
    tokens = [lemmatizer.lemmatize(w) for w in tokens]
    # ↓ german stemmer trial run; maybe tryout in REPL and see ?
    # tokens = [german_stemmer.stem(w) for w in tokens]
    
    freq = defaultdict(int)
    for token in tokens:
        freq[token] += 1
        
    tkns = [
    [token for token in tokens if freq[token] > 1]
    ]

    dictionary = corpora.Dictionary(tkns)

    vectors = dictionary.doc2bow(raw_content.lower().split())

    return dictionary, vectors