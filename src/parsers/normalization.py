import json
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
import time
import asyncio
from config.logger import normalization as logger
from database.mongo import resume_collection, job_collection
from pathlib import Path
import re

BASE_DIR = Path(__file__).parent
NORMALIZED_SKILLS_FILE = BASE_DIR / "normalized_skills.json"

# Common alias map: simplified keys (alphanumeric lowercase) -> canonical skill name
ALIAS_MAP = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "py": "Python",
    "python": "Python",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react": "React",
}


def _simple_key(skill: str) -> str:
    if not skill:
        return ""
    s = str(skill).lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def extract_skills(employees: list, jobs: list, skill_map: dict) -> list:
    """
    Extract skills not yet present in skill_map, applying alias map to capture
    short forms (e.g., "js" -> "JavaScript") so they are treated consistently.
    """
    skills = set()

    # Build a normalized lookup set for existing skill_map keys (using simple keys)
    normalized_map_keys = { _simple_key(k): v for k, v in skill_map.items() }

    def add_skill_candidate(raw_skill):
        if not raw_skill:
            return
        
        # Ensure it's a string, not a list or other type
        if isinstance(raw_skill, list):
            logger.warning(f"Skill is a list, skipping: {raw_skill}")
            return
        
        raw_skill = str(raw_skill).strip()
        if not raw_skill:  # After strip, check again
            return
            
        simple = _simple_key(raw_skill)

        # If alias map maps this short form to a canonical name, use canonical
        if simple in ALIAS_MAP:
            canonical = ALIAS_MAP[simple]
            # If canonical already known in skill_map, skip
            if _simple_key(canonical) in normalized_map_keys:
                return
            skills.add(canonical)
            return

        # Otherwise if raw skill (simple) already in skill_map keys, skip
        if simple in normalized_map_keys:
            return

        # Add the original raw skill for human/OpenAI normalization
        skills.add(raw_skill)

    for doc in employees:
        for skill in doc.get("primary_skills", []):
            add_skill_candidate(skill)
        for skill in doc.get("secondary_skills", []):
            add_skill_candidate(skill)

    for doc in jobs:
        for skill_obj in doc.get("required_skills_with_scores", []):
            # Handle both string and dict formats
            if isinstance(skill_obj, str):
                skill_name = skill_obj
            elif isinstance(skill_obj, dict):
                skill_name = skill_obj.get("skill_name")
            else:
                logger.warning(f"Unexpected skill format: {skill_obj} (type: {type(skill_obj)})")
                continue
            
            add_skill_candidate(skill_name)

    skills = list(skills)
    skills.sort()
    return skills

# The rest of the file mirrors the original bulk-write helpers but uses a robust
# lookup when applying the skill_map so that keys with punctuation or different
# casing still resolve correctly.

async def process_employees(employee_operations):
    if not employee_operations:
        logger.error("No employee operations to process.")
        return {
            "success": True,
            "modified": 0,
            "matched": 0,
            "errors": 0,
            "message": "No employees operations to perform"
        }
    try:
        # Run synchronous bulk_write in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: resume_collection.bulk_write(employee_operations, ordered=False)
        )
        logger.info(
            f"Employee skills replacement complete: {result.modified_count} updated, {result.matched_count} matched"
        )
        return {
            "success": True,
            "modified": result.modified_count,
            "matched": result.matched_count,
            "errors": 0,
            "message": f"Successfully updated {result.modified_count} employees"
        }
    except BulkWriteError as bwe:
        write_errors = bwe.details.get('writeErrors', [])
        n_modified = bwe.details.get('nModified', 0)
        n_matched = bwe.details.get('nMatched', 0)
        n_errors = len(write_errors)
        logger.error(
            f"Employee bulk write was partial success: {n_modified} modified, {n_matched} matched, {n_errors} errors"
        )
        for error in write_errors[:5]:
            logger.error(f"Employee write error: {error}")
        return {
            "success": False,
            "modified": n_modified,
            "matched": n_matched,
            "errors": n_errors,
            "message": f"Partial success: {n_modified} updated, {n_errors} errors"
        }
    except Exception as e:
        logger.error(f"Unexpected error while updating normalized skills in employee colection: {e}")
        return {
            "success": False,
            "modified": 0,
            "matched": 0,
            "errors": len(employee_operations),
            "message": f"Failed to update the employee skill names: {str(e)}"
        }


