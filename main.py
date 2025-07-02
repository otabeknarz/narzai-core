import json

from ai import get_ai
from handlers import get_agent 

Agent = get_agent()
AI = get_ai()


def main() -> None:
    user_prompt = input("Write your project description: ")
    response = AI.gemini_call_json(model="gemini-2.5-flash", user_prompt=user_prompt, system_prompt=Agent.SYSTEM_PROMPT_START)
    Agent.states = {"first_description": user_prompt}

    dispatcher = {
        "askFromUser": Agent.ask_from_user,
        "makeSummaryOfProject": Agent.make_summary_of_project,
        "makeTZFromSummary": Agent.make_TZ_from_summary, 
        "initializeProject": Agent.initialize_project, 
        "installDependencies": Agent.install_dependencies,
        "writeToFile": Agent.write_to_file,
    }
    loop = True
    while loop:
        response = dispatcher.get(response.get("method", ""), lambda: ...)(params=response.get("params", {}))
        if response.get("method") == "makeSummaryOfProject":
            loop = False


if __name__ == "__main__":
    main()
