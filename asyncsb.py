import asyncio
import nest_asyncio
import requests
import unicodedata
from xml.etree import ElementTree

url = ""

async def get_protocol_text_xml(url: str): 
    if url[-4:] != ".xml":
        raise ValueError
    else:
        async with requests.get(url) as response:
            return await ElementTree.fromstring(response.content)
        
async def parse_response(response: ElementTree.Element):
    async with await get_protocol_text_xml(url) as response:
        document = {}
        document["metadata"] = {}
        document["content"] = {}
        root = response
        vorspann = root[0]
        for item in vorspann:
            if item.tag == "kopfdaten":
                for i in item:
                    for j in i:
                        document["metadata"][j.tag] = unicodedata.normalize("NFKC",j.text)
    
        sitzungsverlauf = root[1]
        for item in sitzungsverlauf:
            if item.tag == "tagesordnungspunkt":
                document["content"][unicodedata.normalize("NFKC",item.attrib["top-id"])] = await parse_top(item)

    yield document