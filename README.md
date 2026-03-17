# tapas-data

Personal data repository that powers the RAG (Retrieval-Augmented Generation) pipeline behind [TapasOS](https://tapas-patra.github.io) — my AI-first developer portfolio.

Instead of manually managing data in a database, I maintain structured YAML files here. On every push, a GitHub Action syncs only the changed entries to Supabase (pgvector), where they're embedded and used by the AI chatbot to answer questions about me.

## How It Works

```
Edit YAML → Push to main → GitHub Action runs sync.py
                                    ↓
                          Computes content hash per entry
                                    ↓
                          Compares with hashes in Supabase
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
                New entry      Modified entry   Deleted entry
                    ↓               ↓               ↓
              Embed + Insert   Delete + Re-embed   Delete
                    ↓               ↓               ↓
                    └───────────────┼───────────────┘
                                    ↓
                          Unchanged entries → Skip
                          (zero embedding cost)
```

## Data Files

| File | Source | Description |
|------|--------|-------------|
| `profile.yaml` | `profile` | Introduction, current role, contact info |
| `skills.yaml` | `skills` | Technical skills by category |
| `experience.yaml` | `experience` | Work history and responsibilities |
| `projects.yaml` | `projects` | Project descriptions and tech stacks |
| `education.yaml` | `education` | Degrees and certifications |
| `achievements.yaml` | `achievements` | Awards and measurable impact |

## YAML Structure

Every file follows the same format:

```yaml
source: skills          # Unique key — maps to Supabase source column
label: Technical Skills  # Human-readable name

entries:
  - id: languages        # Stable ID — used for change tracking
    category: Languages
    text: >
      Python (Advanced) — my primary language for backend, automation, and AI.
      JavaScript/TypeScript — frontend, Node.js, Cloudflare Workers.
```

- `source` — identifies this file in the database
- `id` — stable identifier for each entry (never change this, or it creates a new entry)
- `text` — main content that gets embedded for RAG retrieval
- Other fields (`category`, `company`, `tech`, etc.) — stored as metadata

## Entry-Level Sync

The sync is **granular at the entry level**, not the file level:

| Change | What Happens | Embedding Cost |
|--------|-------------|----------------|
| Entry unchanged | Hash matches → **skip** | Zero |
| Entry text modified | Delete old → re-embed new | 1 embedding call |
| Entry removed from YAML | Delete from Supabase | Zero |
| New entry added | Embed and insert | 1 embedding call |

This means editing one bullet point in one entry only costs a single embedding API call, not a full re-index.

## Dashboard

A web-based control center is available at **[tapas-patra.github.io/tapas-data](https://tapas-patra.github.io/tapas-data/)** (GitHub Pages).

Features:
- View all sources and entries
- Edit, add, or delete entries (commits directly to this repo)
- Trigger incremental sync or full reindex
- Live workflow status with progress tracking

Requires a GitHub Personal Access Token with `repo` + `workflow` scopes.

## Manual Sync

### From GitHub Actions UI

Go to **Actions → Sync Data to RAG → Run workflow**:
- Default: incremental sync (only changed entries)
- Check "Wipe all data": full reindex (deletes everything, re-embeds all entries)

### Locally

```bash
export ADMIN_REINDEX_TOKEN="your-token"
export BACKEND_URL="https://portfolio-bot-5pwk.onrender.com"

pip install -r scripts/requirements.txt

# Incremental sync
python scripts/sync.py

# Full wipe + reindex
python scripts/sync.py --full
```

## Setup

### GitHub Secrets Required

| Secret | Value |
|--------|-------|
| `BACKEND_URL` | Backend API URL (e.g., `https://portfolio-bot-5pwk.onrender.com`) |
| `ADMIN_REINDEX_TOKEN` | Same token configured in the backend environment |

### Backend Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `POST /admin/sync` | Entry-level diff sync |
| `POST /admin/wipe` | Delete all documents (for full reindex) |

## Architecture

This repo is part of the TapasOS ecosystem:

```
tapas-data (this repo)          → Data source (YAML files)
    ↓ GitHub Action
portfolio-bot (backend)         → FastAPI + RAG pipeline
    ↓ Supabase pgvector
tapas-patra.github.io (frontend) → TapasOS + AI chatbot
```
