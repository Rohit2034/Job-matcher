import numpy as np
from mongo_client import client
from embedder import embed

resume_col = client.get_collection("resumes")
job_col = client.get_collection("jobs")


# ----------------------------
# Utility: Cosine Similarity
# ----------------------------
def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    denom = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    if denom == 0:
        return 0.0

    return float(np.dot(vec1, vec2) / denom)


# ----------------------------
# Skill Parsing
# ----------------------------
def _parse_skills(skills_str: str) -> set:
    if not skills_str:
        return set()
    return {s.strip().lower() for s in skills_str.split(",")}


def _skill_matches(job_skill: str, resume_skill: str) -> bool:
    job_skill = job_skill.lower()
    resume_skill = resume_skill.lower()

    if job_skill == resume_skill:
        return True

    if job_skill in resume_skill or resume_skill in job_skill:
        return True

    if job_skill == "sql" and any(
        db in resume_skill for db in ["mysql", "postgresql", "sqlite", "oracle", "mssql"]
    ):
        return True

    if "api" in job_skill and "api" in resume_skill:
        return True

    return False


# ----------------------------
# Skill Score Calculation
# ----------------------------
def _calculate_skill_match_score(job_meta, resume_meta):
    job_skills = _parse_skills(job_meta.get("skills", ""))
    primary = _parse_skills(resume_meta.get("primary_skills", ""))
    secondary = _parse_skills(resume_meta.get("secondary_skills", ""))

    if not job_skills:
        return 0.0

    primary_matches = sum(
        1 for j in job_skills
        if any(_skill_matches(j, r) for r in primary)
    )

    secondary_matches = sum(
        1 for j in job_skills
        if any(_skill_matches(j, r) for r in secondary)
    )

    skill_score = (primary_matches * 20) + (secondary_matches * 10)
    max_score = len(job_skills) * 20

    return (skill_score / max_score) * 100 if max_score else 0.0


# ----------------------------
# MAIN MATCH FUNCTION
# ----------------------------
def match_job(job_id: str, top_k: int = 5):

    job = job_col.get(ids=[job_id])

    if not job["documents"] or job["documents"][0] is None:
        raise ValueError(f"Job {job_id} not found")

    job_text = job["documents"][0]
    job_meta = job["metadatas"][0]

    # Generate embedding for job
    job_embedding = embed(job_text)

    all_resumes = list(resume_col._col.find({"embedding": {"$exists": True}}))

    results = []

    for resume in all_resumes:
        resume_meta = resume.get("metadata", {})
        resume_embedding = resume.get("embedding", [])

        if not resume_embedding:
            continue

        # ---- Skill Score ----
        skill_score = _calculate_skill_match_score(job_meta, resume_meta)

        # ---- Embedding Score ----
        emb_score = cosine_similarity(job_embedding, resume_embedding) * 100

        # ---- Final  Score ----
        final_score = (0.6 * emb_score) + (0.4 * skill_score)

        results.append({
            "id": resume["_id"],
            "filename": resume_meta.get("filename", "Unknown"),
            "final_score": round(final_score, 2),
            "skill_score": round(skill_score, 2),
            "embedding_score": round(emb_score, 2),
            "primary": resume_meta.get("primary_skills", ""),
            "secondary": resume_meta.get("secondary_skills", "")
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    top_results = results[:top_k]

    print(f"\n🔍 Top {top_k} Matches for Job: {job_id}\n")
    print(f"Required Skills: {job_meta.get('skills', '')}\n")

    for i, r in enumerate(top_results):
        print(f"{i+1}. {r['filename']}")
        print(f"   Final Score: {r['final_score']}/100")
        print(f"   Skill Score: {r['skill_score']}")
        print(f"   Embedding Score: {r['embedding_score']}")
        print(f"   Primary Skills: {r['primary']}")
        print(f"   Secondary Skills: {r['secondary']}")
        print("-" * 50)



if __name__ == "__main__":
    match_job("job3.txt")
