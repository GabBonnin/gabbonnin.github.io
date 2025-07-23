import requests
import os
import json
from slugify import slugify

# Your ORCID ID
ORCID_ID = "0000-0002-7084-8774"
API_URL = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
OUTPUT_DIR = "content/publication"
JSON_FILE = os.path.join(OUTPUT_DIR, "publications.json")

# Map ORCID types to Hugo Blox numeric and text types
TYPE_MAP = {
    "journal-article": ("2", "Journal article"),
    "conference-paper": ("1", "Conference paper"),
    "book": ("5", "Book"),
    "book-chapter": ("6", "Book section"),
    "report": ("4", "Report"),
    "thesis": ("7", "Thesis"),
    "preprint": ("3", "Preprint"),
    "patent": ("8", "Patent"),
}

def fetch_bibtex(doi, title, authors, year):
    """Fetch BibTeX from CrossRef; fallback to minimal if no DOI"""
    if doi:
        doi_url = f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
        r = requests.get(doi_url)
        if r.status_code == 200:
            return r.text
    authors_str = " and ".join(authors) if authors else "Unknown"
    return f"@article{{{slugify(title)}_{year},\n  title={{ {title} }},\n  author={{ {authors_str} }},\n  year={{ {year} }}\n}}"

# Fetch data from ORCID
headers = {"Accept": "application/json"}
response = requests.get(API_URL, headers=headers)
data = response.json()

publications = []

for work in data.get("group", []):
    summary = work["work-summary"][0]

    title = summary["title"]["title"]["value"]
    pub_type_code, pub_type_text = TYPE_MAP.get(summary.get("type", "").lower(), ("2", "Journal article"))

    pub_date = summary.get("publication-date") or {}
    year = (pub_date.get("year") or {}).get("value", "1900")

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

    # Prepare folder and BibTeX file
    folder_name = slugify(title)
    pub_folder = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(pub_folder, exist_ok=True)

    bibtex_content = fetch_bibtex(doi, title, authors, year)
    with open(os.path.join(pub_folder, "cite.bib"), "w") as f:
        f.write(bibtex_content)

    # Save metadata to list (for JSON)
    publications.append({
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "publication_type_name": pub_type_text,
        "bibtex": bibtex_content.replace("\n", "\\n"),
        "cite_path": f"/publication/{folder_name}/cite.bib"
    })

# Write JSON file for Hugo to use
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(JSON_FILE, "w") as f:
    json.dump(publications, f, indent=2)

print(f"Saved {len(publications)} publications to {JSON_FILE}")