import requests


def merge_questions(existing: list[str], new: list[str]) -> list[str]:
    return existing + new


def get_username(telegram_token: str) -> str:
    try:
        response = requests.get(f"https://api.telegram.org/bot{telegram_token}/getMe")
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json().get("result", {}).get("username", "user")
    except requests.RequestException as e:
        print("Error fetching Telegram username:", e)
        return get_username(input("Telegram bot is not available, please provide a valid bot token to continue:"))
