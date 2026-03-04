import json
import os
import re
from collections import Counter
from typing import Dict, List, Tuple, Optional
from src.config.azure_con import AzureOpenAIConnection
from src.database.mongo import kb_collection


class SkillNormalizer:
    SIMILARITY_THRESHOLD = 0.4
    CANDIDATE_LIMIT = 20
    # Shared client and semaphore
    azure_connection = AzureOpenAIConnection()
    client = azure_connection.get_client()
    semaphore = azure_connection.get_semaphore()

    def __init__(self):
        pass

    def load_skill_map(self) -> Dict[str, str]:
        kb_doc = kb_collection.find_one({"_id": "skill_map"})
        if kb_doc and "map" in kb_doc:
            return kb_doc["map"]
        return {}



    def save_skill_map(self, skill_map: Dict[str, str]) -> None:
        kb_collection.update_one(
            {"_id": "skill_map"},
            {"$set": {"map": skill_map}},
            upsert=True
        )

    @staticmethod
    def tokenize(skill: str) -> set:
        return set(re.findall(r"[a-z0-9+#.]+", skill.lower()))



    @classmethod
    def jaccard_similarity(cls, a: str, b: str) -> float:
        set_a = cls.tokenize(a)
        set_b = cls.tokenize(b)
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)



    def filter_candidate_keys(self, new_skill: str, canonical_keys: List[str], threshold: float = None) -> List[str]:
        if threshold is None:
            threshold = self.SIMILARITY_THRESHOLD
        candidates = []
        for key in canonical_keys:
            score = self.jaccard_similarity(new_skill, key)
            if score >= threshold:
                candidates.append(key)
        return candidates[:self.CANDIDATE_LIMIT]



    async def get_chat_completion(self, temperature: float, prompt: str) -> Optional[dict]:
        async with SkillNormalizer.semaphore:
            response = await SkillNormalizer.client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                messages=[
                    {"role": "system", "content": "You are a strict skill canonicalization engine."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            raw = response.choices[0].message.content
            if not raw or not raw.strip():
                print("⚠ Empty response from LLM. Skipping.")
                return None
            try:
                return json.loads(raw)
            except Exception:
                raw = raw.strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start == -1 or end <= start:
                    print(f"⚠ Malformed response from LLM. Raw output:\n{raw}\nSkipping.")
                    return None
                try:
                    return json.loads(raw[start:end])
                except Exception:
                    print(f"⚠ Failed to parse JSON from LLM. Raw output:\n{raw}\nSkipping.")
                    return None


    async def map_skill_to_kb(self, skill: str, skill_map: Dict[str, str]) -> Optional[Tuple[str, bool]]:
        canonical_keys = list(set(skill_map.values()))
        candidate_keys = self.filter_candidate_keys(skill, canonical_keys)
        prompt = f"""
You are a strict skill canonicalization engine.

Existing Canonical Skills:
{json.dumps(candidate_keys, indent=2)}

New Skill:
"{skill}"

Rules:
- If this skill matches an existing canonical skill, return it.
- If not, create a NEW short canonical name.
- Avoid duplicates or fragmentation.
- Prefer concise names (e.g., React, Python, Node.js).
- Do not invent specializations unless necessary.

Return JSON:
{{
    "canonical": "Final Skill Name",
    "is_new": true/false
}}
"""
        result = await self.get_chat_completion(0, prompt)
        if not result:
            return None
        canonical = result.get("canonical", "").strip()
        is_new = result.get("is_new", False)
        return canonical, is_new


    @staticmethod
    def extract_all_skills(employees: List[dict], jobs: List[dict], skill_map: Dict[str, str]) -> List[str]:
        skill_counts = Counter()
        for emp in employees:
            skill_counts.update(emp.get("primary_skills", []))
            skill_counts.update(emp.get("secondary_skills", []))
        for job in jobs:
            skill_counts.update(job.get("primary_skills", []))
            skill_counts.update(job.get("secondary_skills", []))
            required = job.get("required_skills_with_scores", {})
            if isinstance(required, dict):
                skill_counts.update(required.keys())
        new_skills = [skill for skill in skill_counts.keys() if skill not in skill_map]
        new_skills.sort(key=lambda x: -skill_counts[x])
        return new_skills


    async def normalize_skills(self, employees: List[dict], jobs: List[dict]):
        skill_map = self.load_skill_map()
        skills_to_process = self.extract_all_skills(employees, jobs, skill_map)
        if not skills_to_process:
            print("No new skills found.")
            return skill_map
        print(f"Skills to normalize: {len(skills_to_process)}")
        for idx, skill in enumerate(skills_to_process, start=1):
            print(f"[{idx}/{len(skills_to_process)}] Processing: {skill}")
            result = await self.map_skill_to_kb(skill, skill_map)
            if not result:
                continue
            canonical, is_new = result
            skill_map[skill] = canonical
        self.save_skill_map(skill_map)
        print("Normalization complete.")
        return skill_map


    @staticmethod
    def apply_normalization_to_documents(documents: List[dict], skill_map: Dict[str, str]) -> List[dict]:
        def to_lower(s):
            return s.lower() if isinstance(s, str) else s
        for doc in documents:
            doc["primary_skills"] = [to_lower(skill_map.get(s, s)) for s in doc.get("primary_skills", [])]
            doc["secondary_skills"] = [to_lower(skill_map.get(s, s)) for s in doc.get("secondary_skills", [])]
            required = doc.get("required_skills_with_scores", {})
            if isinstance(required, dict):
                new_required = {}
                for skill, score in required.items():
                    canonical = to_lower(skill_map.get(skill, skill))
                    new_required[canonical] = score
                doc["required_skills_with_scores"] = new_required
        return documents


async def run_normalization(employees, jobs):
    normalizer = SkillNormalizer()
    skill_map = await normalizer.normalize_skills(employees, jobs)
    employees = SkillNormalizer.apply_normalization_to_documents(employees, skill_map)
    jobs = SkillNormalizer.apply_normalization_to_documents(jobs, skill_map)
    return employees, jobs