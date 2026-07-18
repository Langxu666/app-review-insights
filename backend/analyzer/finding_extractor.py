import json
import logging
from pathlib import Path
from typing import List, Optional, Any

from services.openai_client import call_llm, parse_json_response
from schemas.finding import Finding

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "finding_extraction.md"


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


def _build_user_message(classification_results: List[dict], analysis_goal: Optional[str] = None) -> str:
    results_json = json.dumps(classification_results, ensure_ascii=False, indent=2, default=str)
    
    if analysis_goal:
        goal_text = f"\n\n## Analysis Goal\nFocus your analysis on: {analysis_goal}\n"
    else:
        goal_text = ""
    
    user_message = f"""## Classified Reviews

Please analyze the following {len(classification_results)} classified reviews and identify recurring issues and meaningful product insights:

{results_json}

{goal_text}

## Output Requirements

Return ONLY a valid JSON object with a 'findings' array. Do NOT include any other text or explanation."""
    
    return user_message


def _parse_findings(response: str) -> List[dict]:
    parsed = parse_json_response(response)
    
    if "error" in parsed:
        logger.error(f"Failed to parse findings: {parsed['error']}")
        return []
    
    if "findings" not in parsed:
        logger.error("findings field not found in response")
        return []
    
    findings = parsed["findings"]
    if not isinstance(findings, list):
        logger.error("findings is not a list")
        return []
    
    return findings


def _validate_finding(finding: dict, valid_review_ids: set) -> bool:
    if not finding.get("supporting_review_ids"):
        logger.warning("Finding has no supporting_review_ids")
        return False
    
    if not isinstance(finding["supporting_review_ids"], list):
        logger.warning("supporting_review_ids is not a list")
        return False
    
    for review_id in finding["supporting_review_ids"]:
        if review_id not in valid_review_ids:
            logger.warning(f"supporting_review_id {review_id} not found in original data")
    
    confidence = finding.get("confidence", 0.5)
    if not (0.0 <= confidence <= 1.0):
        logger.warning(f"Invalid confidence value: {confidence}")
        finding["confidence"] = max(0.0, min(1.0, confidence))
    
    evidence_sufficiency = finding.get("evidence_sufficiency", "limited")
    valid_sufficiency = {"sufficient", "limited", "insufficient"}
    if evidence_sufficiency not in valid_sufficiency:
        logger.warning(f"Invalid evidence_sufficiency: {evidence_sufficiency}")
        finding["evidence_sufficiency"] = "limited"
    
    return True


def extract_findings(classification_results: List[Any], analysis_goal: Optional[str] = None) -> dict:
    system_prompt = _load_system_prompt()
    
    results = []
    for result in classification_results:
        if isinstance(result, dict):
            results.append(result)
        elif hasattr(result, "model_dump"):
            results.append(result.model_dump())
        else:
            results.append(dict(result))
    
    valid_review_ids = {str(r.get("review_id", r.get("id", ""))) for r in results if r.get("review_id") or r.get("id")}
    logger.info(f"Extracting findings from {len(results)} classification results")
    
    user_message = _build_user_message(results, analysis_goal)
    response = call_llm(system_prompt, user_message, temperature=0.1)
    
    raw_findings = _parse_findings(response)
    
    findings_list: List[Finding] = []
    finding_counter = 1
    
    for finding in raw_findings:
        if not _validate_finding(finding, valid_review_ids):
            logger.warning(f"Skipping invalid finding: {finding.get('title', 'Unknown')}")
            continue
        
        if not finding.get("finding_id"):
            finding["finding_id"] = f"F{finding_counter:03d}"
            finding_counter += 1
        else:
            existing_ids = {f.finding_id for f in findings_list}
            if finding["finding_id"] in existing_ids:
                finding["finding_id"] = f"F{finding_counter:03d}"
                finding_counter += 1
        
        if not finding.get("supporting_review_ids"):
            logger.warning(f"Finding {finding['finding_id']} has no supporting reviews")
            continue
        
        if not finding.get("support_count"):
            finding["support_count"] = len(finding.get("supporting_review_ids", []))
        
        if not finding.get("conflicting_evidence"):
            finding["conflicting_evidence"] = []
        
        if not finding.get("assumptions"):
            finding["assumptions"] = []
        
        if not finding.get("uncertainty_notes"):
            finding["uncertainty_notes"] = ""
        
        try:
            finding_obj = Finding(**finding)
            findings_list.append(finding_obj)
            logger.info(f"Added finding: {finding_obj.finding_id} - {finding_obj.title}")
        except Exception as e:
            logger.error(f"Failed to create Finding object: {e}")
            logger.debug(f"Raw finding: {finding}")
    
    logger.info(f"Extracted {len(findings_list)} findings from classification results")
    
    return {
        "findings": findings_list,
        "total_classifications": len(results),
        "extracted_findings": len(findings_list),
        "valid_review_ids": len(valid_review_ids)
    }