from grobid_client.grobid_client import GrobidClient
import os
import xml.etree.ElementTree as ET


ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

def get_full_text(el):
    """Recursively extract all text including inline elements."""
    parts = [el.text or ""]
    for child in el:
        parts.append(get_full_text(child))
        parts.append(child.tail or "")
    return "".join(parts).strip()

# def extract_frontmatter(root):
#     ns = {"tei": "http://www.tei-c.org/ns/1.0"}

#     # Title
#     title = get_full_text(root.find(".//tei:titleStmt/tei:title", ns)) or "Untitled"

#     # Authors (from <sourceDesc><analytic><author>)
#     authors = []
#     for author in root.findall(".//tei:fileDesc/tei:sourceDesc//tei:analytic/tei:author", ns):
#         pers = author.find("tei:persName", ns)
#         forename = " ".join([get_full_text(fn) for fn in pers.findall("tei:forename", ns)]) if pers is not None else ""
#         surname = get_full_text(pers.find("tei:surname", ns)) if pers is not None else ""
#         full_name = f"{forename} {surname}".strip()

#         email_el = author.find("tei:email", ns)
#         email = get_full_text(email_el) if email_el is not None else ""

#         affs = []
#         for aff in author.findall("tei:affiliation", ns):
#             org = aff.find("tei:orgName", ns)
#             if org is not None:
#                 affs.append(get_full_text(org))

#         authors.append({
#             "name": full_name,
#             "email": email,
#             "affiliations": affs
#         })

#     # Abstract
#     abstract = get_full_text(root.find(".//tei:profileDesc/tei:abstract", ns) or ET.Element("abstract"))

#     # Keywords
#     keywords = [
#         get_full_text(k) for k in root.findall(".//tei:textClass//tei:term", ns)
#     ]

#     return {
#         "title": title,
#         "authors": authors,
#         "abstract": abstract,
#         "keywords": keywords
#     }


def extract_frontmatter(root):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    # === TITLE ===
    # Try titleStmt/title first
    title_el = root.find(".//tei:titleStmt/tei:title", ns)

    # Fallback to monogr/title if empty or not found
    if title_el is None or not get_full_text(title_el).strip():
        title_el = root.find(".//tei:fileDesc/tei:sourceDesc//tei:monogr/tei:title", ns)

    title = get_full_text(title_el).strip() if title_el is not None else "Untitled"

    # === AUTHORS ===
    author_nodes = root.findall(".//tei:fileDesc/tei:sourceDesc//tei:analytic/tei:author", ns)
    if not author_nodes:
        author_nodes = root.findall(".//tei:fileDesc/tei:sourceDesc//tei:monogr/tei:author", ns)

    authors = []
    for author in author_nodes:
        pers = author.find("tei:persName", ns)
        forename = " ".join([
            get_full_text(fn) for fn in pers.findall("tei:forename", ns)
        ]) if pers is not None else ""
        surname = get_full_text(pers.find("tei:surname", ns)) if pers is not None else ""
        full_name = f"{forename} {surname}".strip()

        email_el = author.find("tei:email", ns)
        email = get_full_text(email_el) if email_el is not None else ""

        affs = []
        for aff in author.findall("tei:affiliation", ns):
            org = aff.find("tei:orgName", ns)
            if org is not None:
                affs.append(get_full_text(org))

        authors.append({
            "name": full_name,
            "email": email,
            "affiliations": affs
        })

    # === ABSTRACT ===
    abstract_el = root.find(".//tei:profileDesc/tei:abstract", ns)
    abstract = get_full_text(abstract_el) if abstract_el is not None else ""

    # === KEYWORDS ===
    keywords = [
        get_full_text(k) for k in root.findall(".//tei:textClass//tei:term", ns)
    ]

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "keywords": keywords
    }



def extract_sections(div, level=2):
    """Recursively extract sections and subsections into Markdown."""
    lines = []

    head = div.find("tei:head", ns)
    if head is None:
        return []  # skip divs without section titles

    title = get_full_text(head)
    number = head.attrib["n"] if "n" in head.attrib else ""
    heading = f"{'#' * level} {number} {title}".strip()
    lines.append(heading + "\n")

    for p in div.findall("tei:p", ns):
        para = get_full_text(p)
        if para:
            lines.append(para + "\n")

    for fig in div.findall("tei:figure", ns):
        caption = get_full_text(fig)
        if caption:
            lines.append(f"**Figure:** {caption}\n")

    # Handle subsections recursively
    for sub_div in div.findall("tei:div", ns):
        lines.extend(extract_sections(sub_div, level + 1))

    return lines

def extract_bibliography(root):
    """Extract references from <listBibl>."""
    lines = ["## References\n"]
    bibs = root.findall(".//tei:listBibl/tei:biblStruct", ns)
    for i, bibl in enumerate(bibs, 1):
        ref_text = get_full_text(bibl)
        lines.append(f"[{i}] {ref_text}\n")
    return lines

def parse_tei_full_markdown(tei_path):
    """Main function to parse full TEI XML and return Markdown text."""
    tree = ET.parse(tei_path)
    root = tree.getroot()

    md_lines = []

    # Front matter
    front = extract_frontmatter(root)
    md_lines.append(f"# {front['title']}\n")
    if front["authors"]:
        md_lines.append("**Authors:**\n")
        for author in front["authors"]:
            line = f"- {author['name']}"
            if author["email"]:
                line += f" <{author['email']}>"
            if author["affiliations"]:
                line += f" ({'; '.join(author['affiliations'])})"
            md_lines.append(line)
    if front["keywords"]:
        md_lines.append(f"**Keywords:** {', '.join(front['keywords'])}\n")
    if front["abstract"]:
        md_lines.append(f"**Abstract:**\n\n{front['abstract']}\n")

    # Sections
    divs = root.findall(".//tei:text/tei:body/tei:div", ns)
    for div in divs:
        md_lines.extend(extract_sections(div))

    # Bibliography
    bib_lines = extract_bibliography(root)
    if len(bib_lines) > 1:
        md_lines.extend(bib_lines)

    return "\n".join(md_lines)



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



# sections = parse_tei_sections_loose("./tei_output/aa20674-12.grobid.tei.xml")

# for sec in sections:
#     print(f"\n--- {sec['title']} ---\n")
#     print(sec['text'][:50000], "\n")  # print first 500 chars


# Converting TEI to Markdown
markdown_text = parse_tei_full_markdown("./tei_output/Thesis_de_Meulenaer.grobid.tei.xml")

# Save to file
with open("vizualize.md", "w", encoding="utf-8") as f:
    f.write(markdown_text)

# Optional: print preview
print(markdown_text[:1000])


# tei_path = "./tei_output/aa20674-12.grobid.tei.xml"
# tree = ET.parse(tei_path)
# root = tree.getroot()

# authors = extract_authors(root)

# print("Extracted authors:\n")
# for author in authors:
#     print("-", author)