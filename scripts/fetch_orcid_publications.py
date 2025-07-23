import requests
import os
from slugify import slugify
import hashlib
import json

# Your ORCID ID
ORCID_ID = "0000-0002-7084-8774"
API_URL = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
OUTPUT_DIR = "content/publication"

# Map ORCID types to Hugo Blox numeric publication_types
TYPE_MAP = {
    "journal-article": "2",
    "conference-paper": "1",
    "book": "5",
    "book-chapter": "6",
    "report": "4",
    "thesis": "7",
    "preprint": "3",
    "patent": "8",
}

# Human-readable type names
TYPE_TEXT_MAP = {
    "1": "Conference paper",
    "2": "Journal article",
    "3": "Preprint",
    "4": "Report",
    "5": "Book",
    "6": "Book section",
    "7": "Thesis",
    "8": "Patent",
}

headers = {"Accept": "application/json"}

def compute_hash(content: str) -> str:
    """Generate hash to detect file changes"""
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def fetch_bibtex(doi: str, title: str, authors: list, year: str) -> str:
    """Fetch BibTeX from CrossRef; fallback to minimal BibTeX if no DOI"""
    if doi:
        doi_url = f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
        r = requests.get(doi_url)
        if r.status_code == 200:
            return r.text
    # Minimal fallback BibTeX
    authors_str = " and ".join(authors) if authors else "Unknown"
    return f"@article{{{slugify(title)}_{year},\n  title={{ {title} }},\n  author={{ {authors_str} }},\n  year={{ {year} }}\n}}"

# Fetch works from ORCID
response = requests.get(API_URL, headers=headers)
data = response.json()

updated_count = 0

for work in data.get("group", []):
    summary = work["work-summary"][0]

    # Title and type
    title = summary["title"]["title"]["value"]
    pub_type_code = TYPE_MAP.get(summary.get("type", "").lower(), "2")
    pub_type_text = TYPE_TEXT_MAP[pub_type_code]

    # Safe date handling
    pub_date = summary.get("publication-date") or {}
    year = (pub_date.get("year") or {}).get("value", "1900")
    month = (pub_date.get("month") or {}).get("value", "01")
    day = (pub_date.get("day") or {}).get("value", "01")

    # DOI
    doi = None
    for ext_id in summary.get("external-ids", {}).get("external-id", []):
        if ext_id.get("external-id-type") == "doi":
            doi = ext_id.get("external-id-value")

    # Fetch full details for authors & journal
    work_url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{summary['put-code']}"
    work_details = requests.get(work_url, headers=headers).json()

    authors = []
    contributors = (work_details.get("contributors") or {}).get("contributor", [])
    for c in contributors:
        name = c.get("credit-name", {}).get("value")
        if name:
            authors.append(name)

    journal_data = work_details.get("journal-title")
    journal = journal_data.get("value") if journal_data else ""

    # Prepare directory structure (folder per publication)
    folder_name = slugify(title)
    pub_folder = os.path.join(OUTPUT_DIR, folder_name)
    if not os.path.exists(pub_folder):
        os.makedirs(pub_folder)

    # Fetch BibTeX
    bibtex_content = fetch_bibtex(doi, title, authors, year)
    bibtex_escaped = bibtex_content.replace('"', '\\"').replace('\n', '\\n')

    # Markdown content (index.md)
    md_content = f"""---
title: "{title}"
date: {year}-{month}-{day}
doi: "{doi if doi else ''}"
publication_types: ["{pub_type_code}"]
publication_type_name: "{pub_type_text}"
authors: {json.dumps(authors)}
publication: "{journal}"
abstract: ""
bibtex: "{bibtex_escaped}"
---
"""

    md_path = os.path.join(pub_folder, "index.md")

    # Skip unchanged files
    if os.path.exists(md_path):
        with open(md_path, "r") as existing_file:
            if compute_hash(existing_file.read()) == compute_hash(md_content):
                continue

    # Write index.md
    with open(md_path, "w") as f:
        f.write(md_content)

    # Write cite.bib file (download option)
    with open(os.path.join(pub_folder, "cite.bib"), "w") as f:
        f.write(bibtex_content)

    updated_count += 1

print(f"Updated or added {updated_count} publications (others unchanged).")