async def process_jobs(job_operations):
    if not job_operations:
        logger.error("No job operations to process.")
        return {
            "success": True,
            "modified": 0,
            "matched": 0,
            "errors": 0,
            "message": "No job operations to perform"
        }
    try:
        # Run synchronous bulk_write in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: job_collection.bulk_write(job_operations, ordered=False)
        )
        logger.info(
            f"Job skills replacement complete: {result.modified_count} updated, {result.matched_count} matched"
        )
        return {
            "success": True,
            "modified": result.modified_count,
            "matched": result.matched_count,
            "errors": 0,
            "message": f"Successfully updated {result.modified_count} jobs"
        }
    except BulkWriteError as bwe:
        write_errors = bwe.details.get('writeErrors', [])
        n_modified = bwe.details.get('nModified', 0)
        n_matched = bwe.details.get('nMatched', 0)
        n_errors = len(write_errors)
        logger.error(
            f"Job bulk write partial success: {n_modified} modified, {n_matched} matched, {n_errors} errors"
        )
        for error in write_errors[:5]:
            logger.error(f"Job write error: {error}")
        return {
            "success": False,
            "modified": n_modified,
            "matched": n_matched,
            "errors": n_errors,
            "message": f"Partial success: {n_modified} updated, {n_errors} errors"
        }
    except Exception as e:
        logger.error(f"Unexpected error while updating normalized skills in job colection: {e}")
        return {
            "success": False,
            "modified": 0,
            "matched": 0,
            "errors": len(job_operations),
            "message": f"Failed to update job skill names: {str(e)}"
        }


async def replace_skills(employees, jobs, skill_map):
    employee_operations = []
    job_operations = []

    # Build normalized lookup for skill_map
    normalized_map = { _simple_key(k): v for k, v in skill_map.items() }

    def resolve_skill(raw_skill):
        """Resolve a raw skill to the final standardized name using:
           1) exact key in skill_map
           2) simple-key lookup in skill_map
           3) alias map
           4) fallback to original raw_skill
        """
        if raw_skill is None:
            return ""
        
        # Handle list case - flatten to first element or empty string
        if isinstance(raw_skill, list):
            logger.warning(f"resolve_skill received a list: {raw_skill}, using first element")
            raw_skill = raw_skill[0] if raw_skill else ""
        
        raw_skill_str = str(raw_skill).strip()
        if not raw_skill_str:
            return ""
            
        # 1) exact
        if raw_skill_str in skill_map:
            return skill_map[raw_skill_str]
        # 2) simple key
        simple = _simple_key(raw_skill_str)
        if simple in normalized_map:
            return normalized_map[simple]
        # 3) alias
        if simple in ALIAS_MAP:
            return ALIAS_MAP[simple]
        # fallback
        return raw_skill_str

    for doc in employees:
        employee_id = doc.get("employee_id")
        primary_skills = doc.get("primary_skills", [])
        secondary_skills = doc.get("secondary_skills", [])

        updated_primary_skills = set([
            resolve_skill(skill) for skill in primary_skills
            if resolve_skill(skill)  # Filter out empty strings
        ])

        updated_secondary_skills = set([
            resolve_skill(skill) for skill in secondary_skills
            if resolve_skill(skill)  # Filter out empty strings
        ])

        updated_secondary_skills = updated_secondary_skills - updated_primary_skills

        employee_operations.append(
            UpdateOne(
                {"employee_id": employee_id},
                {"$set": {
                    "primary_skills": list(updated_primary_skills),
                    "secondary_skills": list(updated_secondary_skills),
                    "is_normalized": True
                }}
            )
        )

    for doc in jobs:
        so_id = doc.get("so_id")
        required_skills_with_scores = doc.get("required_skills_with_scores", [])

        updated_required_skills_with_scores = []
        seen_skills = set()

        for skill_obj in required_skills_with_scores:
            # Handle both string and dict formats
            if isinstance(skill_obj, str):
                original_name = skill_obj
                score = 0
            elif isinstance(skill_obj, dict):
                original_name = skill_obj.get("skill_name")
                score = skill_obj.get("score", 0)
            else:
                logger.warning(f"Unexpected skill format in replace_skills: {skill_obj}")
                continue
                
            updated_name = resolve_skill(original_name)

            # Skip empty or already-seen skills
            if not updated_name or updated_name in seen_skills:
                continue
                
            seen_skills.add(updated_name)
            updated_required_skills_with_scores.append({
                "skill_name": updated_name,
                "score": score
            })

        updated_required_skills_with_scores.sort(
            key=lambda x: (-x["score"], x["skill_name"])
        )

        job_operations.append(
            UpdateOne(
                {"so_id": so_id},
                {"$set": {
                    "required_skills_with_scores": updated_required_skills_with_scores,
                    "is_normalized": True
                }}
            )
        )

    employee_result, job_result = await asyncio.gather(
        process_employees(employee_operations),
        process_jobs(job_operations)
    )

    overall_success = employee_result["success"] and job_result["success"]
    return {
        "success": overall_success,
        "employees": employee_result,
        "jobs": job_result,
        "total_modified": employee_result["modified"] + job_result["modified"],
        "total_errors": employee_result["errors"] + job_result["errors"],
        "message": "Skill replacement complete" if overall_success else "Skill replacement completed with errors"
    }


