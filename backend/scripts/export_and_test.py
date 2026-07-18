"""
Export reviews data and test findings extraction, PRD generation, and test case generation.
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

from collector.apple_collector import collect_reviews
from analyzer.cleaner import clean_reviews
from analyzer.classifier import classify_reviews
from analyzer.finding_extractor import extract_findings
from planner.prd_generator import generate_prd
from planner.test_generator import generate_test_cases

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)


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
    print("=" * 60)
    print("Step 1: Collect reviews")
    print("=" * 60)
    reviews = collect_reviews("https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684")
    print(f"  Collected: {len(reviews)} reviews")
    save_json("test_raw_reviews.json", reviews)

    print()
    print("=" * 60)
    print("Step 2: Clean reviews")
    print("=" * 60)
    cleaned_result = clean_reviews(reviews)
    cleaned_data = cleaned_result.get("cleaned_data", [])
    print(f"  Cleaned: {len(cleaned_data)} reviews (removed {len(reviews) - len(cleaned_data)})")
    save_json("test_cleaned_reviews.json", cleaned_data)

    print()
    print("=" * 60)
    print("Step 3: Classify reviews")
    print("=" * 60)
    classified_result = classify_reviews(
        cleaned_data,
        analysis_goal="Identify user pain points, feature requests, and bug reports for product improvement",
    )
    classification_results = (
        classified_result.get("classification_results", [])
        if isinstance(classified_result, dict)
        else classified_result
    )
    print(f"  Classified: {len(classification_results)} reviews")
    save_json("test_classification_results.json", classification_results)

    print()
    print("=" * 60)
    print("Step 4: Extract findings")
    print("=" * 60)
    try:
        findings_result = extract_findings(
            classification_results,
            analysis_goal="Identify user pain points, feature requests, and bug reports for product improvement",
        )
        findings_list = (
            findings_result.get("findings", [])
            if isinstance(findings_result, dict)
            else findings_result
        )
        print(f"  Findings: {len(findings_list)}")
        if findings_list:
            for f in findings_list:
                sev = f.severity if hasattr(f, 'severity') else f.get('severity', '?')
                title = f.title if hasattr(f, 'title') else f.get('title', '?')
                print(f"    - [{sev}] {title}")
        save_json("test_findings.json", findings_list)
    except Exception as e:
        print(f"  ERROR extracting findings: {e}")
        import traceback
        traceback.print_exc()
        findings_list = []

    print()
    print("=" * 60)
    print("Step 5: Generate PRD")
    print("=" * 60)
    if findings_list:
        try:
            prd_result = generate_prd(
                findings_list,
                analysis_goal="Identify user pain points, feature requests, and bug reports for product improvement",
            )
            print(f"  PRD title: {prd_result.get('title', 'N/A')}")
            print(f"  Requirements: {prd_result.get('requirements_count', len(prd_result.get('requirements', [])))}")
            print(f"  Version plans: {len(prd_result.get('version_plan', []))}")
            print(f"  User stories: {len(prd_result.get('user_stories', []))}")
            save_json("test_prd.json", prd_result)
        except Exception as e:
            print(f"  ERROR generating PRD: {e}")
            import traceback
            traceback.print_exc()
            prd_result = None
    else:
        print("  SKIPPED: No findings to generate PRD from")
        prd_result = None

    print()
    print("=" * 60)
    print("Step 6: Generate test cases")
    print("=" * 60)
    if prd_result:
        try:
            test_cases = generate_test_cases(prd_result)
            print(f"  Test cases: {len(test_cases)}")
            if test_cases:
                for tc in test_cases:
                    print(f"    - {tc.get('id', '?')}: {tc.get('title', '?')} (req: {tc.get('related_requirement', '?')})")
            save_json("test_test_cases.json", test_cases)
        except Exception as e:
            print(f"  ERROR generating test cases: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("  SKIPPED: No PRD to generate test cases from")

    print()
    print("=" * 60)
    print("ALL DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()