from prelim_analysis import load_json, get_content
import asyncio
from tqdm import tqdm

raw_protocols = load_json()

async def preprocess_document(protocol):
    processed_document = get_content(protocol,preserve_content=True)
    return processed_document

async def main():
    """
    Usage: run python3 -i process-async.py
    """
    protocols = []
    for p in tqdm(raw_protocols.keys(),desc="Parsing protocols"):
        protocol = await preprocess_document(raw_protocols[p])
        protocols.append(protocol)
    print("Finished protocol preprocessing")
    return protocols
        
#if __name__ == "__main__":
protocols = asyncio.run(main())
