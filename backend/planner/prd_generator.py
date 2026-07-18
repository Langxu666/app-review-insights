import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any

from services.openai_client import call_llm, parse_json_response
from schemas.prd import PRDDraft, Requirement, VersionPlan, UserStory, Priority

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "prd_generation.md"
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_EFFORTS = {"S", "M", "L", "XL"}


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


def _build_user_message(findings: List[dict], analysis_goal: Optional[str] = None, app_name: Optional[str] = None) -> str:
    findings_json = json.dumps(findings, ensure_ascii=False, indent=2, default=str)
    
    app_text = f"\n\n## App Name\n{app_name}\n" if app_name else ""
    goal_text = f"\n\n## Analysis Goal\n{analysis_goal}\n" if analysis_goal else ""
    
    user_message = f"""## Validated Findings

Please generate a PRD draft from the following {len(findings)} findings:

{findings_json}

{app_text}{goal_text}

## Output Requirements

Return ONLY a valid JSON object with a 'prd_draft' field. Do NOT include any other text or explanation."""
    
    return user_message


def _parse_prd(response: str) -> dict:
    parsed = parse_json_response(response)
    
    if "error" in parsed:
        logger.error(f"Failed to parse PRD: {parsed['error']}")
        return {}
    
    if isinstance(parsed, list):
        logger.error("Response is a list, expected dict")
        return {}
    
    if "prd_draft" not in parsed:
        logger.error("prd_draft field not found in response")
        return {}
    
    return parsed["prd_draft"]


def _validate_requirement(requirement: dict, valid_finding_ids: set, all_req_ids: set) -> bool:
    if not requirement.get("source_finding_ids"):
        logger.warning(f"Requirement {requirement.get('req_id', 'unknown')} has no source_finding_ids, will auto-assign from description")
        requirement["source_finding_ids"] = []
    
    for fid in requirement["source_finding_ids"]:
        if fid not in valid_finding_ids:
            logger.warning(f"source_finding_id {fid} not found in findings")
    
    priority = requirement.get("priority", "P2")
    if priority not in VALID_PRIORITIES:
        logger.warning(f"Invalid priority {priority}, defaulting to P2")
        requirement["priority"] = "P2"
    
    effort = requirement.get("effort_estimate", "M")
    if effort not in VALID_EFFORTS:
        logger.warning(f"Invalid effort_estimate {effort}, defaulting to M")
        requirement["effort_estimate"] = "M"
    
    target_version = requirement.get("target_version", "v1.1")
    if not re.match(r"^v\d+\.\d+$", target_version):
        logger.warning(f"Invalid target_version format {target_version}, defaulting to v1.1")
        requirement["target_version"] = "v1.1"
    
    if not requirement.get("is_assumption"):
        requirement["is_assumption"] = False
    
    return True


def _validate_version_plan(version_plan: dict, all_req_ids: set) -> bool:
    req_ids = version_plan.get("requirement_ids", [])
    for rid in req_ids:
        if rid not in all_req_ids:
            logger.warning(f"requirement_id {rid} in version_plan not found in requirements")
    
    return True


def _normalize_requirements(raw_reqs: list) -> list:
    """Normalize LLM-generated requirements to match the expected schema.
    
    Handles:
    - 'id' → 'req_id'
    - Missing 'title' → derived from 'description'
    - Missing 'user_problem' / 'business_value' → defaults
    - 'acceptance_criteria' as string → list
    """
    normalized = []
    for req in raw_reqs:
        if isinstance(req, str):
            logger.warning(f"Skipping requirement string: {req[:50]}...")
            continue
        
        # Map 'id' → 'req_id'
        if "id" in req and "req_id" not in req:
            req["req_id"] = req.pop("id")
        
        # Generate title from description if missing
        if not req.get("title") and req.get("description"):
            desc = req["description"]
            req["title"] = desc[:80] + ("..." if len(desc) > 80 else "")
        
        # Default missing fields
        if not req.get("user_problem"):
            req["user_problem"] = req.get("description", "User problem not specified")
        if not req.get("business_value"):
            req["business_value"] = "Improves user satisfaction and retention"
        
        # Convert acceptance_criteria string to list
        if isinstance(req.get("acceptance_criteria"), str):
            req["acceptance_criteria"] = [req["acceptance_criteria"]]
        
        normalized.append(req)
    return normalized


def _normalize_version_plan(version_plan: Any) -> list:
    """Normalize version_plan from object format to array format.
    
    Handles LLM returning: {"v1.1": {...}, "v1.2": {...}}
    Instead of expected: [{"version": "v1.1", ...}, {"version": "v1.2", ...}]
    """
    if isinstance(version_plan, dict) and not isinstance(version_plan, list):
        logger.info("Converting version_plan from object to array format")
        plans = []
        for version_key, plan_data in version_plan.items():
            if isinstance(plan_data, dict):
                plan_data["version"] = version_key
                plans.append(plan_data)
            else:
                logger.warning(f"Skipping non-dict version plan entry: {version_key}")
        return plans
    return version_plan if isinstance(version_plan, list) else []


