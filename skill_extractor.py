import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_version=os.getenv("AZURE_API_VERSION")
)

AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT")


def parse_skills(text: str):
    """
    Extract primary and secondary skills from resume text
    Returns: (primary_skills, secondary_skills)
    """

    if not text or len(text.strip()) < 50:
        return [], []

    prompt = f"""
Extract skills from the following resume text.

Return ONLY valid JSON in this format:
{{
  "primary_skills": ["skill1", "skill2"],
  "secondary_skills": ["skillA", "skillB"]
}}

Resume:
{text[:4000]}
"""

    response = client.chat.completions.create(
        model=AZURE_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "You are a resume skill extraction engine."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        return data.get("primary_skills", []), data.get("secondary_skills", [])
    except json.JSONDecodeError:
        print("Skill extraction failed, invalid JSON")
        return [], []