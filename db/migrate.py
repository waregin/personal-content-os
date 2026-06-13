"""Run DDL to create (or verify) a complete user schema in content_os.

Usage:
    uv run python db/migrate.py [schema_name]

schema_name defaults to user_waregin. Safe to run multiple times.
"""

import argparse
import sys

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS {schema}.source_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        TEXT NOT NULL,
    source_format   TEXT NOT NULL,
    source_url      TEXT,
    doc_date        DATE,
    imported_at     TIMESTAMPTZ DEFAULT now(),
    corpus_type     TEXT NOT NULL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS {schema}.chunks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_id       UUID NOT NULL REFERENCES {schema}.source_documents(id) ON DELETE CASCADE,
    chunk_index         INTEGER NOT NULL,
    chunk_text          TEXT NOT NULL,
    embedding           vector(1536),
    source_type         TEXT NOT NULL,
    source_file         TEXT,
    source_date         DATE,
    ingested_at         TIMESTAMPTZ DEFAULT now(),
    corpus_type         TEXT NOT NULL,
    origin              TEXT NOT NULL,
    epistemic_status    TEXT,
    polish_level        TEXT,
    completion_status   TEXT,
    voice_eligible      BOOLEAN DEFAULT TRUE,
    position_eligible   BOOLEAN DEFAULT TRUE,
    send_to_api         TEXT DEFAULT 'ask',
    speaker             TEXT,
    context_only        BOOLEAN DEFAULT FALSE,
    topic_tags          TEXT[],
    human_reviewed      BOOLEAN DEFAULT FALSE,
    review_notes        TEXT
);

CREATE TABLE IF NOT EXISTS {schema}.voice_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label           TEXT,
    version         INTEGER DEFAULT 1,
    profile_data    JSONB NOT NULL,
    corpus_size     INTEGER,
    corpus_hash     TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS {schema}.drafts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id           UUID REFERENCES {schema}.drafts(id),
    title               TEXT,
    version             INTEGER DEFAULT 0,
    content             TEXT,
    status              TEXT DEFAULT 'idea',
    priority            TEXT DEFAULT 'normal',
    origin              TEXT,
    platform_target     TEXT[],
    published_url       TEXT,
    published_at        DATE,
    inspiring_chunks    UUID[],
    surfaced_from       TEXT,
    human_approved      BOOLEAN DEFAULT FALSE,
    critique_notes      TEXT,
    voice_profile_id    UUID REFERENCES {schema}.voice_profiles(id),
    topic_tags          TEXT[],
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);
"""

# Indexes use IF NOT EXISTS (Postgres 9.5+). The index name encodes both schema
# and table so multiple schemas don't collide.
INDEXES = [
    "CREATE INDEX IF NOT EXISTS {s}_chunks_embedding_idx     ON {schema}.chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    "CREATE INDEX IF NOT EXISTS {s}_chunks_source_doc_idx    ON {schema}.chunks (source_doc_id)",
    "CREATE INDEX IF NOT EXISTS {s}_chunks_corpus_type_idx   ON {schema}.chunks (corpus_type)",
    "CREATE INDEX IF NOT EXISTS {s}_chunks_epistemic_idx     ON {schema}.chunks (epistemic_status)",
    "CREATE INDEX IF NOT EXISTS {s}_chunks_send_api_idx      ON {schema}.chunks (send_to_api)",
    "CREATE INDEX IF NOT EXISTS {s}_chunks_speaker_idx       ON {schema}.chunks (speaker)",
    "CREATE INDEX IF NOT EXISTS {s}_chunks_topic_tags_idx    ON {schema}.chunks USING GIN (topic_tags)",
    "CREATE INDEX IF NOT EXISTS {s}_voice_version_idx        ON {schema}.voice_profiles (version)",
    "CREATE INDEX IF NOT EXISTS {s}_voice_created_idx        ON {schema}.voice_profiles (created_at)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_parent_idx        ON {schema}.drafts (parent_id)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_status_idx        ON {schema}.drafts (status)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_version_idx       ON {schema}.drafts (version)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_priority_idx      ON {schema}.drafts (priority)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_topic_tags_idx    ON {schema}.drafts USING GIN (topic_tags)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_platform_idx      ON {schema}.drafts USING GIN (platform_target)",
    "CREATE INDEX IF NOT EXISTS {s}_drafts_inspiring_idx     ON {schema}.drafts USING GIN (inspiring_chunks)",
]


def migrate(schema: str) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            print(f"Creating schema {schema!r} if it does not exist...")
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

            print("Running table DDL...")
            cur.execute(DDL.format(schema=schema))

            print("Creating indexes...")
            for stmt in INDEXES:
                cur.execute(stmt.format(schema=schema, s=schema))

        conn.commit()
        print(f"Migration complete for schema {schema!r}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate a user schema in content_os.")
    parser.add_argument(
        "schema",
        nargs="?",
        default="user_waregin",
        help="Postgres schema name (default: user_waregin)",
    )
    args = parser.parse_args()
    migrate(args.schema)
