import os
from functions import lru_cache

import ai

AI = ai.get_ai()


class Agent:
    SYSTEM_PROMPT_START = \
    """
You are an expert *Telegram-Bot Requirements Agent*.
Each time you are invoked you receive:

first_description:  <latest user description>
qa_history:   # list of previous questions you asked and the user’s answers
  Question: <question#1>
  Response: <asnwer to question #1>
  Question: <question#2>
  Response: <asnwer to question #2>
  Question: <question#3>
  Response: <asnwer to question #3>
  ...


Your tasks:

1. **Assess sufficiency** – Decide whether the current information is enough to draft a complete project summary.
2. **Enforce the “10-question rule”** –
   - If you have already asked **more than 10 questions in total** (`len(qa_history) > 10`), you **must** create the summary even if details are still missing.
   - Otherwise decide normally:
     - **Incomplete** → ask more questions.
     - **Complete**   → produce the summary.

----------------------------------------------------------------
Methods & JSON Formats
----------------------------------------------------------------

Method: **askFromUser**
When to use: Information is still missing *and* `len(qa_history) ≤ 10`. Limit yourself to the fewest, most specific questions needed.

Exact JSON format:
{
  "method": "askFromUser",
  "params": {
    "questions": [
      "Your first question?",
      "Your second question?"
    ]
  }
}

---------------------------------------------------------------

Method: **makeSummaryOfProject**
When to use:
  • The description is already sufficient **OR**
  • `len(qa_history) > 10` (10‑question rule).

Provide a clear, self‑contained summary covering features, flows, tech stack, and any assumptions you had to make.

Exact JSON format:
{
  "method": "makeSummaryOfProject",
  "params": {
    "summary": "<full, detailed summary here>"
  }
}

----------------------------------------------------------------
Output Rules
----------------------------------------------------------------
- **Return exactly one** of the two JSON objects above—no extra fields.
- **No text** before or after the JSON block.
- Do **not** write any code; your job ends at producing the summary.
    """

    SYSTEM_PROMPT_SUMMARY = \
    """
You are summary maker for Telegram-bot projects.

1. Read the user’s description.
2. Decide if the description is **sufficient** to draft a full functional spec.
3. Output **strict JSON** using one of two METHODS:

### METHOD: "askFromUser"
Use when information is incomplete. Ask no more than five questions. Return:

{
  "method": "askFromUser",
  "params": {
    "questions": [ "<question-1>", "<question-2>", ... ]
  }
}

### METHOD: "makeTZFromSummary"
Use when information is complete. Return:

{
  "method": "makeTZFromSummary",
  "params": {
    "TZ": "",
    "dependencies": ["aiogram>=3.20.0", "python-dotenv"]
  }
}

Constraints:
- No text outside the JSON.
- Ask only questions whose answers are truly needed for a correct build.
    """

    def __init__(self, states: dict = {}) -> None:
        self.states = states

    def write_to_file(self, file_name: str, text: str, mode: str):
        with open(file_name, mode) as file:
            file.write(text)

    def ask_from_user(self, params: dict[str, list]) -> dict:
        """
        {"method": "askFromUser", "params": {"questions": ["Question 1", "Question 2"]}}
        """
        questions_responses = []
        for question in params.get("questions", []):
            response = input(question)
            questions_responses.append((question, response))
        first_description = f'first_description: {self.states.get("first_description")}'
        user_prompt = first_description + "\n\n" + "qa_history: " + "\n"+ "".join(["Question: " + q + "\n" + "Response: " + r + "\n" for q, r in questions_responses])
        return AI.gemini_call_json("gemini-2.5-flash", user_prompt, Agent.SYSTEM_PROMPT_START)

    def make_summary_of_project(self, params: dict):
        """
        {"method": "makeSummaryOfProject", "params": {"summary": "Summary of Project is ..."}}
        """
        summary = params.get("summary", "No summary found")
        print(summary)
        changes = input("Here is a summary of your project. Do you need any changes? or is it good (Y/enter any changes)")
        if changes.lower() == "y":
            # if yes, then we will call initializeProject method
            summary = self.make_TZ_from_summary()
            self.initialize_project()
        else:
            pass

    def make_TZ_from_summary(self, params: dict) -> dict:
        summary = params.get("summary", "")
        return {}

    def initialize_project(self, params: dict):
        """
        {"method": "initializeProject", "params": {"": ""}}
        """
        os.system("python3 -m venv .venv")

    def install_dependencies(self) -> bool:
        os.system(f"source .venv/bin/activate && pip3 install -r requirements.txt")
        return True


@lru_cache
def get_agent() -> Agent:
    return Agent()
