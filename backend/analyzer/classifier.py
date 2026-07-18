import json
import logging
from pathlib import Path
from typing import List, Optional, Any

from services.openai_client import call_llm, parse_json_response
from schemas.classification import ClassificationResult

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "review_classification.md"
BATCH_SIZE = 20


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


def _build_user_message(reviews: List[dict], analysis_goal: Optional[str] = None) -> str:
    reviews_json = json.dumps(reviews, ensure_ascii=False, indent=2, default=str)
    
    if analysis_goal:
        goal_text = f"\n\n## Analysis Goal\nYour analysis should focus on: {analysis_goal}\n"
    else:
        goal_text = ""
    
    user_message = f"""## User Reviews

Please analyze the following {len(reviews)} user reviews and provide classification results in JSON format:

{reviews_json}

{goal_text}

## Output Requirements

Return ONLY a valid JSON object with classification_results array. Do NOT include any other text or explanation."""
    
    return user_message


def _parse_classification_results(response: str) -> List[dict]:
    parsed = parse_json_response(response)
    
    if "error" in parsed:
        logger.error(f"Failed to parse classification results: {parsed['error']}")
        return []
    
    if isinstance(parsed, list):
        logger.info("Response is a direct list, treating as classification results")
        return parsed
    
    if "classification_results" in parsed:
        results = parsed["classification_results"]
        if isinstance(results, list):
            return results
        logger.error("classification_results is not a list")
        return []
    
    logger.error("classification_results field not found in response")
    logger.debug(f"Response keys: {list(parsed.keys())}")
    return []


def _classify_batch(batch_reviews: List[dict], system_prompt: str, analysis_goal: Optional[str] = None) -> List[ClassificationResult]:
    if not batch_reviews:
        return []
    
    try:
        user_message = _build_user_message(batch_reviews, analysis_goal)
        response = call_llm(system_prompt, user_message, temperature=0.1, max_tokens=8192)
        
        raw_results = _parse_classification_results(response)
        
        classification_results = []
        for result in raw_results:
            try:
                mapped_result = {
                    "review_id": result.get("review_id") or result.get("id", ""),
                    "primary_category": result.get("primary_category") or result.get("category", result.get("topic", "")),
                    "sentiment": result.get("sentiment", "neutral"),
                    "summary": result.get("summary") or result.get("comment", ""),
                    "confidence": result.get("confidence", 0.5),
                    "key_quote": result.get("key_quote") or result.get("quote", result.get("excerpt", ""))
                }
                
                if not mapped_result["review_id"]:
                    logger.warning("Skipping result without review_id")
                    continue
                if not mapped_result["primary_category"]:
                    mapped_result["primary_category"] = "Uncategorized"
                if not mapped_result["summary"]:
                    mapped_result["summary"] = "No summary available"
                
                classification_result = ClassificationResult(**mapped_result)
                classification_results.append(classification_result)
            except Exception as e:
                logger.warning(f"Skipping invalid classification result: {e}")
                logger.debug(f"Invalid result: {result}")
        
        logger.info(f"Classified {len(classification_results)}/{len(batch_reviews)} reviews in this batch")
        return classification_results
    
    except Exception as e:
        logger.error(f"Error classifying batch of {len(batch_reviews)} reviews: {e}")
        return []


def classify_reviews(cleaned_data: List[Any], analysis_goal: Optional[str] = None) -> dict:
    system_prompt = _load_system_prompt()
    
    reviews = []
    for review in cleaned_data:
        if isinstance(review, dict):
            reviews.append(review)
        elif hasattr(review, "model_dump"):
            reviews.append(review.model_dump())
        else:
            reviews.append(dict(review))
    
    total_reviews = len(reviews)
    logger.info(f"Starting classification of {total_reviews} reviews")
    
    batches = [reviews[i:i + BATCH_SIZE] for i in range(0, total_reviews, BATCH_SIZE)]
    logger.info(f"Split into {len(batches)} batches (batch size: {BATCH_SIZE})")
    
    all_classification_results: List[ClassificationResult] = []
    failed_batches = 0
    processed_batches = 0
    
    for i, batch in enumerate(batches):
        logger.info(f"Processing batch {i + 1}/{len(batches)} ({len(batch)} reviews)")
        
        results = _classify_batch(batch, system_prompt, analysis_goal)
        
        if results:
            all_classification_results.extend(results)
            processed_batches += 1
        else:
            failed_batches += 1
            logger.warning(f"Batch {i + 1} failed to produce valid results")
    
    success_rate = (processed_batches / len(batches)) * 100 if batches else 0
    
    logger.info(f"Classification complete: {len(all_classification_results)}/{total_reviews} reviews classified, {success_rate:.1f}% batch success rate")
    
    return {
        "classification_results": all_classification_results,
        "total_reviews": total_reviews,
        "classified_count": len(all_classification_results),
        "batches_processed": processed_batches,
        "batches_failed": failed_batches,
        "success_rate": success_rate
    }