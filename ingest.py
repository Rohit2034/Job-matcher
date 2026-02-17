import os
import re
from mongo_client import client
from embedder import embed
from skill_extractor import parse_skills
from text_utils import extract_text  

resume_col = client.get_or_create_collection("resumes")
job_col = client.get_or_create_collection("jobs")


def _extract_job_metadata(text: str) -> dict:
    """Extract location, employment type, and experience from job description."""
    metadata = {
        "location": "Unknown",
        "job_type": "Full-time",
        "min_exp": 0,
        "max_exp": 0
    }
    
    location_match = re.search(r"Location:\s*([^\n]+)", text, re.IGNORECASE)
    if location_match:
        metadata["location"] = location_match.group(1).strip()

    type_match = re.search(r"Employment Type:\s*([^\n]+)", text, re.IGNORECASE)
    if type_match:
        metadata["job_type"] = type_match.group(1).strip()
    
    exp_match = re.search(r"Experience Required:\s*(\d+)[–\-](\d+)", text, re.IGNORECASE)
    if exp_match:
        metadata["min_exp"] = int(exp_match.group(1))
        metadata["max_exp"] = int(exp_match.group(2))
    
    return metadata


def ingest_resumes(path="data/resumes"):
    print(f"Scanning resumes folder: {os.path.abspath(path)}")
    files = os.listdir(path)
    print("Files:", files)

    added = 0

    for file in files:
        if not file.lower().endswith((".txt", ".pdf", ".docx")):
            continue

        text = extract_text(os.path.join(path, file))

        if not text or len(text.strip()) < 50:
            print(f" Skipping {file}: no readable text (likely scanned PDF)")
            continue

        primary_skills, secondary_skills = parse_skills(text)

        resume_col.add(
            ids=[file],
            documents=[text],
            embeddings=[embed(text)],
            metadatas=[{
                "filename": file,
                "primary_skills": ", ".join(primary_skills),
                "secondary_skills": ", ".join(secondary_skills)
            }]
        )

        added += 1

    print(f"Resumes added: {added}")


def ingest_jobs(path="data/jobs"):
    print(f"Scanning jobs folder: {os.path.abspath(path)}")
    files = os.listdir(path)
    print("Files:", files)

    added = 0

    for file in files:
        if not file.lower().endswith((".txt", ".pdf", ".docx")):
            continue

        file_path = os.path.join(path, file)
        text = extract_text(file_path)

        if not text or len(text.strip()) < 50:
            print(f" Skipping {file}: no readable text")
            continue

        primary_skills, secondary_skills = parse_skills(text)
        job_meta = _extract_job_metadata(text)

        job_col.add(
            ids=[file],
            documents=[text],
            embeddings=[embed(text)],
            metadatas=[{
                "job_id": file,
                "skills": ", ".join(primary_skills + secondary_skills),
                "location": job_meta["location"],
                "job_type": job_meta["job_type"],
                "min_exp": job_meta["min_exp"],
                "max_exp": job_meta["max_exp"],
                "role": "Backend"
            }]
        )

        added += 1

    print(f"Jobs added: {added}")

