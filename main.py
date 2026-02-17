import sys
from ingest import ingest_resumes, ingest_jobs
from match import match_job
from mongo_client import client

job_col = client.get_collection("jobs")

def print_menu():
    print("\n" + "=" * 50)
    print(" JOB MATCHER SYSTEM - CLI")
    print("=" * 50)
    print("1. Ingest Resumes (data/resumes)")
    print("2. Ingest Jobs (data/jobs)")
    print("3. Match Job")
    print("4. Exit")
    print("=" * 50)


def handle_ingest_resumes():
    try:
        print("\n Ingesting resumes from data/resumes ...\n")
        ingest_resumes("data/resumes")
        print(" Resume ingestion completed.\n")
    except Exception as e:
        print(" Error ingesting resumes:", e)


def handle_ingest_jobs():
    try:
        print("\n Ingesting jobs from data/jobs ...\n")
        ingest_jobs("data/jobs")
        print("Job ingestion completed.\n")
    except Exception as e:
        print(" Error ingesting jobs:", e)


def handle_match_job():
    try:
        # Fetch all jobs
        all_jobs = list(job_col._col.find({"metadata": {"$exists": True}}))

        if not all_jobs:
            print(" No jobs found. Please ingest jobs first (Option 2).")
            return

        print("\n Available Jobs")
        print("=" * 40)
        print(f"Total Jobs: {len(all_jobs)}\n")

        for idx, job in enumerate(all_jobs, 1):
            job_id = job["_id"]
            print(f"{idx}. {job_id}")

        print("=" * 40)

        choice = input("Select job number to match: ").strip()

        if not choice.isdigit():
            print(" Invalid selection.")
            return

        choice = int(choice)

        if choice < 1 or choice > len(all_jobs):
            print(" Selection out of range.")
            return

        selected_job_id = all_jobs[choice - 1]["_id"]

        top_k = input("How many top results? (default 5): ").strip()
        top_k = int(top_k) if top_k.isdigit() else 5

        match_job(selected_job_id, top_k=top_k) 

    except Exception as e:
        print(" Error matching job:", e)


def main():
    while True:
        print_menu()
        choice = input("Select option (1-4): ").strip()

        if choice == "1":
            handle_ingest_resumes()

        elif choice == "2":
            handle_ingest_jobs()

        elif choice == "3":
            handle_match_job()

        elif choice == "4":
            print(" Exiting Job Matcher CLI...")
            sys.exit(0)

        else:
            print(" Invalid option. Please select 1-4.")


if __name__ == "__main__":
    main()
