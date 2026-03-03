# Job Matcher

Job Matcher is an AI-based resume screening and job-matching system that extracts structured information from resumes and job descriptions using Azure OpenAI and matches candidates using weighted skill-based scoring implemented directly in MongoDB aggregation pipelines.

## Overview

The system reduces manual resume screening by:

- Parsing resumes and job descriptions from PDF files  
- Extracting structured JSON data using Azure OpenAI  
- Separating primary and secondary skills with normalization  
- Storing standardized data in MongoDB  
- Matching jobs ↔ resumes using hybrid weighted scoring (no embeddings)  

## Main Features

- Resume and JD parsing using Azure OpenAI (async client)  
- Strict JSON output enforcement via prompt engineering  
- Primary and secondary skill extraction with normalization  
- MongoDB-based storage with indexed fields  
- Skill-based weighted hybrid scoring  
- Matching in both directions:  
  - Job → Top candidate resumes  
  - Resume → Top matching jobs  
- CLI-driven workflow  

## Workflow

1. Place resume PDFs in:

```

data/input/resumes

```

2. Place JD PDFs in:

```

data/input/jd

```

3. Run the jd_parser:

```

python -m src.parsers.jd_parser

```

4. Run the resume_parser:

```

python -m src.parsers.resume_parser

```

5. Run the CLI:

```

python -m src.main

```

4. Parse resumes or JDs using Azure OpenAI.  
5. Extract structured JSON fields (skills, experience, location, education, etc.).  
6. Normalize and upsert data into MongoDB.  
7. Run matching using MongoDB aggregation pipelines.  
8. Return ranked results based on weighted scoring.  

## Project Structure

```

src/
├── main.py                         # CLI menu and orchestration
├── parsers/
│   ├── resume_parser.py            # Resume parsing and MongoDB upsert
│   ├── jd_parser.py                # JD parsing and MongoDB upsert
│   └── pdf_extractor.py            # PDF text extraction
├── matcher/
│   └── matcher.py                  # Matching logic and scoring pipelines
├── database/
│   └── mongo.py                    # MongoDB client and index setup
├── config/
│   ├── settings.py                 # Environment configuration
│   └── tech_mapping.py             # Technology-category classification loader
data/
├── input/
│   ├── resumes/                    # Resume PDFs
│   └── jd/                         # JD PDFs

```

## MongoDB Data Format

### Resume Document

- candidate_id (UUID)  
- name  
- email  
- primary_skills (normalized list)  
- secondary_skills (normalized list)  
- location (list)  
- experience_years (computed from parsed experience)  
- education  
- profile_summary  
- created_at  

### Job Document

- job_id (filename without extension)  
- job_summary  
- key_responsibilities  
- primary_skills (normalized list)  
- secondary_skills (normalized list)  
- required_skills_with_scores (dictionary)  
- minimum_experience_in_years  
- technology  
- category  
- location  
- justification  
- created_at  

## Database Details

- **Database Name:** `Job_Matcher`  
- **Collections:** `resumes`, `jobs`  

Indexes are created for:

- candidate_id  
- email  
- job_id  
- Skill fields  

## Matching Logic

Matching is implemented using MongoDB aggregation pipelines.

### Weighted Scoring Parameters

```

PRIMARY_WEIGHT   = 70
SECONDARY_WEIGHT = 30


```

### Scoring Components

- Primary skill overlap  
- Secondary skill overlap  

experience acts as a cutoff 

**Final Score = Weighted sum of all scoring components**

Results are sorted in descending order and top N matches are returned.

**Important:**  
There is NO embedding generation or semantic vector search in the current codebase.

## Basic Usage

### 1. Install Dependencies

```

pip install -r requirements.txt

```

### 2. Set Environment Variables

- MONGO_URI  
- AZURE_OPENAI_API_KEY  
- AZURE_OPENAI_ENDPOINT  
- AZURE_OPENAI_API_VERSION  
- AZURE_OPENAI_DEPLOYMENT  
- AZURE_CONCURRENCY  

### 3. Run the CLI

```

python -m src.main

```

### 4. Choose Menu Options

- Match Job → Resumes  
- Match Resume → Jobs
- Exit  

## Tech Stack

- Python 3.8+  
- Azure OpenAI (async client)  
- MongoDB  
- pypdf  
- asyncio  

## Requirements

- Python environment  
- MongoDB (local or Atlas)  
- Azure OpenAI credentials  
- Proper environment variable configuration  

## Security Notes

- Never commit `.env` file.  
- Keep Azure API keys and MongoDB URI private.  
- Resume data contains personal information — handle securely.  
```
