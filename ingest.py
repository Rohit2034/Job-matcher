import os
import re
from mongo_client import client
from embedder import embed
from skill_extractor import parse_skills
from text_utils import extract_text

resume_col = client.get_collection("resumes")
job_col = client.get_collection("jobs")



def _extract_job_metadata(text: str) -> dict:
    """Extract location, employment type, and experience from job description."""
    metadata = {
        "location": "Unknown",
        "job_type": "Full-time",
        "min_exp": 0,
        "max_exp": 0
    }
    
    # Extract Location
    location_match = re.search(r"Location:\s*([^\n]+)", text, re.IGNORECASE)
    if location_match:
        metadata["location"] = location_match.group(1).strip()
    
    # Extract Employment Type
    type_match = re.search(r"Employment Type:\s*([^\n]+)", text, re.IGNORECASE)
    if type_match:
        metadata["job_type"] = type_match.group(1).strip()
    
    # Extract Experience (e.g., "3–7 years" or "3-7 years")
    exp_match = re.search(r"Experience Required:\s*(\d+)[–\-](\d+)", text, re.IGNORECASE)
    if exp_match:
        metadata["min_exp"] = int(exp_match.group(1))
        metadata["max_exp"] = int(exp_match.group(2))
    
    return metadata


def ingest_resumes(path="data/resumes", batch_size=100):
    print(f"Scanning resumes folder: {os.path.abspath(path)}")
    files = os.listdir(path)
    print(f"Files found: {len(files)}")

    added = 0
    allowed = {".pdf", ".docx", ".txt"}
    batch = []

    for file in files:
        _, ext = os.path.splitext(file)
        if ext.lower() not in allowed:
            continue

        text = extract_text(os.path.join(path, file))

        if not text or len(text.strip()) < 50:
            print(f"⚠️ Skipping {file}: no readable text (likely scanned or empty)")
            continue

        primary_skills, secondary_skills = parse_skills(text)
        batch.append({
            "id": file,
            "document": text,
            "embedding": embed(text),
            "metadata": {
                "filename": file,
                "primary_skills": ", ".join(primary_skills),
                "secondary_skills": ", ".join(secondary_skills)
            }
        })

        # Batch insert when reaching batch_size
        if len(batch) >= batch_size:
            resume_col.add(
                ids=[b["id"] for b in batch],
                documents=[b["document"] for b in batch],
                embeddings=[b["embedding"] for b in batch],
                metadatas=[b["metadata"] for b in batch]
            )
            added += len(batch)
            print(f"✅ Processed {added} resumes...")
            batch = []

    # Insert remaining batch
    if batch:
        resume_col.add(
            ids=[b["id"] for b in batch],
            documents=[b["document"] for b in batch],
            embeddings=[b["embedding"] for b in batch],
            metadatas=[b["metadata"] for b in batch]
        )
        added += len(batch)

    print(f"✅ Total resumes added: {added}")


def ingest_jobs(path="data/jobs", batch_size=50):
    print(f"Scanning jobs folder: {os.path.abspath(path)}")
    files = os.listdir(path)
    print(f"Files found: {len(files)}")

    added = 0
    allowed = {".pdf", ".docx", ".txt"}
    batch = []

    for file in files:
        _, ext = os.path.splitext(file)
        if ext.lower() not in allowed:
            continue

        text = extract_text(os.path.join(path, file))

        if not text or len(text.strip()) < 50:
            print(f"⚠️ Skipping {file}: no readable text (likely scanned or empty)")
            continue

        primary_skills, secondary_skills = parse_skills(text)
        job_meta = _extract_job_metadata(text)
        batch.append({
            "id": file,
            "document": text,
            "embedding": embed(text),
            "metadata": {
                "job_id": file,
                "skills": ", ".join(primary_skills + secondary_skills),
                "location": job_meta["location"],
                "job_type": job_meta["job_type"],
                "min_exp": job_meta["min_exp"],
                "max_exp": job_meta["max_exp"],
                "role": "Backend"
            }
        })

        # Batch insert when reaching batch_size
        if len(batch) >= batch_size:
            job_col.add(
                ids=[b["id"] for b in batch],
                documents=[b["document"] for b in batch],
                embeddings=[b["embedding"] for b in batch],
                metadatas=[b["metadata"] for b in batch]
            )
            added += len(batch)
            print(f"✅ Processed {added} jobs...")
            batch = []

    # Insert remaining batch
    if batch:
        job_col.add(
            ids=[b["id"] for b in batch],
            documents=[b["document"] for b in batch],
            embeddings=[b["embedding"] for b in batch],
            metadatas=[b["metadata"] for b in batch]
        )
        added += len(batch)

    print(f"✅ Total jobs added: {added}")


if __name__ == "__main__":
    ingest_resumes()
    ingest_jobs()