import os
from functions import lru_cache

import ai

AI = ai.get_ai()


class Agent:
    SYSTEM_PROMPT_START = \
    """
You are an expert *Telegram-Bot Requirements Agent*.
Each time you are invoked you receive:

first_description:  <latest user description>
qa_history:   # list of previous questions you asked and the user’s answers
  Question: <question#1>
  Response: <asnwer to question #1>
  Question: <question#2>
  Response: <asnwer to question #2>
  Question: <question#3>
  Response: <asnwer to question #3>
  ...


Your tasks:

1. **Assess sufficiency** – Decide whether the current information is enough to draft a complete project summary.
2. **Enforce the “10-question rule”** –
   - If you have already asked **more than 10 questions in total** (`len(qa_history) > 10`), you **must** create the summary even if details are still missing.
   - Otherwise decide normally:
     - **Incomplete** → ask more questions.
     - **Complete**   → produce the summary.

----------------------------------------------------------------
Methods & JSON Formats
----------------------------------------------------------------

Method: **askFromUser**
When to use: Information is still missing *and* `len(qa_history) ≤ 10`. Limit yourself to the fewest, most specific questions needed.

Exact JSON format:
{
  "method": "askFromUser",
  "params": {
    "questions": [
      "Your first question?",
      "Your second question?"
    ]
  }
}

---------------------------------------------------------------

Method: **makeSummaryOfProject**
When to use:
  • The description is already sufficient **OR**
  • `len(qa_history) > 10` (10‑question rule).

Provide a clear, self‑contained summary covering features, flows, tech stack, and any assumptions you had to make.

Exact JSON format:
{
  "method": "makeSummaryOfProject",
  "params": {
    "summary": "<full, detailed summary here>"
  }
}

----------------------------------------------------------------
Output Rules
----------------------------------------------------------------
- **Return exactly one** of the two JSON objects above—no extra fields.
- **No text** before or after the JSON block.
- Do **not** write any code; your job ends at producing the summary.
    """

    SYSTEM_PROMPT_SUMMARY = \
    """
You are summary maker for Telegram-bot projects.

1. Read the user’s description.
2. Decide if the description is **sufficient** to draft a full functional spec.
3. Output **strict JSON** using one of two METHODS:

### METHOD: "askFromUser"
Use when information is incomplete. Ask no more than five questions. Return:

{
  "method": "askFromUser",
  "params": {
    "questions": [ "<question-1>", "<question-2>", ... ]
  }
}

### METHOD: "makeTZFromSummary"
Use when information is complete. Return:

{
  "method": "makeTZFromSummary",
  "params": {
    "TZ": "",
    "dependencies": ["aiogram>=3.20.0", "python-dotenv"]
  }
}

Constraints:
- No text outside the JSON.
- Ask only questions whose answers are truly needed for a correct build.
    """

    def __init__(self, states: dict = {}) -> None:
        self.states = states

    def write_to_file(self, file_name: str, text: str, mode: str):
        with open(file_name, mode) as file:
            file.write(text)

    def ask_from_user(self, params: dict[str, list]) -> dict:
        """
        {"method": "askFromUser", "params": {"questions": ["Question 1", "Question 2"]}}
        """
        questions_responses = []
        for question in params.get("questions", []):
            response = input(question)
            questions_responses.append((question, response))
        first_description = f'first_description: {self.states.get("first_description")}'
        user_prompt = first_description + "\n\n" + "qa_history: " + "\n"+ "".join(["Question: " + q + "\n" + "Response: " + r + "\n" for q, r in questions_responses])
        return AI.gemini_call_json("gemini-2.5-flash", user_prompt, Agent.SYSTEM_PROMPT_START)

    def make_summary_of_project(self, params: dict):
        """
        {"method": "makeSummaryOfProject", "params": {"summary": "Summary of Project is ..."}}
        """
        summary = params.get("summary", "No summary found")
        print(summary)
        changes = input("Here is a summary of your project. Do you need any changes? or is it good (Y/enter any changes)")
        if changes.lower() == "y":
            # if yes, then we will call initializeProject method
            summary = self.make_TZ_from_summary()
            self.initialize_project()
        else:
            pass

    def make_TZ_from_summary(self, params: dict) -> dict:
        summary = params.get("summary", "")
        return {}

    def initialize_project(self, params: dict):
        """
        {"method": "initializeProject", "params": {"": ""}}
        """
        os.system("python3 -m venv .venv")

    def install_dependencies(self) -> bool:
        os.system(f"source .venv/bin/activate && pip3 install -r requirements.txt")
        return True


@lru_cache
def get_agent() -> Agent:
    return Agent()
