from src.matcher.matcher import match_job_to_resumes, match_resume_to_jobs
from src.database.mongo import resume_collection, job_collection


def main_menu():
    while True:
        try:
            print("\n========== JOB MATCHER SYSTEM ==========")
            print("1. Match Resume → Top JDs")
            print("2. Match Job → Top Resumes")
            print("3. Exit")

            choice = input("Enter choice: ").strip()

            # Resume → Job
            if choice == "1":

                resumes = list(
                    resume_collection.find({}, {"candidate_id": 1, "name": 1, "email": 1})
                )

                if not resumes:
                    print("No resumes found in database.\n")
                    continue

                print("\nAvailable Candidates:")
                for idx, r in enumerate(resumes, 1):
                    print(f"{idx}. {r.get('name', 'Unknown')} | {r.get('email')}")

                selected = input("\nEnter candidate number: ").strip()
                top_n = input("Top matches (default 5): ").strip()

                top_n = int(top_n) if top_n.isdigit() else 5

                selected_index = int(selected) - 1
                if 0 <= selected_index < len(resumes):
                    candidate_id = resumes[selected_index]["candidate_id"]
                else:
                    print("Invalid selection.\n")
                    continue

                results = match_resume_to_jobs(candidate_id, top_n)

                if not results:
                    print("No matching jobs found.\n")
                else:
                    print(f"\nTop {top_n} Matching Jobs:\n")
                    for idx, job in enumerate(results, 1):
                        print(f"{idx}. Job ID: {job.get('job_id')}")
                        print(f"   Category: {job.get('category', 'N/A')}")
                        print(f"   Technology: {job.get('technology')}")
                        print(f"   Score: {job.get('total_score', 0)}")
                        print()

            # Job → Resume
            elif choice == "2":

                jobs = list(
                    job_collection.find({}, {"job_id": 1, "technology": 1})
                )

                if not jobs:
                    print("No jobs found in database.\n")
                    continue

                print("\nAvailable Jobs:")
                for idx, j in enumerate(jobs, 1):
                    print(f"{idx}. {j.get('job_id')} | {j.get('technology')}")

                selected = input("\nEnter job number: ").strip()
                top_n = input("Top matches (default 5): ").strip()

                top_n = int(top_n) if top_n.isdigit() else 5

                selected_index = int(selected) - 1
                if 0 <= selected_index < len(jobs):
                    job_id = jobs[selected_index]["job_id"]
                else:
                    print("Invalid selection.\n")
                    continue

                results = match_job_to_resumes(job_id, top_n)

                if not results:
                    print("No matching resumes found.\n")
                else:
                    print(f"\nTop {top_n} Matching Resumes:\n")
                    for idx, r in enumerate(results, 1):
                        print(f"{idx}. {r.get('name')} | {r.get('email')}")
                        print(f"   Score: {r.get('total_score')}")
                        print()

            elif choice == "3":
                print("Exiting system. Goodbye!")
                break

            else:
                print("Invalid choice. Please select 1-3.\n")

        except KeyboardInterrupt:
            print("\nProgram interrupted. Exiting safely.")
            break

        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main_menu()