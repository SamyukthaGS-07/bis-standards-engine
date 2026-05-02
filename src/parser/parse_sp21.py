"""
BIS SP 21 Parser — Fixed for actual PDF structure
===================================================
Real structure observed:
  SUMMARY OF
  IS 383 : 1970 COARSE AND FINE AGGREGATES FROM NATURAL
  SOURCES FOR CONCRETE
  (Second Revision)
  1. Scope — ...
"""

import re
import json
import argparse
from pathlib import Path
from typing import Optional
import pdfplumber


MATERIAL_CATEGORIES = {
    "Cement": [
        "cement", "opc", "ppc", "portland", "clinker", "fly ash cement",
        "blast furnace", "masonry cement", "rapid hardening", "sulphate",
        "hydrophobic", "white portland", "high alumina",
    ],
    "Steel": [
        "steel", "reinforcement", "rebar", "tmt", "mild steel", "structural steel",
        "wire rod", "iron", "deformed bar", "fe 415", "fe 500", "rolled",
        "cold twisted", "hard drawn", "wire fabric",
    ],
    "Concrete": [
        "concrete", "rcc", "pcc", "prestressed", "ready mix", "ready-mix",
        "admixture", "mix design", "precast", "reinforced concrete",
    ],
    "Aggregates": [
        "aggregate", "coarse aggregate", "fine aggregate", "sand", "gravel",
        "crushed stone", "all-in aggregate", "lightweight aggregate",
    ],
    "Bricks & Masonry": [
        "brick", "masonry", "block", "tile", "clay", "fly ash brick",
        "autoclaved", "aac", "burnt clay", "sand lime",
    ],
    "Waterproofing": [
        "waterproof", "damp proof", "bitumen", "bituminous", "sealant",
        "membrane", "sealing compound", "joint sealant",
    ],
    "Timber & Wood": [
        "timber", "wood", "plywood", "board", "veneer", "fibre board",
        "particle board", "flush door", "wooden",
    ],
    "Paints & Coatings": [
        "paint", "coating", "primer", "varnish", "enamel", "distemper",
        "putty", "whitewash",
    ],
    "Glass": [
        "glass", "glazing", "tempered glass", "laminated glass", "wired glass",
    ],
    "Pipes & Fittings": [
        "pipe", "fitting", "valve", "coupling", "flange", "tube",
        "conduit", "drainage", "sewerage",
    ],
    "Asbestos": [
        "asbestos", "asbestos cement",
    ],
    "Other": [],
}

APPLICATION_KEYWORDS = {
    "structural": ["structural", "load bearing", "load-bearing", "rcc",
                   "prestressed", "foundation", "column", "beam", "reinforced"],
    "finishing": ["finish", "plaster", "render", "surface", "texture", "smooth"],
    "waterproofing": ["waterproof", "damp", "moisture", "leak", "seal", "joint"],
    "thermal": ["thermal", "insulation", "heat", "temperature"],
    "acoustic": ["acoustic", "sound", "noise", "vibration"],
    "general_construction": ["construction", "building", "masonry", "wall", "floor", "roof"],
    "drainage": ["drainage", "sewerage", "sewer", "manhole"],
    "roofing": ["roof", "roofing", "sheet", "corrugated"],
    "lightweight": ["lightweight", "light weight", "aac", "cellular", "aerated"],
}


