global raw_protocols
import os
from process_async import protocols as raw_protocols

import json
from typing import List
from prelim_analysis import Protocol

from collections import defaultdict
from gensim import corpora, logging
import pandas as pd
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from itertools import combinations
from gensim.models import Word2Vec

from sklearn.decomposition import NMF, LatentDirichletAllocation, MiniBatchNMF
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sec_terms_2 import sec_terms_2 as sec_terms
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
# sort by time 

raw_protocols.sort(key=lambda item: item.date)

def generate_ldaseq_dataset(protocols: List[Protocol]):
    global raw_protocols
    corpus = []
    ppm = {}
    
    dictionary = corpora.Dictionary()
    for p in tqdm(protocols,desc="Preparing LDASEQ data"):
        # append vectors to corpus
        corpus.append(p.vectors)
        # append protocol dictionary to dataset dictionary
        dictionary.merge_with(p.dictionary)
        date = p.date
        my = f"{date.month}/{date.year}"
        try:
            ppm[my].append(p.id)
        except KeyError:
            ppm[my] = [p.id]
        raw_protocols = raw_protocols[1:]


    return corpus, dictionary, ppm



def bin_by_month(protocols: List[Protocol]) -> dict:
    month_binned_protocols = {}
    for protocol in tqdm(protocols, desc="Timescale binning"):
        # get month/year time bin
        date = protocol.date
        my = f"{date.month}/{date.year}"
        try:
            month_binned_protocols[my].append([protocol.vectors])
        except KeyError:
            month_binned_protocols[my] = [protocol.vectors]

    return month_binned_protocols



#DTM (LDA)
# gensim ldaseqmodel
from gensim.models import ldaseqmodel

print("GENERATING LDASEQ DATASET")

corpus, dictionary, ppm = generate_ldaseq_dataset(raw_protocols)

count_ppm = {}

for key,value in ppm.items():
    count_ppm[key] = len(value)

#collect protocol ids and groupby quarter
df = pd.DataFrame.from_dict(count_ppm,orient='index',columns=['doc_ids'])
df.index = pd.PeriodIndex(df.index,freq='Q')
df = df.groupby(df.index).sum()

doc_lengths = df['doc_ids'].values.tolist()

q2 = input("INITIALIZE LDASEQMODEL? y/n\n")
if q2.lower() == "y":
    print("Starting...",end="")
    ldaseq = ldaseqmodel.LdaSeqModel(
        corpus=corpus,
        id2word=dictionary,
        time_slice=doc_lengths,
        num_topics=15,
        em_max_iter=10)
    print(" Finished")

def visualize_topic_distribution_over_time(model: ldaseqmodel.LdaSeqModel):
    num_topics = model.num_topics
    num_docs = 214
    data = []
    for d in range(0,num_docs,1):
        data.append(model.doc_topics(d))
    
    df = pd.DataFrame(data)
    return df

#NMF

n_samples = 2000
n_features = 1000
n_components = 20
n_top_words = 20
batch_size = 128
init = "nndsvda"
max_df = 0.95
min_df = 2

from preprocessing import stop_words

def layer_one_nmf(protocols,max_df=0.9,min_df=0.2):
    print("Starting NMF")
    ts_nmf_models = []
    
    i = 0
    for qslice in doc_lengths:

        #for q in protocols[i:qslice + i]:
        print(f"Analyzing protocols {i} - {qslice+i}")
        tfidf_vectorizer = TfidfVectorizer(
            max_df=max_df, min_df=min_df, max_features=n_features, stop_words=list(stop_words)
        )
        tfidf = tfidf_vectorizer.fit_transform([p.content for p in protocols[i:qslice + i]])
        terms = list(tfidf_vectorizer.get_feature_names_out())
        nmf = NMF(
            n_components=n_components,
            init="random"
        )
        
        W = nmf.fit_transform(tfidf)
       
        H = nmf.components_
       
        ts_nmf_models.append((W,H,terms))
        i = qslice + i
    print("Finished")
    return ts_nmf_models

def get_descriptor(terms,H,topic_index,top):
    top_indices = np.argsort(H[topic_index,:])[::-1]
    top_terms = []
    for term_index in top_indices[0:top]:
        top_terms.append(terms[term_index])
    return top_terms

def plot_top_term_weights(terms,H,topic_index,top):
    
    top_indices = np.argsort(H[topic_index,:])[::-1]
    top_terms = []
    top_weights = []
    for term_index in top_indices[0:top]:
        top_terms.append(terms[term_index])
        top_weights.append(H[topic_index,term_index])
    top_terms.reverse()
    top_weights.reverse()
    fig = plt.figure(figsize=(13,8))
    ypos = np.arange(top)
    ax = plt.barh(ypos, top_weights, align="center", color="green",tick_label=top_terms)
    plt.xlabel("Term Weight",fontsize=14)
    plt.tight_layout()

def calculate_coherence(w2v_model,term_rankings):
    overall_coherence = 0.0
    for topic_index in range(len(term_rankings)):
        pair_scores = []
        for pair in combinations( term_rankings[topic_index], 2 ):
            try:
                similarity = w2v_model.wv.similarity(pair[0],pair[1])
            except KeyError:
                similarity = 0
            pair_scores.append( similarity )
        topic_score = sum(pair_scores) / len(pair_scores)
        overall_coherence += topic_score
   
    return overall_coherence / len(term_rankings)


