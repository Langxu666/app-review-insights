import json
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict

from services.openai_client import call_llm, parse_json_response
from schemas.test_case import TestCase

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "test_case_generation.md"


def _load_system_prompt() -> str:
    if not PROMPT_FILE.exists():
        logger.error(f"Prompt file not found: {PROMPT_FILE}")
        raise FileNotFoundError(f"Prompt file not found: {PROMPT_FILE}")

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    system_prompt_start = content.find("## System Prompt")
    output_format_start = content.find("## Output Format")

    if system_prompt_start == -1:
        logger.error("System Prompt section not found in prompt file")
        raise ValueError("System Prompt section not found")

    if output_format_start == -1:
        prompt_text = content[system_prompt_start:]
    else:
        prompt_text = content[system_prompt_start:output_format_start]

    prompt_text = prompt_text.replace("## System Prompt", "").strip()

    return prompt_text


def _extract_requirements(prd_draft: dict) -> List[dict]:
    if "requirements" in prd_draft:
        raw = prd_draft["requirements"]
    elif "prd_draft" in prd_draft and isinstance(prd_draft["prd_draft"], dict):
        raw = prd_draft["prd_draft"].get("requirements", [])
    else:
        logger.warning("No requirements found in PRD draft")
        return []

    requirements = []
    for req in raw:
        if isinstance(req, dict):
            requirements.append(req)
        elif hasattr(req, "model_dump"):
            requirements.append(req.model_dump())
        else:
            try:
                requirements.append(dict(req))
            except (TypeError, ValueError):
                logger.warning(f"Skipping non-dict requirement: {req}")
    return requirements


def _build_user_message(requirements: List[dict], prd_draft: dict) -> str:
    requirements_json = json.dumps(requirements, ensure_ascii=False, indent=2, default=str)

    prd_summary = {
        "title": prd_draft.get("title", "") or (
            prd_draft.get("prd_draft", {}).get("title", "") if isinstance(prd_draft.get("prd_draft"), dict) else ""
        ),
        "app_name": prd_draft.get("app_name", "") or (
            prd_draft.get("prd_draft", {}).get("app_name", "") if isinstance(prd_draft.get("prd_draft"), dict) else ""
        ),
    }
    prd_summary_json = json.dumps(prd_summary, ensure_ascii=False, default=str)

    user_message = f"""## PRD Requirements

Generate manual test case drafts for the following {len(requirements)} functional requirements:

{requirements_json}

## PRD Summary

{prd_summary_json}

## Output Requirements

Return ONLY a valid JSON object with a 'test_case_drafts' field.
Each test case must have its related_requirement set to the exact requirement ID from the PRD.
Do NOT include any other text or explanation."""

    return user_message


def _parse_test_cases(response: str) -> List[dict]:
    parsed = parse_json_response(response)

    if "error" in parsed:
        logger.error(f"Failed to parse test cases: {parsed['error']}")
        return []

    if "test_case_drafts" not in parsed:
        logger.error("test_case_drafts field not found in response")
        return []

    return parsed["test_case_drafts"]


def _validate_test_case(test_case: dict, valid_req_ids: set) -> bool:
    if not test_case.get("related_requirement"):
        logger.warning(f"Test case {test_case.get('id', 'unknown')} has no related_requirement")
        return False

    if test_case["related_requirement"] not in valid_req_ids:
        logger.warning(
            f"related_requirement {test_case['related_requirement']} not found in PRD requirements"
        )

    if not test_case.get("title"):
        logger.warning(f"Test case {test_case.get('id', 'unknown')} has no title")
        test_case["title"] = f"Verify requirement {test_case.get('related_requirement', 'UNKNOWN')}"

    if not test_case.get("steps"):
        logger.warning(f"Test case {test_case.get('id', 'unknown')} has no steps")
        test_case["steps"] = ["Verify the requirement is met"]

    if isinstance(test_case.get("steps"), str):
        test_case["steps"] = [test_case["steps"]]

    if isinstance(test_case.get("preconditions"), str):
        test_case["preconditions"] = [test_case["preconditions"]]

    if not test_case.get("preconditions"):
        test_case["preconditions"] = ["No specific preconditions"]

    if not test_case.get("expected_result"):
        logger.warning(f"Test case {test_case.get('id', 'unknown')} has no expected_result")
        test_case["expected_result"] = "Requirement is verified successfully."

    return True


def generate_test_cases(prd_draft: dict) -> List[dict]:
    system_prompt = _load_system_prompt()

    requirements = _extract_requirements(prd_draft)
    valid_req_ids = {str(req.get("req_id", "")) for req in requirements if req.get("req_id")}

    logger.info(f"Generating test cases for {len(requirements)} requirements")

    user_message = _build_user_message(requirements, prd_draft)
    response = call_llm(system_prompt, user_message, temperature=0.1)

    raw_test_cases = _parse_test_cases(response)

    if not raw_test_cases:
        logger.warning("No test cases generated, falling back to per-requirement generation")
        test_cases = []
        for req in requirements:
            fallback = {
                "id": f"TC{len(test_cases) + 1:03d}",
                "title": f"Verify {req.get('req_id', 'UNKNOWN')}: {req.get('feature_title', req.get('title', ''))}",
                "related_requirement": req.get("req_id", "UNKNOWN"),
                "preconditions": ["No specific preconditions"],
                "steps": [f"Verify requirement {req.get('req_id', 'UNKNOWN')} is implemented correctly"],
                "expected_result": f"Requirement {req.get('req_id', 'UNKNOWN')} is verified successfully.",
            }
            test_cases.append(fallback)
        return test_cases

    valid_test_cases = []
    tc_counter = 1
    existing_ids = set()

    for tc in raw_test_cases:
        if isinstance(tc, str):
            logger.warning(f"Skipping string test case: {tc[:50]}...")
            continue

        if not _validate_test_case(tc, valid_req_ids):
            continue

        if not tc.get("id"):
            tc["id"] = f"TC{tc_counter:03d}"

        tc_id = tc["id"]
        if tc_id in existing_ids:
            tc["id"] = f"TC{tc_counter:03d}"

        try:
            tc_obj = TestCase(**tc)
            valid_test_cases.append(tc_obj)
            existing_ids.add(tc["id"])
            tc_counter += 1
        except Exception as e:
            logger.error(f"Failed to create TestCase object: {e}")
            logger.debug(f"Raw test case: {tc}")

    if not valid_test_cases:
        logger.warning("No valid test cases after validation, falling back to per-requirement generation")
        for req in requirements:
            fallback = {
                "id": f"TC{len(valid_test_cases) + 1:03d}",
                "title": f"Verify {req.get('req_id', 'UNKNOWN')}: {req.get('feature_title', req.get('title', ''))}",
                "related_requirement": req.get("req_id", "UNKNOWN"),
                "preconditions": ["No specific preconditions"],
                "steps": [f"Verify requirement {req.get('req_id', 'UNKNOWN')} is implemented correctly"],
                "expected_result": f"Requirement {req.get('req_id', 'UNKNOWN')} is verified successfully.",
            }
            valid_test_cases.append(TestCase(**fallback))

    logger.info(f"Generated {len(valid_test_cases)} valid test cases")
    return [tc.model_dump() for tc in valid_test_cases]