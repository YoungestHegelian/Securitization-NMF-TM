import json
import os
import pandas as pd
from pathlib import Path
import datetime
from typing import List, Optional
import re
import string


from preprocessing import preprocess
class Protocol:
    def __init__(self,date: datetime.datetime,content: str,id: str, preserve_content: bool):
        self.date = date
        self.content = content
        self.id = id
        self.preserve_content = preserve_content
        self.dictionary, self.vectors = preprocess(content)

        #↓ remove this for nmf modeling; requires content as List[str]
        if not self.preserve_content:
            self.content = None

    def __str__(self):
        return f"Protocol {self.date.strftime('%d.%m.%Y')}"

storage_dir = "utils/protocols"
storage_path = Path(storage_dir)

def load_json() -> dict:
    protocols = {}
    for file in storage_path.iterdir():
        with open(file,'r') as f:
            json_object = json.load(f)
            json_object['metadata']['datum'] = date_formatter(json_object['metadata']['datum'])
            json_object['metadata']['word_count'] = get_word_count(json_object)
            protocols[file.name.split("_",2)[-1].split(".")[0]] = json_object

    return protocols

def date_formatter(raw_date):
    months_ger = {
        "Januar":'1',
        "Februar":'2',
        "März":'3',
        "April":'4',
        "Mai":'5',
        "Juni":'6',
        "Juli":'7',
        "August":'8',
        "September":'9',
        "Oktober":'10',
        "November":'11',
        "Dezember":'12'
    }
    date_items = raw_date.split()
    relevant_date_items = date_items[-3:]
    day = relevant_date_items[0].rstrip(".")
    month = months_ger[relevant_date_items[1]]
    year = relevant_date_items[2]
    datestring = f"{year}-{month}-{day}"

    date = datetime.datetime.strptime(datestring,"%Y-%m-%d")

    return date

def get_word_count(protocol) -> int:
    wc = 0
    for top in protocol["content"]:
        for id, content in protocol["content"][top].items():
            if type(content) == list:
                wc += len(content.split())
            elif type(content) == dict:
                for p,c in protocol['content'][top][id].items():
                    if type(c) == str:
                        wc += len(c.split())
            elif type(content) == str:
                wc += len(content.split())
    return wc

def get_content(protocol: dict, preserve_content: Optional[bool]) -> Protocol:
    """
    Parse raw protocol dict and return Protocol class
    """
    raw_content = ""
    date = protocol['metadata']['datum']
    id = protocol['metadata']['sitzungsnr']
    content = protocol['content']
    for top in content.keys():
        top_content = content[top]
        #print("TOP CONTENT",top_content["p_0"])
        for key,value in top_content.items():
            # match case re works differently rework
            # enhance parsing: needs pre-.lowering, filter out punctuation and such
            if re.match("p_[0-9][0-9]|p_[0-9]",str(key)):
                for word in value.split():
                    #parsed_word = word.translate(str.maketrans('','',string.punctuation)) + " " 
                    raw_content += word.lower() + " "
            if re.match("speech_[0-9][0-9]|speech_[0-9]",key):
                for p,s in top_content[key].items():
                    if re.match(r"p_[0-9][0-9]|p_[0-9]",p):
                        for word in s.split():
                            #psw = s.translate(str.maketrans('','',string.punctuation)) + " "
                            raw_content += word.lower() + " "
        #print(f"FINISHED PARSING {top}")

    if preserve_content:
        if preserve_content == True:
            return Protocol(date=date,content=raw_content,id=id,preserve_content=True)
        elif preserve_content == False:
            return Protocol(date=date,content=raw_content,id=id,preserve_content=False)
    else:
        return Protocol(date=date,content=raw_content,id=id,preserve_content=False)



def get_index_by_month(protocols) -> List[dict]:
    month_index = {}
    sorted_month_index = {}

    for id,content in protocols.items():
        date = content['metadata']['datum']
        my = f"{date.month}/{date.year}"
        try:
            month_index[my].append(list(content['index'].values()))
        except KeyError:
            month_index[my] = [ i for i in content['index'].values()]

    datelist = []
    for key in month_index.keys():
        datelist.append(key)
    datelist = sorted(datelist, key=lambda x: datetime.datetime.strptime(x,"%m/%Y"))

    for dateindex in datelist:
        sorted_month_index[dateindex] = month_index[dateindex]

    
    return [month_index,sorted_month_index]


"""for top in content.keys():
...     top_content = content[top]
...     for key,value in top_content.items():
...             if re.match("speech_[0-9][0-9]|speech_[0-9]",key):
...                     for p,s in top_content[key].items():
...                             if re.match(r"p_[0-9][0-9]|p_[0-9]",p):
...                                     for word in s.split():
...                                             raw_content += word + " "
"""