def plot_top_words(ts_nmf_models,index):
    fig, axes = plt.subplots(3,5)
    axes = axes.flatten()
    for topic_idx,topic in enumerate(ts_nmf_models[index][0].components_):
        top_features_ind = topic.argsort()[-n_top_words:]
        top_features = ts_nmf_models[index][1][top_features_ind]
        weights = topic[top_features_ind]
        ax = axes[topic_idx]
        ax.barh(top_features,weights,height=0.7)
        ax.set_title(f"Topic {topic_idx+1}")
        ax.tick_params(axis="both",which="major",labelsize=20)
        for i in "top right left".split():
            ax.spines[i].set_visible(False)
        plt.subplots_adjust(top=0.90, bottom=0.05, wspace=0.90, hspace=0.3)
        fig.suptitle(f"MiniBatchNMF - {df.index[index].__str__()}",fontsize=40)


def load_nmf_model():
    ts_nmf = []
    base_dir = "models/nmf/model"
    timeslice_models = ['nmf_0', 'nmf_1', 'nmf_2', 'nmf_3', 'nmf_4', 'nmf_5', 'nmf_6', 'nmf_7', 'nmf_8', 'nmf_9','nmf_10', 'nmf_11', 'nmf_12', 'nmf_13',]
    for ts_dir in timeslice_models:
        ts_data = os.listdir(base_dir +"/" + ts_dir)
        w_path = base_dir + "/" + ts_dir + "/" + ts_data[1]
        h_path = base_dir + "/" + ts_dir + "/" + ts_data[0]
        text_path = base_dir + "/" + ts_dir + "/" + ts_data[2]
        with open(text_path,"r") as textfile:
            text = textfile.readlines()
        ts_nmf.append((np.load(w_path),np.load(h_path),text))
    return ts_nmf

def get_nmf_words(ts_nmf):
    df_words = pd.DataFrame()
    for i,ts in enumerate(ts_nmf):
        for t in range(n_components):
            top_terms = get_descriptor(ts[2],ts[1],t,20)
            c = 0
            for term in top_terms:
                if term.strip() in sec_terms:
                    c+=1
            df_words.loc[i,t] = c
    return df_words

def get_avg_topic_weight_nmf(ts_nmf):
    df_avg = pd.DataFrame()
    for i,ts in enumerate(ts_nmf):
        weights = ts[0]
        num_docs = len(weights)
        for t in range(n_components):
            topic_weights = []
            for doc in weights:
                    topic_weights.append(doc[t])
            topic_avg_weight = sum(topic_weights)/num_docs
            df_avg.loc[i,t] = topic_avg_weight
    return df_avg

def get_si_pos_neg_weights(df_words: pd.DataFrame, df_weights: pd.DataFrame) -> pd.DataFrame:
    df_weights["si_weights_total"] = df_weights[df_words.astype(bool) == True].sum(axis=1)
    df_weights["no_si_weights_total"] = df_weights.drop("si_weights_total",axis=1)[df_words.astype(bool) == False].sum(axis=1)
    return df_weights

def gen_sec_topics_df_nmf():
    zeros = np.zeros((14,20))
    df_sec_topics = pd.DataFrame(zeros,columns=[i for i in range(20)])
    sec_topics = [[13], [0,4,8,13,16,17], [2,6,14], [11], [9], [2,4,7,12], [3], [11], [15], [5,6,19], [0,2,15,18], [1], [], [7] ]
    for i,t in enumerate(sec_topics):
        if len(t) != 0:
            df_sec_topics.loc[i,t] = 1

    return df_sec_topics

def plot_nmf_topics(df_words: pd.DataFrame):
    df_words["sec_voc"] = df_words.astype(bool).sum(axis=1)
    df_words["sec_pol"] = [1,6,4,1,1,3,1,1,1,3,4,1,0,1]
    df_words["sec_clean"] = df_words["sec_voc"] - df_words["sec_pol"]
    m1,b1 = np.polyfit(df_words.index,df_words["sec_voc"],1)
    m2,b2 = np.polyfit(df_words.index,df_words["sec_pol"],1)
    #m3,b3 = np.polyfit(df_words.index,df_words["sec_clean"],1)
    plt.plot(df_words.index,df_words["sec_voc"],label="Themen - Sicherheitsvokabular (Tsv)")
    plt.plot(df_words.index,m1*df_words.index+b1,color="black",linestyle="--",label="Regressionsgerade")
    #plt.plot(df_words.index,df_words["sec_pol"],label="Themen - Sicherheitspolitik (Tsp)")
    #plt.plot(df_words.index,m2*df_words.index+b2,color="black",linestyle="--",label="Regressionsgerade")
    #plt.plot(df_words.index,df_words["sec_clean"],label="Tsv - Tsp")
    #plt.plot(df_words.index,m3*df_words.index+b3,color="black",linestyle="--")
    
    plt.xticks(df_words.index,["Q4 2021","Q1 2022","Q2 2022","Q3 2022","Q4 2022","Q1 2023","Q2 2023","Q3 2023","Q4 2023","Q1 2024","Q2 2024","Q3 2024","Q4 2024","Q1 2025"],rotation=90)
    plt.ylabel("Anzahl Themen")
    plt.xlabel("Quartal")
    plt.title("Themenentwicklung - NMF")
    plt.legend()


def get_tops_by_quarter():
    doc_slices = [9, 17, 19, 13, 19, 18, 18, 13, 19, 16, 18, 10, 19, 6]
    base_dir = "utils/protocols"
    doc_tops = {}
    for doc in os.listdir(base_dir):
        doc_path = base_dir + "/" + doc
        with open(doc_path,"r") as f:
            doc_content = json.load(f)
        doc_id = doc_content["metadata"]["sitzungsnr"]
        doc_index = doc_content["index"]
# layer 2
# 
# nmf_model.fit()
