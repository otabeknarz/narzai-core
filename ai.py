from google.genai import Client
from google.genai.types import GenerateContentConfig, GenerateContentResponse
import json
import re

from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")


def get_cleaned_dict(raw: str) -> dict:
    raw_clean = re.sub(r"^```json|```$", "", raw.strip(), flags=re.IGNORECASE).strip()
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError:
        raw_clean = raw_clean.replace("'", '"')
        return json.loads(raw_clean)


class AI:
    def __init__(self) -> None:
        self.gemini_client = Client(
            api_key=GEMINI_API_KEY
        )

    def gemini_call(self, model: str, user_prompt: str, system_prompt: str) -> GenerateContentResponse:
        return self.gemini_client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )

    def gemini_call_json(self, model: str, user_prompt: str, system_prompt: str) -> dict:
        response = self.gemini_call(model, user_prompt, system_prompt)
        json_response = get_cleaned_dict(response.text or "{}")
        return json_response


    def gpt_call(self, model: str, user_prompt: str, system_prompt: str) -> None:
        pass


@lru_cache
def get_ai() -> AI:
    return AI()

