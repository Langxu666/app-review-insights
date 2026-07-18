"""
Debug script: Test JSON parsing and findings extraction with raw LLM output.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from services.openai_client import call_llm, parse_json_response, _fix_json_trailing_commas, _fix_truncated_json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def main():
    # Load classification results
    with open(os.path.join(DATA_DIR, "test_classification_results.json"), "r", encoding="utf-8") as f:
        classification_results = json.load(f)

    print(f"Loaded {len(classification_results)} classification results")

    # Load the finding extraction prompt
    from pathlib import Path
    PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "finding_extraction.md"
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_content = f.read()

    # Extract system prompt
    system_prompt_start = prompt_content.find("## System Prompt")
    output_format_start = prompt_content.find("## Output Format")
    system_prompt = prompt_content[system_prompt_start:output_format_start].replace("## System Prompt", "").strip()

    # Build user message
    results_json = json.dumps(classification_results, ensure_ascii=False, indent=2)
    user_message = f"""## Classified Reviews

Please analyze the following {len(classification_results)} classified reviews and identify recurring issues and meaningful product insights:

{results_json}

## Analysis Goal
Focus your analysis on: Identify user pain points, feature requests, and bug reports for product improvement

## Output Requirements

Return ONLY a valid JSON object with a 'findings' array. Do NOT include any other text or explanation."""

    print("Calling LLM for findings extraction...")
    response = call_llm(system_prompt, user_message, temperature=0.1)

    # Save raw response for debugging
    raw_path = os.path.join(DATA_DIR, "debug_raw_findings_response.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(response)
    print(f"Raw response saved to {raw_path}")
    print(f"Response length: {len(response)} chars")
    print(f"Response preview: {response[:300]}...")

    # Try parsing
    print("\n--- Testing parse_json_response ---")
    parsed = parse_json_response(response)
    print(f"Parsed type: {type(parsed).__name__}")
    print(f"Parsed keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'N/A'}")

    if "error" in parsed:
        print(f"PARSE ERROR: {parsed['error']}")
        # Try manual debugging
        print("\n--- Manual Debug ---")
        # Check if it's valid JSON
        try:
            result = json.loads(response)
            print("  json.loads SUCCESS: type =", type(result).__name__)
        except json.JSONDecodeError as e:
            print(f"  json.loads FAILED: {e}")
            # Show context around error
            pos = e.pos
            start = max(0, pos - 50)
            end = min(len(response), pos + 50)
            print(f"  Context around error position {pos}:")
            print(f"  ...{repr(response[start:end])}...")

        # Try with trailing comma fix
        fixed = _fix_json_trailing_commas(response)
        try:
            result = json.loads(fixed)
            print("  After _fix_json_trailing_commas: SUCCESS")
        except json.JSONDecodeError as e:
            print(f"  After _fix_json_trailing_commas: FAILED at pos {e.pos}")

        # Try with truncation fix
        truncated = _fix_truncated_json(fixed)
        try:
            result = json.loads(truncated)
            print("  After _fix_truncated_json: SUCCESS")
        except json.JSONDecodeError as e:
            print(f"  After _fix_truncated_json: FAILED at pos {e.pos}")
            print(f"  Context: ...{repr(truncated[max(0,e.pos-30):min(len(truncated),e.pos+30)])}...")

        # Check for unescaped characters
        for i, ch in enumerate(response):
            if ch == '\n' or ch == '\r' or ch == '\t':
                pass  # normal
            elif ord(ch) < 32 and ch not in '\n\r\t':
                print(f"  Found control char at pos {i}: ord={ord(ch)}")

        # Check for unescaped quotes in strings
        in_string = False
        escape_next = False
        for i, ch in enumerate(response):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
        if in_string:
            print("  WARNING: Unclosed string (odd number of quotes)")

    else:
        print("Parsing SUCCESS!")
        findings = parsed.get("findings", [])
        print(f"Found {len(findings)} findings")
        for f in findings:
            print(f"  - [{f.get('severity', '?')}] {f.get('title', '?')}")


if __name__ == "__main__":
    main()