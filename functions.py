import json
import re

def merge_questions(existing: list[str], new: list[str]) -> list[str]:
    return existing + new

def get_cleaned_dict(raw: str) -> dict:
    raw_clean = re.sub(r"^```json|```$", "", raw.strip(), flags=re.IGNORECASE).strip()
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError:
        raw_clean = raw_clean.replace("'", '"')
        return json.loads(raw_clean)