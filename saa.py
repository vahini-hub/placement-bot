import zipfile
from docx import Document

# Updated file path
WORD_FILE = r"C:\Users\malip\OneDrive\Documents\placepment\placepment plan.docx"

# Check if it's a valid DOCX
if zipfile.is_zipfile(WORD_FILE):
    print("Valid DOCX!")
else:
    print("NOT a valid DOCX!")

# Open the DOCX
doc = Document(WORD_FILE)
print("File opened successfully!\n")

# Print all paragraphs
for i, para in enumerate(doc.paragraphs, start=1):
    print(f"{i}: {para.text}")
