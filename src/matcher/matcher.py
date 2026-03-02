from database.mongo import resume_collection, job_collection

PRIMARY_WEIGHT = 70
SECONDARY_WEIGHT = 30


def normalize_list(value):
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip().lower() for v in value.split(",") if v.strip()]
    return []


def safe_array(field_name):
    return {
        "$cond": {
            "if": {"$isArray": f"${field_name}"},
            "then": {
                "$map": {
                    "input": f"${field_name}",
                    "as": "item",
                    "in": {
                        "$cond": [
                            {"$eq": [{"$type": "$$item"}, "string"]},
                            {"$toLower": "$$item"},
                            ""
                        ]
                    }
                }
            },
            "else": {
                "$cond": {
                    "if": {"$eq": [{"$type": f"${field_name}"}, "string"]},
                    "then": [{"$toLower": f"${field_name}"}],
                    "else": []
                }
            }
        }
    }

def match_resume_to_jobs(candidate_id: str, top_n: int = 5):
    resume = resume_collection.find_one({"candidate_id": candidate_id})
    if not resume:
        return []

    resume_primary = normalize_list(resume.get("primary_skills"))
    resume_secondary = normalize_list(resume.get("secondary_skills"))
    resume_experience = resume.get("total_experience_months")

    if resume_experience is None:
        years = resume.get("experience_years", 0)
        resume_experience = int(float(years) * 12)

    pipeline = [
    # 🔹 Pre-filter jobs using $match
    {
        "$match": {
            "$or": [
                {"primary_skills": {"$in": resume_primary}},
                {"secondary_skills": {"$in": resume_secondary}}
            ]
        }
    },

    {
            "$match": {
                "minimum_experience_in_months": {"$lte": resume_experience}
            }
        },

    # 🔹 Normalize fields safely
    {
        "$addFields": {
            "primary_array": safe_array("primary_skills"),
            "secondary_array": safe_array("secondary_skills"),
        }
    },

    # 🔹 Compute skill intersections
    {
        "$addFields": {
            "primary_match": {"$size": {"$setIntersection": ["$primary_array", resume_primary]}},
            "secondary_match": {"$size": {"$setIntersection": ["$secondary_array", resume_secondary]}}
        }
    },

    # 🔹 Compute scores
    {
        "$addFields": {
            "primary_score": {
                "$multiply": [
                    {"$divide": ["$primary_match", {"$max": [{"$size": "$primary_array"}, 1]}]},
                    PRIMARY_WEIGHT
                ]
            },
            "secondary_score": {
                "$multiply": [
                    {"$divide": ["$secondary_match", {"$max": [{"$size": "$secondary_array"}, 1]}]},
                    SECONDARY_WEIGHT
                ]
            }
        }
    },

    # 🔹 Total score
    {
        "$addFields": {
            "total_score": {
                "$round": [
                    {"$add": ["$primary_score", "$secondary_score"]},
                    2
                ]
            }
        }
    },

    # 🔹 Sort and limit
    {"$sort": {"total_score": -1}},
    {"$limit": top_n},

    # 🔹 Final projection
    {
        "$project": {
            "_id": 0,
            "job_id": 1,
            "job_summary": 1,
            "technology": 1,
            "category": 1,
            "total_score": 1
        }
    }
]

    return list(job_collection.aggregate(pipeline))


def match_job_to_resumes(job_id: str, top_n: int = 5):
    job = job_collection.find_one({"job_id": job_id})
    if not job:
        return []

    job_primary = normalize_list(job.get("primary_skills"))
    job_secondary = normalize_list(job.get("secondary_skills"))
    job_experience = job.get("minimum_experience_in_months")

    if job_experience is None:
        years = job.get("minimum_experience_in_years", 0)
        job_experience = int(float(years) * 12)

    pipeline = [
        {
            "$match": {
                "$or": [
                    {"primary_skills": {"$in": job_primary}},
                    {"secondary_skills": {"$in": job_secondary}}
                ]
            }
        },

        {
            "$match": {
                "total_experience_months": {"$gte": job_experience}
            }
        },

        {
            "$addFields": {
                "primary_array": safe_array("primary_skills"),
                "secondary_array": safe_array("secondary_skills"),
            }
        },

        {
            "$addFields": {
                "primary_match": {"$size": {"$setIntersection": ["$primary_array", job_primary]}},
                "secondary_match": {"$size": {"$setIntersection": ["$secondary_array", job_secondary]}}
            }
        },

        {
            "$addFields": {
                "primary_score": {
                    "$multiply": [
                        {"$divide": ["$primary_match", {"$max": [{"$size": "$primary_array"}, 1]}]},
                          PRIMARY_WEIGHT
                    ]
                },
                "secondary_score": {
                    "$multiply": [
                        {"$divide": ["$secondary_match", {"$max": [{"$size": "$secondary_array"}, 1]}]}, 
                        SECONDARY_WEIGHT
                    ]
                },
            }
        },
        
        {"$addFields": {
            "total_score": {"$round": [{"$add": ["$primary_score", "$secondary_score"]}, 2]}
        }},
        {"$sort": {"total_score": -1}},
        {"$limit": top_n},
        {"$project": {"_id": 0, "candidate_id": 1, "name": 1, "email": 1, "total_score": 1}}
    ]

    return list(resume_collection.aggregate(pipeline))
