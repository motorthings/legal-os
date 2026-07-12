"""
Index help documentation into vector database.

Reads markdown files from backend/help_docs/, chunks them, generates embeddings,
and stores in help_documents + help_chunks tables.

Usage:
    cd backend
    python3 scripts/index_help_docs.py [--force]

Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, VOYAGE_API_KEY
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

DOCS_DIR = Path(__file__).resolve().parent.parent / "help_docs"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MIN_CHUNK_LENGTH = 50

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Directories to role access mapping
ROLE_ACCESS_MAP = {
    "user": ["user", "admin"],
    "system": ["user", "admin"],
}
DEFAULT_ROLES = ["user", "admin"]


def get_role_access(file_path: Path) -> list[str]:
    relative = file_path.relative_to(DOCS_DIR)
    parts = relative.parts
    if len(parts) > 1:
        return ROLE_ACCESS_MAP.get(parts[0], DEFAULT_ROLES)
    return DEFAULT_ROLES


def get_category(file_path: Path) -> str:
    relative = file_path.relative_to(DOCS_DIR)
    parts = relative.parts
    if len(parts) > 1:
        return parts[0]
    return "general"


def extract_title(content: str, file_path: Path) -> str:
    match = re.match(r"^#\s+(.+)", content)
    if match:
        return match.group(1).strip()
    return file_path.stem.replace("-", " ").title()


def split_into_sections(content: str) -> list[dict]:
    sections = []
    current_heading = ""
    current_text = []

    for line in content.split("\n"):
        heading_match = re.match(r"^(#{1,3})\s+(.+)", line)
        if heading_match:
            if current_text:
                text = "\n".join(current_text).strip()
                if text:
                    sections.append({"heading": current_heading, "text": text})
            current_heading = heading_match.group(2).strip()
            current_text = []
        else:
            current_text.append(line)

    if current_text:
        text = "\n".join(current_text).strip()
        if text:
            sections.append({"heading": current_heading, "text": text})

    return sections


def chunk_text(text: str, heading: str = "") -> list[dict]:
    if len(text) <= CHUNK_SIZE:
        if len(text) >= MIN_CHUNK_LENGTH:
            return [{"content": text, "heading": heading}]
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE

        if end < len(text):
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + CHUNK_SIZE // 2:
                end = para_break + 2
            else:
                sent_break = text.rfind(". ", start, end)
                if sent_break > start + CHUNK_SIZE // 2:
                    end = sent_break + 2

        chunk_text_str = text[start:end].strip()
        if len(chunk_text_str) >= MIN_CHUNK_LENGTH:
            chunks.append({"content": chunk_text_str, "heading": heading})

        start = end - CHUNK_OVERLAP
        if start >= len(text):
            break

    return chunks


def process_file(file_path: Path) -> tuple[dict, list[dict]]:
    content = file_path.read_text(encoding="utf-8")
    title = extract_title(content, file_path)
    category = get_category(file_path)
    role_access = get_role_access(file_path)
    relative_path = str(file_path.relative_to(DOCS_DIR))
    word_count = len(content.split())

    document = {
        "title": title,
        "file_path": relative_path,
        "category": category,
        "role_access": role_access,
        "content": content,
        "word_count": word_count,
    }

    sections = split_into_sections(content)
    chunks = []
    chunk_index = 0
    for section in sections:
        section_chunks = chunk_text(section["text"], section["heading"])
        for chunk in section_chunks:
            chunks.append({
                "content": chunk["content"],
                "heading_context": chunk["heading"],
                "role_access": role_access,
                "chunk_index": chunk_index,
                "metadata": {
                    "file_path": relative_path,
                    "category": category,
                },
            })
            chunk_index += 1

    return document, chunks


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate Voyage AI embeddings for text chunks."""
    if not VOYAGE_API_KEY:
        print("ERROR: VOYAGE_API_KEY not set")
        sys.exit(1)

    embeddings = []
    batch_size = 16

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = httpx.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {VOYAGE_API_KEY}"},
            json={
                "input": batch,
                "model": "voyage-3-lite",
                "input_type": "document",
            },
            timeout=60.0,
        )
        if resp.status_code != 200:
            print(f"Embedding error: {resp.status_code} {resp.text}")
            sys.exit(1)

        data = resp.json()
        embeddings.extend([d["embedding"] for d in data["data"]])
        print(f"  Batch {i // batch_size + 1}: {len(batch)} texts → {len(data['data'])} embeddings")

    return embeddings


