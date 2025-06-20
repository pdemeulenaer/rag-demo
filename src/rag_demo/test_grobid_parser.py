from grobid_client.grobid_client import GrobidClient
import os
import xml.etree.ElementTree as ET


def parse_tei_sections_loose(tei_path):
    tree = ET.parse(tei_path)
    root = tree.getroot()
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # Find all <div> inside <body>
    divs = root.findall(".//tei:text/tei:body/tei:div", ns)
    sections = []

    for div in divs:
        title_elem = div.find("tei:head", ns)
        title = title_elem.text.strip() if title_elem is not None else "Untitled"

        paragraphs = [
            p.text.strip()
            for p in div.findall("tei:p", ns)
            if p.text and p.text.strip()
        ]
        text = "\n".join(paragraphs)

        if text:
            sections.append({
                "title": title,
                "text": text
            })

    return sections


# Init client
client = GrobidClient(config_path="grobid_config.json")

# Ensure output directory exists
os.makedirs("./tei_output", exist_ok=True)

# Input folder (must be a directory, not a file)
pdf_folder = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/one_pdf/"
os.makedirs(pdf_folder, exist_ok=True)

# Copy your PDF into this folder
# e.g., cp /path/to/paper.pdf ./pdf_input/

# # Process all PDFs in the folder
# client.process(
#     "processFulltextDocument",
#     pdf_folder,
#     "./tei_output",
#     consolidate_header=True,
#     consolidate_citations=True
# )


sections = parse_tei_sections_loose("./tei_output/aa20674-12.grobid.tei.xml")

for sec in sections:
    print(f"\n--- {sec['title']} ---\n")
    print(sec['text'][:50000], "\n")  # print first 500 chars

