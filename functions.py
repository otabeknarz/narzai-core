from google.genai import Client
from google.genai.types import GenerateContentConfig

from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")


class AgentAI:
    def __init__(self) -> None:
        self.gemini_client = Client(
            api_key=GEMINI_API_KEY
        )

    def gemini_call(self, model: str, user_prompt: str, system_prompt: str) -> str | None:
        return self.gemini_client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        ).text

    def gpt_call(self, model: str, user_prompt: str, system_prompt: str) -> None:
        pass


@lru_cache
def get_agentai() -> AgentAI:
    return AgentAI()

