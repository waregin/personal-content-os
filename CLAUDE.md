# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Project Is

`personal-content-os` is a three-module AI-powered personal content system:

- **Module 1 — The Corpus**: Ingests personal writings, conversations, and reference material into a pgvector database. Chunks, embeds, classifies, and stores with rich metadata.
- **Module 2 — The Idea Engine**: Analyzes the corpus to surface content ideas the owner is uniquely positioned to write. Runs on demand or schedule.
- **Module 3 — The Drafting Engine**: Takes an approved idea, retrieves relevant corpus chunks as voice/style reference, and produces a first draft with inline critique annotations and a final critique pass.

Long-term goal: personal use first, then a high-ticket done-for-you service, eventually a SaaS product.

## Tech Stack

- **Runtime / packaging**: Python with `uv` (never use pip directly)
- **Database**: PostgreSQL with pgvector extension
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensions — this number must match the vector column definition exactly)
- **LLM calls**: Anthropic API (Claude) for classification, drafting, and critique; OpenAI API as fallback
- **Linting / formatting**: Ruff
- **UI**: Streamlit or Marimo (TBD — chat interface as primary, dashboard as secondary)
- **Automation**: n8n for workflow orchestration (external)
- **Orchestration**: LangChain / LangGraph for agent patterns

## Commands

```bash
uv sync                       # install dependencies
uv run ruff check .           # lint
uv run ruff format .          # format
uv run pytest                 # run tests
uv run streamlit run app.py   # run app (if Streamlit)
uv run marimo run app.py      # run app (if Marimo)
```

## Database Architecture — Read This Before Touching the DB

### Schema isolation
Every user/client gets their own Postgres schema. **Never put application data in the public schema.**
- Owner schema: `user_owner` (replace with actual username)
- Future clients: `user_alice`, `user_bob`, etc.
- Always prefix table references with the schema name, or set `search_path` explicitly at the start of a session.
- Schemas created manually via `sudo -u postgres psql` must be granted to `waregin` explicitly: `GRANT ALL ON SCHEMA schema_name TO waregin;` — the migration script handles this automatically when creating new client schemas via db/migrate.py.

### Tables (all within user schema)
- `source_documents` — one row per ingested file
- `chunks` — one row per chunk, with embedding vector and all metadata
- `voice_profiles` — versioned snapshots of the owner's voice model
- `drafts` — unified ideas + drafts table (version=0 is an idea, version≥1 is a draft)

### Critical rules — never violate these
1. **views-discarded chunks are ingest-only**: never retrieve them as positions to argue from. Filter `WHERE epistemic_status != 'views-discarded'` on all position retrieval queries.
2. **send-to-api flag must be respected**: before passing any chunk text to an external API, check its `send_to_api` flag. If `false`, never send. If `ask`, pause and surface for human review. Never bypass this check.
3. **Speaker separation**: in conversation sources, only owner turns have `voice_eligible=true` and `position_eligible=true`. Other speakers are `context_only=true`. Never use context-only chunks for voice modeling or position extraction.
4. **Draft versioning**: never update a draft's content in place. Always insert a new row with `parent_id` pointing to the previous version and `version` incremented.
5. **Schema changes**: always ask before modifying any table definition. Schema migrations affect all existing data.
6. **Never delete corpus data** without explicit confirmation. Deletions are irreversible.

## Secrets

- Secrets go in `.env` (gitignored — never commit)
- Required keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`
- `DATABASE_URL` format: `postgresql://content_os_user:password@localhost/content_os`

## Project Structure (evolving — update as it grows)
personal-content-os/
├── ingestion/          # Module 1: parsers, chunkers, embedder, classifier
├── idea_engine/        # Module 2: gap analysis, idea ranking
├── drafting/           # Module 3: retrieval, drafting, critique
├── db/                 # Schema migrations, db connection utilities
├── ui/                 # Chat interface and dashboard
├── tests/
├── .env                # gitignored
├── pyproject.toml
└── CLAUDE.md

## What to Always Ask Before Doing

- Any change to table definitions (ALTER TABLE, DROP COLUMN, etc.)
- Any DELETE or TRUNCATE on corpus tables
- Any operation that would send flagged chunks to an external API
- Adding new dependencies (confirm with owner before `uv add`)
- Changing the embedding model or vector dimensions (breaks existing embeddings)