def _normalize_user_stories(raw_stories: list) -> list:
    """Normalize user stories from string format to structured objects.
    
    Handles LLM returning: ["As a user, I want X, so that Y"]
    Instead of expected: [{"id": "US001", "role": "user", "goal": "X", "benefit": "Y"}]
    """
    normalized = []
    for i, us in enumerate(raw_stories):
        if isinstance(us, str):
            # Parse "As a [role], I want [goal], so that [benefit]"
            story_text = us
            role = "user"
            goal = ""
            benefit = ""
            is_english = story_text.startswith("As a ")
            
            if is_english:
                rest = story_text[5:]  # Remove "As a "
                if ", I want " in rest:
                    parts = rest.split(", I want ", 1)
                    role = parts[0].strip()
                    remaining = parts[1]
                    if ", so that " in remaining:
                        goal_parts = remaining.split(", so that ", 1)
                        goal = goal_parts[0].strip()
                        benefit = goal_parts[1].strip()
                    else:
                        goal = remaining.strip()
                else:
                    role = rest.strip()
                
                # English string → store in _en fields
                normalized.append({
                    "id": f"US{i + 1:03d}",
                    "role": role,
                    "goal": goal,
                    "benefit": benefit,
                    "role_en": role,
                    "goal_en": goal,
                    "benefit_en": benefit,
                })
            else:
                # Non-English string → store in Chinese fields only
                normalized.append({
                    "id": f"US{i + 1:03d}",
                    "role": story_text[:80],
                    "goal": "",
                    "benefit": "",
                })
        elif isinstance(us, dict):
            if not us.get("id"):
                us["id"] = f"US{i + 1:03d}"
            # If story field exists (old format), parse it
            if isinstance(us.get("story"), str) and not us.get("role"):
                story_text = us.pop("story")
                parsed = _normalize_user_stories([story_text])[0]
                us["role"] = parsed["role"]
                us["goal"] = parsed["goal"]
                us["benefit"] = parsed["benefit"]
                if parsed.get("role_en"):
                    us["role_en"] = parsed["role_en"]
                    us["goal_en"] = parsed["goal_en"]
                    us["benefit_en"] = parsed["benefit_en"]
            normalized.append(us)
        else:
            logger.warning(f"Skipping non-string/non-dict user story: {type(us)}")
    return normalized


