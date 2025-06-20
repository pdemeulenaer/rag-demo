from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Title, NarrativeText, ListItem

# Step 1: Load and chunk the PDF
elements = partition_pdf(
    filename="/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf",
    strategy="hi_res",
    infer_table_structure=False
)

# Step 2: Iterate and group content by section
sections = []
current_section = {"title": "Introduction", "content": []}  # Default/fallback section

for element in elements:
    if isinstance(element, Title):
        # Start of a new section
        if current_section["content"]:
            sections.append(current_section)
        current_section = {"title": element.text.strip(), "content": []}
    else:
        current_section["content"].append(element.text.strip())

# Append last section
if current_section["content"]:
    sections.append(current_section)

# Step 3: Print sections
for i, section in enumerate(sections):
    print(f"=== Section {i+1}: {section['title']} ===")
    print("\n".join(section['content'][:100]))  # Show only first 3 chunks
    print("\n---\n")




# from unstructured.partition.pdf import partition_pdf
# from unstructured.documents.elements import Title

# # Load and chunk the PDF
# elements = partition_pdf(
#     filename="/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf",  # Replace with your file path
#     strategy="fast", # "hi_res",                # or "fast" for speed
#     infer_table_structure=False
# )

# for element in elements:
#     if len(element.text)>100:
#         print(f"Type: {type(element).__name__}")
#         print(f"Text: {element.text}")
#         print(f"Metadata: {element.metadata}\n")

# # # Group content by section
# # chunks = []
# # current_section = {"title": None, "content": []}

# # for el in elements:
# #     if isinstance(el, Title):
# #         if current_section["title"] or current_section["content"]:
# #             chunks.append(current_section)
# #         current_section = {"title": el.text.strip(), "content": []}
# #     else:
# #         if el.text:
# #             current_section["content"].append(el.text.strip())

# # # Append final section
# # if current_section["title"] or current_section["content"]:
# #     chunks.append(current_section)

# # # Write chunks to file
# # with open("chunks_output.txt", "w", encoding="utf-8") as f:
# #     for i, chunk in enumerate(chunks, start=1):
# #         title = chunk["title"] or f"Untitled Section {i}"
# #         content = "\n".join(chunk["content"])
# #         f.write(f"=== Section {i}: {title} ===\n")
# #         f.write(content)
# #         f.write("\n\n")
