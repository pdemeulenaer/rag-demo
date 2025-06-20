from papermage.recipes import CoreRecipe

PDF_PATH = "/home/philippe/Documents/Github/rag-demo/src/rag_demo/folder/aa20674-12.pdf"

recipe = CoreRecipe()
doc = recipe.run(PDF_PATH)

# Print text of each section
for section in doc.sections:
    section_title = section.title.text if section.title else "Unknown"
    section_text = section.text.strip() if section.text else ""
    print(f"\n=== SECTION: {section_title} ===\n")
    print(section_text if section_text else "[No text available]")


# for page in doc.pages:
#     print(f'\n=== PAGE: {page.id} ===\n\n')
#     for row in page.rows:
#         print(row.text)

# for section in doc.sections:
#     print(section)
      

# import json
# with open('filename.json', 'w') as f_out:
#     json.dump(doc.to_json(), f_out, indent=4)        