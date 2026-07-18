import json
import re
import time
import logging
from typing import Optional

from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from .config import settings

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        client_kwargs = {"api_key": api_key}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        
        _client = OpenAI(**client_kwargs)
    return _client

def call_llm(system_prompt: str, user_message: str, temperature: float = 0.1, max_retries: int = 3) -> str:
    client = get_client()
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=4096,
                timeout=60,
            )
            
            result = response.choices[0].message.content
            logger.info(f"LLM call succeeded (attempt {attempt + 1})")
            return result if result else ""
            
        except AuthenticationError:
            logger.error("OpenAI API authentication failed. Check your API key.")
            raise
        except RateLimitError:
            wait_time = 2 ** attempt
            logger.warning(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error("Max retries exceeded due to rate limiting")
                raise
        except APIConnectionError:
            wait_time = 2 ** attempt
            logger.warning(f"Connection error. Retrying in {wait_time} seconds...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error("Max retries exceeded due to connection errors")
                raise
        except APIError as e:
            wait_time = 2 ** attempt
            logger.warning(f"API error: {e}. Retrying in {wait_time} seconds...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries exceeded. API error: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM call: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise

def _fix_json_trailing_commas(json_str: str) -> str:
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    return json_str

def parse_json_response(response: str) -> dict:
    if not response or not response.strip():
        return {"error": "invalid_json"}
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    fixed_response = _fix_json_trailing_commas(response)
    
    try:
        return json.loads(fixed_response)
    except json.JSONDecodeError:
        pass
    
    try:
        pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(pattern, fixed_response)
        if match:
            fixed_match = _fix_json_trailing_commas(match.group(1))
            return json.loads(fixed_match)
    except json.JSONDecodeError:
        pass
    
    try:
        pattern = r'```\s*([\s\S]*?)\s*```'
        match = re.search(pattern, fixed_response)
        if match:
            fixed_match = _fix_json_trailing_commas(match.group(1))
            return json.loads(fixed_match)
    except json.JSONDecodeError:
        pass
    
    try:
        start_idx = fixed_response.find("{")
        end_idx = fixed_response.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = fixed_response[start_idx:end_idx + 1]
            fixed_json_str = _fix_json_trailing_commas(json_str)
            return json.loads(fixed_json_str)
    except json.JSONDecodeError:
        pass
    
    logger.error(f"Failed to parse JSON response: {response[:200]}...")
    return {"error": "invalid_json"}