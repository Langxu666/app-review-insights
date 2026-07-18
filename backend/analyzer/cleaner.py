import re
import logging
from typing import List, Dict
from datetime import datetime

from schemas.review import Review

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 5000
MIN_CONTENT_LENGTH = 2

def deduplicate_reviews(reviews: List[Review]) -> List[Review]:
    seen = set()
    unique_reviews = []
    
    for review in reviews:
        key = (review.content.strip(), review.author.strip())
        if key not in seen:
            seen.add(key)
            unique_reviews.append(review)
    
    removed = len(reviews) - len(unique_reviews)
    logger.info(f"去重完成: 移除 {removed} 条重复评论, 保留 {len(unique_reviews)} 条")
    return unique_reviews

def is_valid_content(content: str) -> bool:
    if not content or not content.strip():
        return False
    
    content = content.strip()
    
    if len(content) < MIN_CONTENT_LENGTH:
        return False
    
    if re.match(r'^[\s\W_]*$', content):
        return False
    
    if re.match(r'^[\u200b\uFEFF\s]*$', content):
        return False
    
    return True

def truncate_content(content: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."

def normalize_date(date_value):
    if isinstance(date_value, datetime):
        return date_value
    
    if isinstance(date_value, str):
        date_str = date_value.strip()
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    
    return datetime.now()

def normalize_reviews(reviews: List[Review]) -> List[Review]:
    normalized = []
    
    for review in reviews:
        content = review.content or ""
        content = content.strip()
        
        if not is_valid_content(content):
            continue
        
        content = truncate_content(content)
        
        normalized_review = Review(
            id=review.id,
            app_id=review.app_id,
            rating=review.rating,
            title=review.title.strip() if review.title else None,
            content=content,
            author=review.author.strip() if review.author else "Anonymous",
            date=normalize_date(review.date),
            version=review.version.strip() if review.version else None,
        )
        
        normalized.append(normalized_review)
    
    logger.info(f"标准化完成: 移除 {len(reviews) - len(normalized)} 条无效评论, 保留 {len(normalized)} 条")
    return normalized

def clean_reviews(reviews: List[Review]) -> Dict:
    original_count = len(reviews)
    
    deduplicated = deduplicate_reviews(reviews)
    removed_duplicates = original_count - len(deduplicated)
    
    cleaned_data = normalize_reviews(deduplicated)
    removed_empty = len(deduplicated) - len(cleaned_data)
    
    final_count = len(cleaned_data)
    
    logger.info(f"清洗完成: 原始 {original_count} -> 去重 {len(deduplicated)} -> 最终 {final_count}")
    
    return {
        "cleaned_data": cleaned_data,
        "removed_duplicates": removed_duplicates,
        "removed_empty": removed_empty,
        "final_count": final_count,
    }