def generate_prd(findings: List[Any], analysis_goal: Optional[str] = None, app_name: Optional[str] = None) -> dict:
    system_prompt = _load_system_prompt()
    
    findings_list = []
    for finding in findings:
        if isinstance(finding, dict):
            findings_list.append(finding)
        elif hasattr(finding, "model_dump"):
            findings_list.append(finding.model_dump())
        else:
            findings_list.append(dict(finding))
    
    valid_finding_ids = {str(f.get("finding_id", "")) for f in findings_list if f.get("finding_id")}
    logger.info(f"Generating PRD from {len(findings_list)} findings")
    
    user_message = _build_user_message(findings_list, analysis_goal, app_name)
    response = call_llm(system_prompt, user_message, temperature=0.1, max_tokens=8192)
    
    # Debug: save raw LLM response
    debug_path = Path(__file__).parent.parent / "data" / "debug_raw_prd_response.txt"
    try:
        debug_path.write_text(response, encoding="utf-8")
        logger.info(f"Raw PRD response saved to {debug_path}")
    except Exception as e:
        logger.warning(f"Failed to save debug response: {e}")
    
    prd_data = _parse_prd(response)
    
    if not prd_data:
        logger.error("Failed to parse PRD data")
        return {"error": "Failed to generate PRD"}
    
    # --- Fix 1: Handle 'functional_requirements' as alternative key for 'requirements' ---
    if "functional_requirements" in prd_data and "requirements" not in prd_data:
        logger.info("Using 'functional_requirements' as 'requirements'")
        prd_data["requirements"] = prd_data.pop("functional_requirements")
    
    # --- Fix 2: Normalize requirements (field mapping) ---
    raw_reqs = prd_data.get("requirements", [])
    if isinstance(raw_reqs, list):
        prd_data["requirements"] = _normalize_requirements(raw_reqs)
    elif isinstance(raw_reqs, str):
        logger.warning("requirements is a string, resetting to empty list")
        prd_data["requirements"] = []
    else:
        prd_data["requirements"] = []
    
    # --- Fix 3: Normalize version_plan (object → array) ---
    prd_data["version_plan"] = _normalize_version_plan(prd_data.get("version_plan", []))
    
    # --- Fix 4: Normalize user_stories (strings → objects) ---
    raw_stories = prd_data.get("user_stories", [])
    if isinstance(raw_stories, list):
        prd_data["user_stories"] = _normalize_user_stories(raw_stories)
    elif isinstance(raw_stories, str):
        logger.warning("user_stories is a string, resetting to empty list")
        prd_data["user_stories"] = []
    else:
        prd_data["user_stories"] = []
    
    # --- Fill in defaults for top-level fields ---
    if not prd_data.get("title"):
        prd_data["title"] = f"PRD - {app_name or 'App'} - Review Analysis"
    
    if not prd_data.get("app_name"):
        prd_data["app_name"] = app_name or "Unknown App"
    
    if not prd_data.get("analysis_goal"):
        prd_data["analysis_goal"] = analysis_goal or "General review analysis"
    
    if not prd_data.get("generated_at"):
        prd_data["generated_at"] = datetime.now().isoformat()
    
    if not prd_data.get("supporting_findings"):
        prd_data["supporting_findings"] = list(valid_finding_ids)
    
    # --- Validate and build requirements ---
    req_ids = set()
    valid_requirements = []
    req_counter = 1
    
    logger.info(f"Raw requirements from LLM: {len(prd_data['requirements'])} items")
    if prd_data["requirements"]:
        logger.info(f"First requirement keys: {list(prd_data['requirements'][0].keys()) if isinstance(prd_data['requirements'][0], dict) else type(prd_data['requirements'][0])}")
    
    for req in prd_data["requirements"]:
        if isinstance(req, str):
            logger.warning(f"Skipping requirement string: {req[:50]}...")
            continue
        
        if not _validate_requirement(req, valid_finding_ids, req_ids):
            logger.warning(f"Skipping requirement {req.get('req_id', '?')} - validation failed")
            continue
        
        if not req.get("req_id"):
            req["req_id"] = f"REQ{req_counter:03d}"
            req_counter += 1
        
        if req["req_id"] in req_ids:
            req["req_id"] = f"REQ{req_counter:03d}"
            req_counter += 1
        
        req_ids.add(req["req_id"])
        
        if not req.get("acceptance_criteria"):
            req["acceptance_criteria"] = ["Default acceptance criteria"]
        
        if isinstance(req.get("acceptance_criteria"), str):
            req["acceptance_criteria"] = [req["acceptance_criteria"]]
        
        if not req.get("source_review_ids"):
            req["source_review_ids"] = []
        
        try:
            req_obj = Requirement(**req)
            valid_requirements.append(req_obj)
        except Exception as e:
            logger.error(f"Failed to create Requirement object: {e}")
            logger.debug(f"Raw requirement: {req}")
    
    prd_data["requirements"] = valid_requirements
    
    # --- Validate and build version plans ---
    valid_version_plans = []
    for plan in prd_data["version_plan"]:
        if isinstance(plan, str):
            logger.warning(f"Skipping version plan string: {plan[:50]}...")
            continue
        
        if _validate_version_plan(plan, req_ids):
            try:
                plan_obj = VersionPlan(**plan)
                valid_version_plans.append(plan_obj)
            except Exception as e:
                logger.error(f"Failed to create VersionPlan object: {e}")
                logger.debug(f"Raw version plan: {plan}")
    
    prd_data["version_plan"] = valid_version_plans
    
    # --- Validate and build user stories ---
    valid_user_stories = []
    for us in prd_data["user_stories"]:
        if isinstance(us, str):
            logger.warning(f"Skipping user story string: {us[:50]}...")
            continue
        
        try:
            us_obj = UserStory(**us)
            valid_user_stories.append(us_obj)
        except Exception as e:
            logger.error(f"Failed to create UserStory object: {e}")
            logger.debug(f"Raw user story: {us}")
    
    prd_data["user_stories"] = valid_user_stories
    
    # --- Build final PRD object ---
    try:
        prd_obj = PRDDraft(**prd_data)
        logger.info(f"PRD generated successfully with {len(valid_requirements)} requirements, {len(valid_version_plans)} version plans, {len(valid_user_stories)} user stories")
        
        return {
            "prd_draft": prd_obj,
            "total_findings": len(findings_list),
            "requirements_count": len(valid_requirements),
            "version_plans_count": len(valid_version_plans),
            "user_stories_count": len(valid_user_stories)
        }
    
    except Exception as e:
        logger.error(f"Failed to create PRDDraft object: {e}")
        logger.debug(f"Raw PRD data: {prd_data}")
        return {"error": f"Failed to create PRD object: {str(e)}"}