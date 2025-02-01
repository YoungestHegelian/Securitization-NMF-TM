import requests
import datetime
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
    document["content"] = {}
    document["index"] = {}
    root = rsp_etree
    vorspann = root[0]
    for item in vorspann:
        if item.tag == "kopfdaten":
            for i in item:
                for j in i:
                    document["metadata"][j.tag] = unicodedata.normalize("NFKC",j.text)
        elif item.tag == "inhaltsverzeichnis":
            pass
    sitzungsverlauf = root[1]
    for item in sitzungsverlauf:
        if item.tag == "tagesordnungspunkt":
            document["content"][unicodedata.normalize("NFKC",item.attrib["top-id"])] = parse_top(item)

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
    return content

#def parse_paragraph(paragraph: ElementTree.Element):
#    content = {}
#    p_ct = 0
#    for item in paragraph:
#        if item.text:
#            content[f"p_{p_ct}"] = unicodedata.normalize("NFKC",item.text)
#            p_ct += 1
#    return content


"""
rsp_dict
    rsp_dict["documents"] (=list)


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

    for item in rsp_etree[1]:
...     if item.tag == "tagesordnungspunkt":
...             item.attrib["top-id"]
...             for i in item:
...                     i.tag ("p"=praesidentin?,"rede"=List("p","kommentar","name")), i.text
"""