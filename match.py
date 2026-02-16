from mongo_client import client

resume_col = client.get_collection("resumes")
job_col = client.get_collection("jobs")


def _parse_skills(skills_str: str) -> set:
    """Parse comma-separated skills into a set of lowercase normalized skills."""
    if not skills_str:
        return set()
    return {s.strip().lower() for s in skills_str.split(",")}


def _skill_matches(job_skill: str, resume_skill: str) -> bool:
    """
    Check if a resume skill matches a job skill with fuzzy matching.
    Handles variations like React/React.js, Python/python, SQL/MySQL, etc.
    """
    job_skill_lower = job_skill.strip().lower()
    resume_skill_lower = resume_skill.strip().lower()
    
    # Exact match
    if job_skill_lower == resume_skill_lower:
        return True
    
    # Substring match (e.g., "react" in "react.js" or vice versa)
    if job_skill_lower in resume_skill_lower or resume_skill_lower in job_skill_lower:
        return True
    
    # Special case: SQL matches any database (PostgreSQL, MySQL, SQLite, etc.)
    if job_skill_lower == "sql" and any(db in resume_skill_lower for db in ["mysql", "postgresql", "sqlite", "oracle", "mssql"]):
        return True
    
    # Special case: REST APIs matches API-related skills
    if "api" in job_skill_lower and "api" in resume_skill_lower:
        return True
    
    return False


def _calculate_skill_match_score(job_meta: dict, resume_primary: str, resume_secondary: str) -> float:
    """
    Calculate matching score out of 100 based on:
    - Skill overlap: primary matches = 20 pts, secondary matches = 10 pts
    - Location match: +15 pts bonus if location/job type matches
    
    Uses fuzzy matching to handle skill name variations (React vs React.js, SQL vs MySQL, etc).
    Score is normalized to a scale of 0-100.
    """
    job_skills_str = job_meta.get("skills", "")
    job_location = job_meta.get("location", "").lower()
    job_type = job_meta.get("job_type", "").lower()
    
    job_skills = _parse_skills(job_skills_str)
    resume_primary_skills = _parse_skills(resume_primary)
    resume_secondary_skills = _parse_skills(resume_secondary)

    if not job_skills:
        return 0.0

    # Count primary skill matches with fuzzy matching
    primary_matches = sum(
        1 for job_skill in job_skills
        if any(_skill_matches(job_skill, res_skill) for res_skill in resume_primary_skills)
    )
    
    # Count secondary skill matches with fuzzy matching
    secondary_matches = sum(
        1 for job_skill in job_skills
        if any(_skill_matches(job_skill, res_skill) for res_skill in resume_secondary_skills)
    )
    
    skill_score = (primary_matches * 20) + (secondary_matches * 10)
    
    # Max possible skill score = all job skills matched as primary
    max_skill_score = len(job_skills) * 20
    
    # Location/job type bonus
    location_bonus = 0.0
    if job_location or job_type:
        # Keywords for different job types
        remote_keywords = {"remote", "work from home", "wfh", "distributed"}
        hybrid_keywords = {"hybrid", "flexible"}
        onsite_keywords = {"bangalore", "onsite", "office", "in-office"}
        
        location_lower = job_location.lower() if job_location else ""
        type_lower = job_type.lower() if job_type else ""
        location_type_combined = f"{location_lower} {type_lower}".lower()
        
        # Check if job location/type matches common categories
        if any(kw in location_type_combined for kw in remote_keywords):
            location_bonus = 15.0  # Full bonus for remote
        elif any(kw in location_type_combined for kw in hybrid_keywords):
            location_bonus = 10.0  # Partial bonus for hybrid
        elif any(kw in location_type_combined for kw in onsite_keywords):
            location_bonus = 5.0   # Small bonus for specific location

    # Total: skill score + location bonus, normalized to 100
    total_score = skill_score + location_bonus
    max_total = max_skill_score + 15.0  # Max skill score + max location bonus
    
    normalized_score = (total_score / max_total) * 100 if max_total > 0 else 0.0
    return min(normalized_score, 100.0)  # Cap at 100


def match_job(job_id: str, top_k: int = 10):
    job = job_col.get(ids=[job_id])

    if not job["documents"]:
        raise ValueError(f"Job {job_id} not found")

    job_text = job["documents"][0]
    job_meta = job["metadatas"][0]

    # Get all resumes
    all_resumes = list(resume_col._col.find({"metadata": {"$exists": True}}))

    # Calculate skill-based scores
    scored_resumes = []
    for resume in all_resumes:
        meta = resume.get("metadata", {})
        score = _calculate_skill_match_score(
            job_meta,
            meta.get("primary_skills", ""),
            meta.get("secondary_skills", "")
        )
        scored_resumes.append((resume["_id"], score, meta))

    # Sort by score descending, then by ID for stability
    scored_resumes.sort(key=lambda x: (-x[1], x[0]))
    top_results = scored_resumes[:top_k]

    print(f"\n🔍 Top {top_k} matches for Job: {job_id}\n")
    print(f"   Job required skills: {job_meta.get('skills', '')}")
    print(f"   Location: {job_meta.get('location', 'N/A')} | Type: {job_meta.get('job_type', 'N/A')}\n")

    for i, (rid, score, meta) in enumerate(top_results):
        print(f"{i+1}. {meta['filename']}")
        print(f"   Score: {score:.1f}/100")
        print(f"   Primary skills: {meta['primary_skills']}")
        print(f"   Secondary skills: {meta['secondary_skills']}")
        print("-" * 50)


if __name__ == "__main__":
    match_job("job3.txt")
