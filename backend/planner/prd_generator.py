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
        logger.warning(f"Requirement {requirement.get('req_id', 'unknown')} has no source_finding_ids")
        return False
    
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
    response = call_llm(system_prompt, user_message, temperature=0.1)
    
    prd_data = _parse_prd(response)
    
    if not prd_data:
        logger.error("Failed to parse PRD data")
        return {"error": "Failed to generate PRD"}
    
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
    
    if not prd_data.get("user_stories") or isinstance(prd_data["user_stories"], str):
        prd_data["user_stories"] = []
        if isinstance(prd_data.get("user_stories"), str):
            logger.warning("user_stories is a string, resetting to empty list")
    
    if not prd_data.get("requirements") or isinstance(prd_data["requirements"], str):
        prd_data["requirements"] = []
        if isinstance(prd_data.get("requirements"), str):
            logger.warning("requirements is a string, resetting to empty list")
    
    if not prd_data.get("version_plan") or isinstance(prd_data["version_plan"], str):
        prd_data["version_plan"] = []
        if isinstance(prd_data.get("version_plan"), str):
            logger.warning("version_plan is a string, resetting to empty list")
    
    req_ids = set()
    valid_requirements = []
    req_counter = 1
    
    for req in prd_data["requirements"]:
        if isinstance(req, str):
            logger.warning(f"Skipping requirement string: {req[:50]}...")
            continue
        
        if not _validate_requirement(req, valid_finding_ids, req_ids):
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
    
    valid_user_stories = []
    us_counter = 1
    for us in prd_data["user_stories"]:
        if isinstance(us, str):
            logger.warning(f"Skipping user story string: {us[:50]}...")
            continue
        
        if not us.get("id"):
            us["id"] = f"US{us_counter:03d}"
            us_counter += 1
        
        if isinstance(us.get("story"), str):
            parts = us["story"].split(", I want ", 1) if ", I want " in us["story"] else [us["story"], ""]
            role = parts[0].replace("As a ", "").strip() if parts[0].startswith("As a ") else parts[0].strip()
            remaining = parts[1] if len(parts) > 1 else ""
            goal_parts = remaining.split(", so that ", 1) if ", so that " in remaining else [remaining, ""]
            goal = goal_parts[0].strip()
            benefit = goal_parts[1].strip() if len(goal_parts) > 1 else ""
            
            us["role"] = role
            us["goal"] = goal
            us["benefit"] = benefit
        
        try:
            us_obj = UserStory(**us)
            valid_user_stories.append(us_obj)
        except Exception as e:
            logger.error(f"Failed to create UserStory object: {e}")
            logger.debug(f"Raw user story: {us}")
    
    prd_data["user_stories"] = valid_user_stories
    
    try:
        prd_obj = PRDDraft(**prd_data)
        logger.info(f"PRD generated successfully with {len(valid_requirements)} requirements and {len(valid_version_plans)} version plans")
        
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