def db_upsert(table: str, data: dict, match_col: str, match_val: str) -> str | None:
    """Upsert a record via PostgREST. Returns the id."""
    # Check if exists
    params = {match_col: f"eq.{match_val}", "select": "id"}
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={k: v for k, v in HEADERS.items() if k != "Prefer"},
        params=params,
        timeout=30.0,
    )

    if resp.status_code == 200 and resp.json():
        # Update
        doc_id = resp.json()[0]["id"]
        httpx.patch(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=HEADERS,
            params={"id": f"eq.{doc_id}"},
            json=data,
            timeout=30.0,
        )
        return doc_id
    else:
        # Insert
        resp = httpx.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=HEADERS,
            json=data,
            timeout=30.0,
        )
        if resp.status_code in (200, 201):
            result = resp.json()
            return result[0]["id"] if isinstance(result, list) else result["id"]
        raise RuntimeError(f"Insert failed ({resp.status_code}): {resp.text}")


def db_delete(table: str, col: str, val: str) -> None:
    httpx.delete(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        params={col: f"eq.{val}"},
        timeout=30.0,
    )


def db_insert(table: str, data: dict | list[dict]) -> list[dict]:
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        json=data,
        timeout=30.0,
    )
    if resp.status_code in (200, 201):
        return resp.json() if resp.status_code == 200 else []
    raise RuntimeError(f"Insert into {table} failed ({resp.status_code}): {resp.text}")


def main():
    parser = argparse.ArgumentParser(description="Index help documentation")
    parser.add_argument("--force", action="store_true", help="Force reindex all docs")
    args = parser.parse_args()

    if not DOCS_DIR.exists():
        print(f"Help docs directory not found: {DOCS_DIR}")
        sys.exit(1)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    md_files = sorted(DOCS_DIR.rglob("*.md"))
    md_files = [f for f in md_files if f.name != "README.md"]

    if not md_files:
        print("No markdown files found")
        sys.exit(1)

    print(f"Found {len(md_files)} markdown files")

    if args.force:
        print("Force reindex: clearing existing data...")
        # Delete all (service role bypasses RLS)
        for table in ["help_chunks", "help_documents"]:
            httpx.delete(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers=HEADERS,
                params={"id": "neq.00000000-0000-0000-0000-000000000000"},
                timeout=30.0,
            )

    all_docs = []
    all_chunks = []
    chunk_to_doc = []

    for fp in md_files:
        doc, chunks = process_file(fp)
        doc_idx = len(all_docs)
        all_docs.append(doc)
        for chunk in chunks:
            all_chunks.append(chunk)
            chunk_to_doc.append(doc_idx)
        print(f"  {doc['file_path']}: {len(chunks)} chunks, {doc['word_count']} words")

    if not all_chunks:
        print("No chunks generated")
        sys.exit(1)

    # Generate embeddings
    print(f"\nGenerating embeddings for {len(all_chunks)} chunks...")
    chunk_texts = [c["content"] for c in all_chunks]
    embeddings = generate_embeddings(chunk_texts)
    print(f"Generated {len(embeddings)} embeddings")

    # Upsert documents
    print("\nUpserting documents...")
    doc_ids = []
    for doc in all_docs:
        doc_id = db_upsert("help_documents", doc, "file_path", doc["file_path"])
        if doc_id:
            # Delete old chunks for this doc
            httpx.delete(
                f"{SUPABASE_URL}/rest/v1/help_chunks",
                headers=HEADERS,
                params={"document_id": f"eq.{doc_id}"},
                timeout=30.0,
            )
        doc_ids.append(doc_id)

    # Insert chunks
    print("Inserting chunks...")
    for i, chunk in enumerate(all_chunks):
        doc_idx = chunk_to_doc[i]
        doc_id = doc_ids[doc_idx]
        if not doc_id:
            continue

        chunk_record = {
            "document_id": doc_id,
            "content": chunk["content"],
            "embedding": embeddings[i],
            "chunk_index": chunk["chunk_index"],
            "heading_context": chunk["heading_context"],
            "role_access": chunk["role_access"],
            "metadata": chunk["metadata"],
        }
        db_insert("help_chunks", chunk_record)

    print(f"\nIndexing complete! Documents: {len(all_docs)}, Chunks: {len(all_chunks)}")


if __name__ == "__main__":
    main()
