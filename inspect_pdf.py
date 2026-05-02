"""
Finds pages with actual IS standards and shows raw text.
"""
import pdfplumber
import re

pdf_path = "BIS_SP21.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    found = 0
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        if re.search(r'IS\s*:?\s*\d{3,6}', text) and len(text) > 200:
            print(f"\n{'='*60}")
            print(f"PAGE {page_num+1}")
            print('='*60)
            print(text[:2000])
            found += 1
            if found >= 5:
                break
