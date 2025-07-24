import requests
import os
from slugify import slugify
import json
import hashlib

# Your ORCID ID
ORCID_ID = "0000-0002-7084-8774"
API_URL = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
OUTPUT_DIR = "content/publication"

# Map ORCID types to text form only
TYPE_MAP = {
    "journal-article": "Journal article",
    "conference-paper": "Conference paper",
    "book": "Book",
    "book-chapter": "Book section",
    "report": "Report",
    "thesis": "Thesis",
    "preprint": "Preprint",
    "patent": "Patent",
}

headers = {"Accept": "application/json"}

def compute_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def fetch_bibtex(doi, title, authors, year):
    if doi:
        doi_url = f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
        r = requests.get(doi_url)
        if r.status_code == 200:
            return r.text
    # fallback minimal BibTeX
    authors_str = " and ".join(authors) if authors else "Unknown"
    return f"@article{{{slugify(title)}_{year},\n  title={{ {title} }},\n  author={{ {authors_str} }},\n  year={{ {year} }}\n}}"

# Fetch ORCID works
response = requests.get(API_URL, headers=headers)
data = response.json()

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

for work in data.get("group", []):
    summary = work["work-summary"][0]

    # Title and type
    title = summary["title"]["title"]["value"]
    pub_type_text = TYPE_MAP.get(summary.get("type", "").lower(), "Journal article")

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

    # Fetch full details for contributors
    work_url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{summary['put-code']}"
    work_details = requests.get(work_url, headers=headers).json()

    authors = []
    editors = []

    contributors = (work_details.get("contributors") or {}).get("contributor", [])
    for c in contributors:
        name = c.get("credit-name", {}).get("value")
        role = (c.get("contributor-attributes") or {}).get("contributor-role", "").lower()

        if name:
            if role == "author" or role == "":
                authors.append(name)
            elif role == "editor":
                editors.append(name)

    # Journal or book title
    journal_data = work_details.get("journal-title")
    journal = journal_data.get("value") if journal_data else ""

    # Prepare publication folder
    folder_name = slugify(title)
    pub_folder = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(pub_folder, exist_ok=True)

    # Fetch BibTeX
    bibtex_content = fetch_bibtex(doi, title, authors, year)
    with open(os.path.join(pub_folder, "cite.bib"), "w") as f:
        f.write(bibtex_content)

    # Markdown front matter (text type)
    md_content = f"""---
title: "{title}"
date: {year}-{month}-{day}
doi: "{doi if doi else ''}"
publication_types: ["{pub_type_text}"]
authors: {json.dumps(authors)}
editors: {json.dumps(editors)}
publication: "{journal}"
abstract: ""
---
"""

    md_path = os.path.join(pub_folder, "index.md")

    # Skip rewriting unchanged files
    if os.path.exists(md_path):
        with open(md_path, "r") as existing_file:
            if compute_hash(existing_file.read()) == compute_hash(md_content):
                continue

    # Write new/updated index.md
    with open(md_path, "w") as f:
        f.write(md_content)

print("Publications updated from ORCID (authors/editors separated, text type).")