import re
import time
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from schemas.review import Review

logger = logging.getLogger(__name__)

APPLE_RSS_URL = "https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

MOCK_REVIEWS = [
    {
        "id": "mock-1",
        "app_id": "mock",
        "rating": 5,
        "title": "Great app!",
        "content": "This app is amazing! It helps me stay fit and healthy. The workouts are well designed and easy to follow.",
        "author": "HappyUser",
        "date": datetime.now(),
        "version": "2.1.0",
    },
    {
        "id": "mock-2",
        "app_id": "mock",
        "rating": 4,
        "title": "Good but could be better",
        "content": "Overall a good app. Would love to see more workout options and better tracking features.",
        "author": "Reviewer2",
        "date": datetime.now(),
        "version": "2.0.5",
    },
    {
        "id": "mock-3",
        "app_id": "mock",
        "rating": 3,
        "title": "Average experience",
        "content": "The app works but there are some bugs. Sometimes it crashes during workouts. Hope they fix this soon.",
        "author": "CriticalUser",
        "date": datetime.now(),
        "version": "2.1.0",
    },
    {
        "id": "mock-4",
        "app_id": "mock",
        "rating": 5,
        "title": "Love it!",
        "content": "Best workout app I've tried. The trainers are great and the community is supportive.",
        "author": "FitnessFan",
        "date": datetime.now(),
        "version": "2.1.0",
    },
    {
        "id": "mock-5",
        "app_id": "mock",
        "rating": 1,
        "title": "Terrible",
        "content": "Waste of money. The subscription is too expensive for what you get. Customer support is non-existent.",
        "author": "AngryUser",
        "date": datetime.now(),
        "version": "2.0.0",
    },
]

def extract_app_id(url: str) -> str:
    url = url.strip()
    
    if url.isdigit():
        return url
    
    pattern = r'id(\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    
    raise ValueError(f"无法从 URL 中提取 app_id: {url}")

def fetch_reviews(app_id: str, page: int = 1, limit: int = 50) -> List[dict]:
    url = APPLE_RSS_URL.format(page=page, app_id=app_id)
    logger.info(f"Fetching reviews for app_id={app_id}, page={page}")
    
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=15)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"App not found: {app_id}")
            return []
        logger.error(f"HTTP error: {e}")
        raise
    except httpx.TimeoutException:
        logger.error(f"Request timed out for app_id={app_id}")
        raise
    except Exception as e:
        logger.error(f"Failed to fetch reviews: {e}")
        raise
    
    try:
        data = response.json()
    except ValueError:
        logger.error("Failed to parse JSON response")
        return []
    
    feed = data.get("feed", {})
    entries = feed.get("entry", [])
    
    if not entries:
        logger.info(f"No reviews found for app_id={app_id}, page={page}")
        return []
    
    reviews = []
    for entry in entries[:limit]:
        review = {}
        
        review_id = entry.get("id", {}).get("label", "")
        review["id"] = review_id
        
        review["app_id"] = app_id
        
        rating = entry.get("im:rating", {}).get("label", "")
        review["rating"] = int(rating) if rating.isdigit() else 0
        
        title = entry.get("title", {}).get("label", "")
        review["title"] = title if title else None
        
        content = entry.get("content", {}).get("label", "")
        review["content"] = content
        
        author = entry.get("author", {}).get("name", {}).get("label", "")
        review["author"] = author
        
        date_str = entry.get("updated", {}).get("label", "")
        try:
            review["date"] = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            review["date"] = datetime.now()
        
        version = entry.get("im:version", {}).get("label", "")
        review["version"] = version if version else None
        
        reviews.append(review)
    
    logger.info(f"Fetched {len(reviews)} reviews for app_id={app_id}, page={page}")
    return reviews

def collect_reviews(url: str, max_pages: int = 3, use_mock_data: bool = False) -> List[Review]:
    try:
        app_id = extract_app_id(url)
    except ValueError as e:
        logger.error(f"Invalid URL: {e}")
        raise
    
    if use_mock_data:
        logger.info("Using mock data for testing")
        return [Review(**review) for review in MOCK_REVIEWS]
    
    all_reviews: List[Review] = []
    
    for page in range(1, max_pages + 1):
        try:
            raw_reviews = fetch_reviews(app_id, page=page)
            
            if not raw_reviews:
                if page == 1:
                    logger.info(f"No reviews found for app_id={app_id}")
                break
            
            for raw in raw_reviews:
                try:
                    review = Review(**raw)
                    all_reviews.append(review)
                except Exception as e:
                    logger.warning(f"Failed to create Review object: {e}")
                    continue
            
            if len(raw_reviews) < 50:
                logger.info(f"Less than 50 reviews on page {page}, stopping")
                break
            
            time.sleep(0.7)
            
        except Exception as e:
            logger.error(f"Error fetching page {page}: {e}")
            continue
    
    logger.info(f"Total collected: {len(all_reviews)} reviews for app_id={app_id}")
    return all_reviews