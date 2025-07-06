from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

llm = init_chat_model("google_genai:gemini-2.0-flash")

class State(TypedDict):
    description: str
    summary: str
    TZ: str
    questions: list

class Feedbakck(BaseModel):
    evaluation: Litaral["enough", "not enough"] = Field(
        description="Decide whether the desctiption is sufficient or not to start the project."
    )