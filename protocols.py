import requests
import datetime
import re
import json
import unicodedata
from xml.etree import ElementTree

DIP_API_KEY="I9FKdCn.hbfefNWCY336dL6x62vfwNKpoN2RZ1gp21"

# TO-DO:
# get_protocol_ids(start_date, end_date)
# """get ids for protocols during the specified time"""
# get_protocol_text(id)
# """get full protocol text for protocol id"""

def get_protocol_ids(start_date: str, end_date: str = datetime.datetime.now().strftime("%Y-%m-%d")):
    """
    Get the ids for protocols of sessions within the specified date range.
    start_date: "YYYY-MM-DD" (%Y-%m-%d)
    end_date: "YYYY-MM-DD" (%Y-%m-%d, defaults to datetime.datetime.now())
    returns the document ids as {"doc_title":"id"}
    """ 
    print(f"Getting document ids from {start_date} to {end_date}")
    auth_header = "ApiKey {}".format(DIP_API_KEY)
    url = f"https://search.dip.bundestag.de/api/v1/plenarprotokoll?f.datum.start={start_date}&f.datum.end={end_date}&f.zuordnung=BT"
    response = requests.get(url,headers={"Authorization": auth_header})
    rsp_dict = response.json()
    print("Found {} documents".format(rsp_dict["numFound"]))
    ids = {}
    for document in rsp_dict["documents"]:
        ids[document["titel"]] = document["id"]
    
    return rsp_dict, ids

def get_protocol_data_json(id: str):
    url = f"https://search.dip.bundestag.de/api/v1/plenarprotokoll-text/{id}"
    auth_header = "ApiKey {}".format(DIP_API_KEY)
    response = requests.get(url,headers={"Authorization":auth_header})
    rsp_dict = response.json()

    return rsp_dict

def get_protocol_data_xml(id: str):
    url = f"https://search.dip.bundestag.de/api/v1/plenarprotokoll-text/{id}?format=xml"
    auth_header = "ApiKey {}".format(DIP_API_KEY)
    response = requests.get(url,headers={"Authorization":auth_header})
    rsp_etree = ElementTree.fromstring(response.content)

    return rsp_etree

def get_protocol_text_xml(url: str): 
    if url[-4:] != ".xml":
        raise TypeError
    else:
        response = requests.get(url)
        rsp_etree = ElementTree.fromstring(response.content)
    return rsp_etree

def parse_xml(rsp_etree: ElementTree.Element):
    document = {}
    document["metadata"] = {}
    document["index"] = {}
    document["content"] = {}
    root = rsp_etree
    vorspann = root[0]
    for item in vorspann:
        if item.tag == "kopfdaten":
            for i in item:
                for j in i:
                    document["metadata"][j.tag] = unicodedata.normalize("NFKC",j.text)
        if item.tag == "inhaltsverzeichnis":
            document["index"] = parse_index(item)
    sitzungsverlauf = root[1]
    for item in sitzungsverlauf:
        if item.tag == "tagesordnungspunkt":
            document["content"][unicodedata.normalize("NFKC",item.attrib["top-id"])] = parse_top(item)
    print(f"Parsed document {rsp_etree}")
    return document

def parse_top(top: ElementTree.Element):
    """
    parse a single top.
    """
    content = {}
    speech_ct = 0
    p_ct = 0
    for item in top:
        if item.tag == "rede":
            content[f"speech_{speech_ct}"] = parse_speech(item)
            speech_ct += 1
        elif item.tag == "p" and item.text:
            content[f"p_{p_ct}"] = unicodedata.normalize("NFKC",item.text)
            p_ct += 1
    print("Parsed TOP")
    return content

def parse_speech(speech: ElementTree.Element):
    """
    parse a single speech.still needs: speaker (incl. party affiliation)
    """
    content = {}
    p_ct = 0
    cmt_ct = 0
    for item in speech:
        if item.tag == "p" and item.text:
            content[f"p_{p_ct}"] = unicodedata.normalize("NFKC",item.text)
            p_ct += 1
        elif item.tag == "kommentar":
            content[f"comment_{cmt_ct}"] = unicodedata.normalize("NFKC",item.text)
    print("Parsed speech")
    return content

def parse_index(index: ElementTree.Element):
    parsed_index = {}
    tops = []
    top_descs = []
    
    for iblock in index:
        if iblock.tag == "ivz-block":
            for block in iblock[0:2]:
                if block.tag == "ivz-block-titel":
                    tops.append(unicodedata.normalize("NFKC",block.text.strip()))
                for element in block:
                    if element.text:
                        top_descs.append(unicodedata.normalize("NFKC",element.text.strip()))
                    
    for t, td in zip(tops,top_descs):
        parsed_index[t] = td

    print("Parsed index")
    return parsed_index

def collector(start_date: str):
    protocols = {}
    rsp_dict, ids = get_protocol_ids(start_date)
    for document in rsp_dict["documents"]:
     url = None
     try:
             url = document["fundstelle"]["xml_url"]
     except KeyError:
             print(f"Document {document["id"]} has no xml url")
     if url:
             rsp_xml = get_protocol_text_xml(url)
             protocols[document["id"]] = parse_xml(rsp_xml)

    return protocols

def main():
    start_date_valid = False
    while start_date_valid == False:
        start_date = input("Set start date for document retrieval (YYYY-MM-DD) : ")
        regex = r"^\d{4}-\d{2}-\d{2}"
        if re.match(regex,start_date):
            start_date_valid = True
        else:
            print("WRONG DATE FORMAT")
    protocols = collector(start_date)
    storage_dir = "protocols/"
    filename = f"BT_Protocols_{start_date}_{datetime.datetime.now().strftime(format="%Y-%m-%d")}.json"
    path = storage_dir + filename
    with open(path,"w") as file:
        json.dump(protocols,file)
    print(f"WROTE PROTOCOLS TO {path}")
    
    exit(0)

if __name__ == "__main__":
    main()
"""
rsp_etree l1 branches:
    'id'
    'dokumentart'
    'typ'
    'vorgangsbezug_anzahl'
    'dokumentnummer'
    'wahlperiode'
    'herausgeber'
    'pdf_hash'
    'aktualisiert'
    'vorgangsbezug'
    'vorgangsbezug'
    'vorgangsbezug'
    'vorgangsbezug'
    'fundstelle'
    'text'
    'titel'
    'datum'
"""