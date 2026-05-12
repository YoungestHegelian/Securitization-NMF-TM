import requests
import datetime
import re
import json
import time
import unicodedata
from xml.etree import ElementTree

DIP_API_KEY="OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"

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
    if rsp_dict['cursor']:
        search_cursor = rsp_dict['cursor']
    ids = {}
    for document in rsp_dict["documents"]:
            ids[document["titel"]] = document["id"]
    
    while search_cursor != None:
        print("Sending additional request with cursor: ",search_cursor)
        
        response = requests.get(url + f"&cursor={search_cursor}",headers={"Authorization": auth_header})
        rsp_docs = response.json()['documents']
        if len(rsp_docs) > 0:
            for document in rsp_docs:
                rsp_dict['documents'].append(document)
            #print([rsp_dict['documents']])
        new_search_cursor = response.json()['cursor']
        for document in rsp_dict["documents"]:
            ids[document["titel"]] = document["id"]
        if search_cursor == new_search_cursor:
            break
        search_cursor = new_search_cursor
        time.sleep(1)

    print("Found {} documents".format(rsp_dict["numFound"]))
    
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
    try:
        response = requests.get(url,headers={"Authorization":auth_header})
    except requests.exceptions.SSLError:
        time.sleep(0.5)
        response = requests.get(url,headers={"Authorization":auth_header})
    rsp_etree = ElementTree.fromstring(response.content)

    return rsp_etree

def get_protocol_text_xml(url: str): 
    if url[-4:] != ".xml":
        raise TypeError
    else:
        try:
            response = requests.get(url)
        except requests.exceptions.SSLError:
            time.sleep(0.5)
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
    #print(f"Parsed document {rsp_etree}")
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
    #print("Parsed TOP")
    return content

def parse_speech(speech: ElementTree.Element):
    """
    parse a single speech.still needs: speaker (incl. party affiliation)
    """
    content = {}
    content["speaker"] = {}
    content["speaker"]["rolle"] = None
    content["speaker"]["fraktion"] = None
    p_ct = 0
    cmt_ct = 0
    for item in speech:
        if len(item.attrib.keys()) > 0:
            if item.attrib["klasse"] == "redner":
                for element in item:
                    if element.tag == "redner":
                        for se in element:
                            if se.tag == "name":
                                for i in se:
                                    if i.tag == "vorname":
                                        content["speaker"]["first_name"] = i.text
                                    elif i.tag == "nachname":
                                        content["speaker"]["last_name"] = i.text
                                    elif i.tag == "rolle":
                                        for j in i:
                                            if j.tag == "rolle_lang":
                                                content["speaker"]["rolle"] = j.text
                                    elif i.tag == "fraktion":
                                        content["speaker"]["fraktion"] = i.text
        #except KeyError:
        #    continue

        if item.tag == "p" and item.text:
            content[f"p_{p_ct}"] = unicodedata.normalize("NFKC",item.text)
            p_ct += 1
        elif item.tag == "kommentar":
            content[f"comment_{cmt_ct}"] = unicodedata.normalize("NFKC",item.text)
            #print(item.text)
            cmt_ct += 1
    #print("Parsed speech")
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

    #print("Parsed index")
    return parsed_index
 
from tqdm import tqdm
def collector(start_date: str):
    protocols = {}
    rsp_dict, ids = get_protocol_ids(start_date,end_date="2025-03-18")
    for document in tqdm(rsp_dict["documents"],desc="Creating Database "):
        url = None
        try:
            url = document["fundstelle"]["xml_url"]
        except KeyError:
            print(f"Document {document['id']} has no xml url")
        if url:
            rsp_xml = get_protocol_text_xml(url)
            protocol = parse_xml(rsp_xml)
            protocols[document["id"]] = protocol
            filename = f"BT_Protocol_{document['id']}.json"
            storage_dir = "utils/protocols/"
            path = storage_dir + filename
            with open(path,"w") as file:
                json.dump(protocol,file)
            time.sleep(3)
    print(f"WROTE PROTOCOLS TO {path}")
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
    collector(start_date)
    
    
    
    #exit(0)

if __name__ == "__main__":
    q = input("Run main() ? y/n\n")
    if q == "y":
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

for doc in documents:
     for top in doc["content"].values():
             for key,value in top.items():
                     if type(top[key]) == dict:
                             if top[key]["speaker"]["fraktion"]:
                                     n1 = top[key]["speaker"]["first_name"]
                                     n2 = top[key]["speaker"]["last_name"]
                                     fr = top[key]["speaker"]["fraktion"]
                                     print(f"{n1} {n2}\t\t{fr}")

"""