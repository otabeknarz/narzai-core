import json
import re
import requests

def merge_questions(existing: list[str], new: list[str]) -> list[str]:
    return existing + new

# def get_cleaned_dict(raw: str) -> dict: # we don't use this function anymore, but i left it live
#     raw_clean = re.sub(r"^```json|```$", "", raw.strip(), flags=re.IGNORECASE).strip()
#     try:
#         return json.loads(raw_clean)
#     except json.JSONDecodeError:
#         raw_clean = raw_clean.replace("'", '"')
#         return json.loads(raw_clean)
    
# def get_cleaned_project_name(raw: str) -> str:
#     raw_clean = re.sub(r"[^\w]", " ", raw.strip()).split()
#     return "_".join(raw_clean)

def get_username(telegram_token: str) -> str:
    try:
        response = requests.get(f"https://api.telegram.org/bot{telegram_token}/getMe")
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json().get("result", {}).get("username", "user")
    except requests.RequestException as e:
        print("Error fetching Telegram username:", e)
        return get_username(input("Telegram bot is not available, please provide a valid bot token to continue:"))