def detect_category(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for cat, keywords in MATERIAL_CATEGORIES.items():
        if cat == "Other":
            continue
        scores[cat] = sum(1 for kw in keywords if kw in text_lower)
    if not scores:
        return "Other"
    best = max(scores, key=scores.get)
    return best if scores.get(best, 0) > 0 else "Other"


def detect_applications(text: str) -> list:
    text_lower = text.lower()
    return [
        app for app, keywords in APPLICATION_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ]


def extract_is_numbers(text: str) -> list:
    found = set()
    for m in re.finditer(r"IS\s*:?\s*(\d{3,6}(?:\s*\(Part\s*\d+\))?)", text, re.IGNORECASE):
        found.add(m.group(1).strip())
    return list(found)


def extract_year(text: str) -> Optional[str]:
    m = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", text)
    return m.group(0) if m else None


def clean_title(raw: str) -> str:
    raw = re.sub(r"^IS\s*:?\s*[\d\s:\(\)Part]+", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\(\s*(?:first|second|third|fourth|fifth)?\s*revis[io]+n\s*\)", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\(\s*(?:19|20)\d\d\s*\)", "", raw)
    # Strip trailing page number artifacts like "1.5 IS 21" or "1.7" or "2.3"
    raw = re.sub(r"\s+\d+\.\d+\s*(?:IS\s*\d+)?$", "", raw)
    raw = re.sub(r"\s+\d+\.\d+$", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.isupper():
        return raw.title()
    return raw


def format_standard_id(is_num: str, year: Optional[str]) -> str:
    """Format as 'IS 383: 1970' to match expected judge format."""
    is_num = is_num.strip()
    if year:
        return f"{is_num}: {year}"
    return is_num


def parse_summary_blocks(full_text: str) -> list:
    parts = re.split(r"SUMMARY\s+OF\b", full_text, flags=re.IGNORECASE)
    blocks = []
    for part in parts[1:]:
        part = part.strip()
        if part and len(part) > 50:
            blocks.append("SUMMARY OF\n" + part)
    return blocks


def parse_standard_block(block_text: str, page_num: int) -> Optional[dict]:
    lines = [l.strip() for l in block_text.split("\n") if l.strip()]
    if not lines:
        return None

    primary_is = None
    primary_is_raw = None
    title_parts = []
    year = None
    title_start_line = 0

    for i, line in enumerate(lines):
        m = re.search(
            r"(IS\s*:?\s*\d{3,6}(?:\s*\(Part\s*\d+\))?)\s*(?::\s*((?:19|20)\d\d))?\s*(.*)",
            line, re.IGNORECASE
        )
        if m:
            primary_is_raw = m.group(1).strip()
            # Normalize: "IS 383" format
            num_match = re.search(r"(\d{3,6}(?:\s*\(Part\s*\d+\))?)", primary_is_raw, re.IGNORECASE)
            if num_match:
                primary_is = f"IS {num_match.group(1).strip()}"
            else:
                primary_is = primary_is_raw
            year = m.group(2)
            title_raw = m.group(3).strip() if m.group(3) else ""
            if title_raw:
                title_parts.append(title_raw)
            title_start_line = i + 1
            break

    if not primary_is:
        return None

    # Continue reading title (may wrap to next lines)
    for j in range(title_start_line, min(title_start_line + 3, len(lines))):
        line = lines[j]
        if re.match(r"^\d+\.", line):
            break
        if re.match(r"^\(.*revis", line, re.IGNORECASE):
            break
        if re.match(r"^(scope|requirements|general|note|for\s+detailed)", line, re.IGNORECASE):
            break
        if len(line) < 5:
            break
        title_parts.append(line)

    title = clean_title(" ".join(title_parts))

    if not year:
        year = extract_year(block_text[:300])

    # Format ID with year for judge compatibility
    standard_id_full = format_standard_id(primary_is, year)

    # Extract scope
    scope = ""
    scope_match = re.search(
        r"(?:Scope|SCOPE)\s*[—\-–:]\s*(.*?)(?=\n\s*\d+\.|$)",
        block_text, re.DOTALL | re.IGNORECASE,
    )
    if scope_match:
        scope = re.sub(r"\s+", " ", scope_match.group(1)).strip()[:600]
    if not scope:
        for line in lines[title_start_line + 3:]:
            if len(line) > 60 and not re.match(r"^\d+\.", line):
                scope = line[:400]
                break

    # Related standards
    all_is = extract_is_numbers(block_text)
    related = [f"IS {n}" for n in all_is if f"IS {n}" != primary_is]

    # Category & applications — use title heavily
    search_text = f"{title} {title} {scope} {block_text[:500]}"
    category = detect_category(search_text)
    applications = detect_applications(search_text)

    keywords = []
    for cat_kws in MATERIAL_CATEGORIES.values():
        for kw in cat_kws:
            if kw in search_text.lower() and kw not in keywords:
                keywords.append(kw)
    for app_kws in APPLICATION_KEYWORDS.values():
        for kw in app_kws:
            if kw in search_text.lower() and kw not in keywords:
                keywords.append(kw)

    return {
        "standard_id": standard_id_full,   # e.g. "IS 383: 1970"
        "standard_id_short": primary_is,   # e.g. "IS 383"
        "title": title,
        "year": year,
        "material_category": category,
        "applications": applications,
        "scope": scope,
        "keywords": keywords[:25],
        "related_standards": related[:10],
        "full_text": block_text[:2000],
        "page": page_num,
    }


def parse_pdf(pdf_path: str, output_path: str) -> list:
    print(f"[Parser] Opening {pdf_path} ...")
    all_text = ""
    page_breaks = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"[Parser] Total pages: {total_pages}")
        for page_num, page in enumerate(pdf.pages, 1):
            if page_num % 50 == 0:
                print(f"[Parser] Reading page {page_num}/{total_pages} ...")
            text = page.extract_text()
            if text:
                page_breaks.append((len(all_text), page_num))
                all_text += text + "\n"

    print(f"[Parser] Total text extracted: {len(all_text):,} chars")
    blocks = parse_summary_blocks(all_text)
    print(f"[Parser] Found {len(blocks)} SUMMARY OF blocks")

    standards = []
    seen_ids = set()

    for block in blocks:
        pos = all_text.find(block[:50])
        page_num = 1
        for char_pos, pg in page_breaks:
            if char_pos <= pos:
                page_num = pg

        record = parse_standard_block(block, page_num)
        if record:
            sid = record["standard_id"]
            if sid not in seen_ids:
                seen_ids.add(sid)
                standards.append(record)

    print(f"[Parser] Extracted {len(standards)} unique standards.")
    print("\n[Parser] Sample (first 5):")
    for s in standards[:5]:
        print(f"  {s['standard_id']} | {s['title'][:60]} | {s['material_category']}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(standards, f, indent=2, ensure_ascii=False)

    print(f"\n[Parser] Saved to {output_path}")
    return standards


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--output", default="data/standards.json")
    args = ap.parse_args()
    parse_pdf(args.pdf, args.output)