async def normalization():
    try:
        logger.info("Starting skill normalization process.")
        start_time = time.perf_counter()

        logger.info("Fetching employees and jobs from MongoDB...")
        # Use synchronous MongoDB calls (not async)
        employees = list(resume_collection.find({}))
        jobs = list(job_collection.find({}))

        logger.info(f"length of employees_collection: {len(employees)}.")
        logger.info(f"length of jobs_collection: {len(jobs)}.")

        # Load existing map (create file if missing)
        if not NORMALIZED_SKILLS_FILE.exists():
            with open(NORMALIZED_SKILLS_FILE, 'w') as f:
                json.dump({}, f)

        with open(NORMALIZED_SKILLS_FILE, 'r') as file:
            skill_map = json.load(file)

        logger.info("Extracting skills from employees and jobs...")
        skills = extract_skills(employees, jobs, skill_map)

        if len(skills) == 0:
            logger.info("No new skills where found. So skipping normalization.")
            logger.info("Applying replacement with existing skill map...")
            response = await replace_skills(employees, jobs, skill_map)
            end_time = time.perf_counter()
            time_taken_seconds = end_time - start_time
            logger.info(f"Time taken to normalize and update: {time_taken_seconds:.2f} seconds")
            return response

        logger.info(f"length of skills to normalize: {len(skills)}.")

        batch_size = 800
        chunks = [skills[i:i + batch_size] for i in range(0, len(skills), batch_size)]
        total_batches = len(chunks)

        logger.info(f"Total batches to process: {total_batches}. Batch size: {batch_size}.")

        for idx, batch in enumerate(chunks, start=1):
            await openai_function(idx, batch, total_batches, skill_map)

        with open(NORMALIZED_SKILLS_FILE, 'w') as f:
            json.dump(skill_map, f, indent=4)

        logger.info("All batches processed. Final output saved to normalized_skills.json.")

        logger.info("Applying normalized skills back to MongoDB...")
        response = await replace_skills(employees, jobs, skill_map)

        end_time = time.perf_counter()
        time_taken_seconds = end_time - start_time
        logger.info(f"Time taken to normalize and update: {time_taken_seconds:.2f} seconds")
        return response
    except Exception as e:
        import traceback
        logger.error(f"Error during normalization process: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"Error during normalization process: {str(e)}"


# OpenAI helpers
from openai_client import client, DEPLOYMENT_NAME


async def get_chat_completion(idx, user_input):
    logger.info(f"Batch: {idx}. Sending request to Azure OpenAI API.")
    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": user_input}],
            temperature=0,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )

        verbose = True

        if verbose:
            i_tokens = response.usage.prompt_tokens
            o_tokens = response.usage.completion_tokens
            current_rupee_value = 85.47
            i_cost = i_tokens * 0.000002 * current_rupee_value
            o_cost = o_tokens * 0.000008 * current_rupee_value
            logger.info(f"Batch: {idx}. Azure OpenAI API response received. Input tokens: {i_tokens}, Output tokens: {o_tokens}, Total tokens: {response.usage.total_tokens}, Estimated cost: ₹{i_cost+o_cost:.4f}")

        assistant_reply = response.choices[0].message.content
        pattern = r'```json\n([\s\S]*?)\n```'
        formatted_data = re.search(pattern, assistant_reply)
        if formatted_data:
            json_string = formatted_data.group(1).strip()
            document = json.loads(json_string)
            return document
        else:
            logger.error(f"Batch: {idx}. No JSON string found in the response.")
            return {}
    except Exception as e:
        logger.error(f"Batch: {idx}. Error during API call: {e}")
        return {}


async def openai_function(idx, batch, total_batches, skill_map):
    logger.info(f"Processing batch {idx}/{total_batches} with {len(batch)} skills.")
    prompt = f"""
    You are given a list of skill names. Each skill may have multiple variations referring to the same core concept.

    Your task is to **normalize** each skill into the **smallest possible set of concise, standard skills**, avoiding unnecessary fragmentation.

    ### Existing Normalizations:
    {json.dumps(skill_map, indent=2)}

    ### New Skills to Normalize:
    {json.dumps(batch, indent=2)}

    ### Requirements:
    - Reuse existing mappings wherever possible.
    - Group all closely related variations under a common standard name (e.g., "React JS", "React.js", "ReactJS" → "React").
    - Only create a new standardized name if it is **functionally or technologically distinct** from existing ones (e.g., "React Native" is different from "React").
    - Prefer short, clean, lowercase-with-title-case names like "React", "Node.js", "Python".
    - Do **not** keep library/tool names separate unless they are commonly used as distinct skills in resumes or job descriptions.

    ### Examples:
    - "React Hook Forms", "React Hooks", "React Testing Library" → "React"
    - "ReactJS", "React.js", "React Js" → "React"
    - "React Native", "React-Native" → "React Native"

    ### Output Format:
    ```json
    {{
        "Original Skill": "Standardized Skill",
        "Another Variation": "Standardized Skill"
    }}
    """

    MAX_RETRIES = 3
    batch_output = {}
    for attempt in range(1, MAX_RETRIES + 1):
        batch_output = await get_chat_completion(idx, prompt)
        if batch_output:
            break
        if attempt < MAX_RETRIES:
            await asyncio.sleep(1)

    if batch_output:
        skill_map.update(batch_output)
    else:
        logger.error(f"Max retries reached. Batch {idx} skipped due to error while OpenAI processing.")
        return

    logger.info(f"Batch {idx} processed and saved successfully.")
