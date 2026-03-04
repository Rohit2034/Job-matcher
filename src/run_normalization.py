"""
Standalone script to run skill normalization manually.

Usage:
    python src/run_normalization.py

This script runs the complete skill normalization pipeline:
1. Fetches all employees and jobs from MongoDB
2. Extracts unmapped skills (applies alias map first)
3. Sends new skills to OpenAI in batches
4. Updates normalized_skills.json
5. Applies normalized skills back to MongoDB
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from parsers.normalization import normalization


async def main():
    """Run the normalization pipeline."""
    print("=" * 60)
    print("Job Matcher - Skill Normalization Pipeline")
    print("=" * 60)
    print()
    
    try:
        result = await normalization()
        
        print("\n" + "=" * 60)
        print("NORMALIZATION COMPLETE")
        print("=" * 60)
        
        if isinstance(result, dict):
            print(f"\nOverall Success: {result.get('success', False)}")
            print(f"Message: {result.get('message', 'N/A')}")
            print(f"Total Records Modified: {result.get('total_modified', 0)}")
            print(f"Total Errors: {result.get('total_errors', 0)}")
            
            if result.get('employees'):
                emp = result['employees']
                print(f"\nEmployee Updates:")
                print(f"  - Modified: {emp.get('modified', 0)}")
                print(f"  - Matched: {emp.get('matched', 0)}")
                print(f"  - Errors: {emp.get('errors', 0)}")
            
            if result.get('jobs'):
                jobs = result['jobs']
                print(f"\nJob Updates:")
                print(f"  - Modified: {jobs.get('modified', 0)}")
                print(f"  - Matched: {jobs.get('matched', 0)}")
                print(f"  - Errors: {jobs.get('errors', 0)}")
        else:
            print(f"\nResult: {result}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
