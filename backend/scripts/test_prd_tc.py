"""
Quick test: PRD generation and Test Case generation from saved findings.
"""
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from planner.prd_generator import generate_prd
from planner.test_generator import generate_test_cases

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def to_serializable(obj):
    """Convert Pydantic models and other objects to JSON-serializable types."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    serializable = to_serializable(data)
    json_str = json.dumps(serializable, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json_str)
    print(f"  Saved: {path} ({len(json_str)} bytes)")
    return path


def main():
    # Load findings from saved file
    findings_path = os.path.join(DATA_DIR, "test_findings.json")
    with open(findings_path, "r", encoding="utf-8") as f:
        findings_list = json.load(f)
    print(f"Loaded {len(findings_list)} findings from {findings_path}")
    for f in findings_list:
        print(f"  - [{f.get('severity', '?')}] {f.get('title', '?')}")

    print()
    print("=" * 60)
    print("Step 1: Generate PRD from findings")
    print("=" * 60)
    try:
        prd_result = generate_prd(
            findings_list,
            analysis_goal="Identify user pain points, feature requests, and bug reports for product improvement",
        )
        
        if "error" in prd_result:
            print(f"  ERROR: {prd_result['error']}")
            return
        
        prd_draft = prd_result.get("prd_draft")
        if prd_draft:
            title = prd_draft.title if hasattr(prd_draft, 'title') else prd_draft.get('title', 'N/A')
            print(f"  PRD title: {title}")
        
        # Use the count fields from the result
        req_count = prd_result.get("requirements_count", 0)
        vp_count = prd_result.get("version_plans_count", 0)
        us_count = prd_result.get("user_stories_count", 0)
        print(f"  Requirements: {req_count}")
        print(f"  Version plans: {vp_count}")
        print(f"  User stories: {us_count}")
        
        # Access requirements from Pydantic model for detail display
        if prd_draft and hasattr(prd_draft, 'requirements'):
            requirements = prd_draft.requirements
        else:
            requirements = []
        
        if requirements:
            print("\n  Requirements detail:")
            for req in requirements:
                rid = req.req_id if hasattr(req, 'req_id') else req.get('req_id', '?')
                rtitle = req.title if hasattr(req, 'title') else req.get('title', '?')
                rpriority = req.priority if hasattr(req, 'priority') else req.get('priority', '?')
                print(f"    - [{rpriority}] {rid}: {rtitle}")
        
        save_json("test_prd.json", prd_result)
    except Exception as e:
        print(f"  ERROR generating PRD: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 60)
    print("Step 2: Generate test cases from PRD")
    print("=" * 60)
    try:
        test_cases = generate_test_cases(prd_result)
        print(f"  Test cases: {len(test_cases)}")
        if test_cases:
            for tc in test_cases:
                tcid = tc.get('id', '?') if isinstance(tc, dict) else getattr(tc, 'id', '?')
                tctitle = tc.get('title', '?') if isinstance(tc, dict) else getattr(tc, 'title', '?')
                tcreq = tc.get('related_requirement', '?') if isinstance(tc, dict) else getattr(tc, 'related_requirement', '?')
                print(f"    - {tcid}: {tctitle} (req: {tcreq})")
        save_json("test_test_cases.json", test_cases)
    except Exception as e:
        print(f"  ERROR generating test cases: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("ALL DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()