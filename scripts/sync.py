"""Sync YAML data files to portfolio-bot RAG backend.

Parses all .yaml files, computes content hashes per entry,
and sends only changed/new/deleted entries to the backend.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import requests
import yaml

BACKEND_URL = os.getenv("BACKEND_URL", "https://portfolio-bot-5pwk.onrender.com")
ADMIN_TOKEN = os.getenv("ADMIN_REINDEX_TOKEN", "")
DATA_DIR = Path(__file__).resolve().parent.parent


def load_yaml_files() -> list[dict]:
    """Load all .yaml files from the data directory."""
    sources = []
    for f in sorted(DATA_DIR.glob("*.yaml")):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if not data or "source" not in data or "entries" not in data:
            print(f"  Skipping {f.name}: missing 'source' or 'entries'")
            continue
        sources.append(data)
        print(f"  Loaded {f.name}: {len(data['entries'])} entries")
    return sources


def flatten_entry(entry: dict) -> str:
    """Flatten a YAML entry into natural text for embedding."""
    parts = []

    # Add structured fields as context
    for key in ("title", "name", "company", "role", "degree", "institution", "category"):
        if key in entry:
            val = entry[key]
            if isinstance(val, list):
                val = ", ".join(val)
            parts.append(str(val))

    if "period" in entry:
        parts.append(f"({entry['period']})")
    if "location" in entry:
        parts.append(f"Location: {entry['location']}")
    if "tech" in entry:
        tech = entry["tech"]
        if isinstance(tech, list):
            tech = ", ".join(tech)
        parts.append(f"Tech: {tech}")

    # Main text content
    if "text" in entry:
        parts.append(entry["text"].strip())

    if "highlights" in entry:
        for h in entry["highlights"]:
            parts.append(f"- {h}")

    return "\n".join(parts)


def content_hash(text: str) -> str:
    """SHA256 hash of flattened entry text."""
    return hashlib.sha256(text.encode()).hexdigest()


def build_payload(sources: list[dict]) -> dict:
    """Build the sync API payload with entries and their hashes."""
    payload_sources = []

    for source_data in sources:
        entries = []
        for entry in source_data["entries"]:
            entry_id = entry.get("id")
            if not entry_id:
                print(f"  WARNING: Entry without 'id' in {source_data['source']}, skipping")
                continue
            flat_text = flatten_entry(entry)
            h = content_hash(flat_text)

            # Build metadata from structured fields (exclude text and id)
            metadata = {}
            for key, val in entry.items():
                if key not in ("id", "text", "highlights"):
                    metadata[key] = val

            entries.append({
                "entry_id": entry_id,
                "content_hash": h,
                "text": flat_text,
                "metadata": metadata,
            })

        payload_sources.append({
            "source": source_data["source"],
            "entries": entries,
        })

    return {"sources": payload_sources}


def sync(payload: dict) -> dict:
    """POST the sync payload to the backend."""
    url = f"{BACKEND_URL}/admin/sync"
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json",
    }
    print(f"\n  Syncing to {url}...")
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()


def main():
    print("tapas-data sync")
    print("=" * 40)

    if not ADMIN_TOKEN:
        print("ERROR: ADMIN_REINDEX_TOKEN not set")
        sys.exit(1)

    print(f"\nLoading YAML files from {DATA_DIR}...")
    sources = load_yaml_files()

    if not sources:
        print("No valid YAML files found.")
        sys.exit(1)

    total_entries = sum(len(s["entries"]) for s in sources)
    print(f"\nTotal: {len(sources)} sources, {total_entries} entries")

    payload = build_payload(sources)
    result = sync(payload)

    print(f"\nSync result:")
    print(f"  Inserted: {result.get('inserted', 0)}")
    print(f"  Updated:  {result.get('updated', 0)}")
    print(f"  Deleted:  {result.get('deleted', 0)}")
    print(f"  Skipped:  {result.get('skipped', 0)}")
    print(f"  Embeddings used: {result.get('embeddings_used', 0)}")


if __name__ == "__main__":
    main()
