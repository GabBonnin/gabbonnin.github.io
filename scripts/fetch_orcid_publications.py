import requests
import os
from slugify import slugify
import hashlib
import json

# Your ORCID ID
ORCID_ID = "0000-0002-7084-8774"
API_URL = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
OUTPUT_DIR = "content/publication"

# Map ORCID types to Hugo Blox publication_types
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

headers = {"Accept": "application/json"}
response = requests.get(API_URL, headers=headers)
data = response.json()

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def compute_hash(content: str) -> str:
    """Generate a hash for the markdown content to detect changes."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()

updated_count = 0

for work in data.get("group", []):
    summary = work["work-summary"][0]

    # Basic metadata
    title = summary["title"]["title"]["value"]
    pub_type = TYPE_MAP.get(summary.get("type", "").lower(), "2")
    pub_date = summary.get("publication-date", {})
    year = pub_date.get("year", {}).get("value", "1900")
    month = pub_date.get("month", {}).get("value", "01")
    day = pub_date.get("day", {}).get("value", "01")

    # DOI
    doi = None
    for ext_id in summary.get("external-ids", {}).get("external-id", []):
        if ext_id.get("external-id-type") == "doi":
            doi = ext_id.get("external-id-value")

    # Fetch full details for authors & journal
    work_url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{summary['put-code']}"
    work_details = requests.get(work_url, headers=headers).json()

    authors = []
    contributors = work_details.get("contributors", {}).get("contributor", [])
    for c in contributors:
        name = c.get("credit-name", {}).get("value")
        if name:
            authors.append(name)

    journal = work_details.get("journal-title", {}).get("value", "")

    # Generate markdown
    md_content = f"""---
title: "{title}"
date: {year}-{month}-{day}
doi: "{doi if doi else ''}"
publication_types: ["{pub_type}"]
authors: {json.dumps(authors)}
publication: "{journal}"
abstract: ""
---
"""

    # File path
    filename = slugify(title)
    filepath = f"{OUTPUT_DIR}/{filename}.md"

    # Check if file exists and is unchanged
    if os.path.exists(filepath):
        with open(filepath, "r") as existing_file:
            existing_hash = compute_hash(existing_file.read())
            new_hash = compute_hash(md_content)
            if existing_hash == new_hash:
                continue  # No changes, skip writing

    # Write new/updated file
    with open(filepath, "w") as f:
        f.write(md_content)
    updated_count += 1

print(f"Updated or added {updated_count} publications (others unchanged).")