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

def call_llm(system_prompt: str, user_message: str, temperature: float = 0.1, max_retries: int = 3, max_tokens: int = 4096) -> str:
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
                max_tokens=max_tokens,
                timeout=180,
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


def _fix_unescaped_strings(json_str: str) -> str:
    """Fix unescaped newlines and control characters within JSON string values.
    
    This handles the common LLM issue where review text containing newlines
    is not properly escaped in the generated JSON.
    """
    result = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(json_str):
        ch = json_str[i]
        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == '\\':
            result.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"':
            result.append(ch)
            in_string = not in_string
            i += 1
            continue
        if in_string and ch == '\n':
            result.append('\\n')
        elif in_string and ch == '\r':
            result.append('\\r')
        elif in_string and ch == '\t':
            result.append('\\t')
        elif in_string and ord(ch) < 0x20:
            result.append(f'\\u{ord(ch):04x}')
        else:
            result.append(ch)
        i += 1
    return ''.join(result)


def _fix_truncated_json(json_str: str) -> str:
    """Fix truncated JSON by tracking string state and closing incomplete structures.
    
    Unlike simple character counting, this tracks whether we're inside a string
    to avoid { and [ characters in review text corrupting the brace count.
    """
    # Track nesting state properly (accounting for strings)
    in_string = False
    escape_next = False
    open_braces = 0
    open_brackets = 0
    
    for ch in json_str:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\':
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == '{':
                open_braces += 1
            elif ch == '}':
                open_braces -= 1
            elif ch == '[':
                open_brackets += 1
            elif ch == ']':
                open_brackets -= 1
    
    # Close any open string
    if in_string:
        json_str += '"'
    
    # Remove trailing comma before closing
    json_str = json_str.rstrip()
    if json_str.endswith(','):
        json_str = json_str[:-1].rstrip()
    
    # Close open structures
    json_str += ']' * max(0, open_brackets)
    json_str += '}' * max(0, open_braces)
    
    return json_str

def parse_json_response(response: str) -> dict:
    if not response or not response.strip():
        return {"error": "invalid_json"}
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Fix unescaped control characters in JSON strings
    fixed_response = _fix_unescaped_strings(response)
    
    try:
        return json.loads(fixed_response)
    except json.JSONDecodeError:
        pass
    
    fixed_response = _fix_json_trailing_commas(fixed_response)
    
    try:
        return json.loads(fixed_response)
    except json.JSONDecodeError:
        pass
    
    truncated_fixed = _fix_truncated_json(fixed_response)
    try:
        return json.loads(truncated_fixed)
    except json.JSONDecodeError:
        pass
    
    try:
        pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(pattern, fixed_response)
        if match:
            fixed_match = _fix_json_trailing_commas(match.group(1))
            truncated_fixed_match = _fix_truncated_json(fixed_match)
            return json.loads(truncated_fixed_match)
    except json.JSONDecodeError:
        pass
    
    try:
        pattern = r'```\s*([\s\S]*?)\s*```'
        match = re.search(pattern, fixed_response)
        if match:
            fixed_match = _fix_json_trailing_commas(match.group(1))
            truncated_fixed_match = _fix_truncated_json(fixed_match)
            return json.loads(truncated_fixed_match)
    except json.JSONDecodeError:
        pass
    
    try:
        start_idx = fixed_response.find("{")
        end_idx = fixed_response.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = fixed_response[start_idx:end_idx + 1]
            fixed_json_str = _fix_json_trailing_commas(json_str)
            truncated_fixed_json_str = _fix_truncated_json(fixed_json_str)
            return json.loads(truncated_fixed_json_str)
    except json.JSONDecodeError:
        pass
    
    logger.error(f"Failed to parse JSON response: {response[:200]}...")
    return {"error": "invalid_json"}