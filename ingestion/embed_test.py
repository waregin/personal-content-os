"""Proof-of-concept: embed one string and write it to user_waregin.chunks.

Usage:
    uv run python ingestion/embed_test.py
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SCHEMA = "user_waregin"
TEST_TEXT = "This is a test chunk for the Content OS ingestion pipeline."

openai_api_key = os.environ.get("OPENAI_API_KEY")
database_url = os.environ.get("DATABASE_URL")

if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
    sys.exit(1)
if not database_url:
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)

client = OpenAI(api_key=openai_api_key)

print("Calling OpenAI embeddings API...")
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=TEST_TEXT,
)
embedding = response.data[0].embedding  # list of 1536 floats

conn = psycopg2.connect(database_url)
try:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.source_documents (filename, source_format, corpus_type)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            ("test", "test", "personal"),
        )
        source_doc_id = cur.fetchone()[0]

        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.chunks (
                source_doc_id, chunk_index, chunk_text, embedding,
                source_type, corpus_type, origin,
                send_to_api, voice_eligible, position_eligible
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                source_doc_id,
                0,
                TEST_TEXT,
                embedding,
                "test",
                "personal",
                "human-written",
                "ask",
                True,
                True,
            ),
        )
        chunk_id = cur.fetchone()[0]

    conn.commit()
    print(f"Inserted chunk: {chunk_id}")
finally:
    conn.close()
