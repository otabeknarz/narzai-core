import os
import docker
import time
import requests

from langchain.chat_models import init_chat_model
from pydantic import BaseModel


from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated, Optional
from langgraph.types import Command
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import Literal
from prompts import (
    SYSTEM_PROMPT_START,
    SYSTEM_PROMPT_GENERATE,
    SYSTEM_PROMPT_WRITE_CODE,
)
from langchain_core.output_parsers.json import JsonOutputParser
from functions import merge_questions, get_username
from dotenv import load_dotenv

from docker_client import (
    initialize_project,
    run_project,
    stop_project,
    restart_project,
    get_logs,
)

load_dotenv()

# LLM
llm = init_chat_model("google_genai:gemini-2.0-flash")
parser = JsonOutputParser()
docker_client = docker.from_env()


# The overall state of the graph (this is the public state shared across nodes)
class OverallState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    name: str
    telegram_bot_username: Optional[str] = ""
    description: Optional[str] = None
    telegramToken: Optional[str] = None
    enough: Optional[bool] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    fullCode: Optional[dict] = None
    questionsAnswers: Annotated[list[str], merge_questions] = []
    questions: Optional[list[str]] = None
    is_docker_created: bool = False
    problem_from_user: Optional[str] = None
    problem_summary: Optional[str] = None
    finished: Optional[str] = None


def createSummary(
    state: OverallState,
) -> Command[Literal["askFromUser", "startProject"]]:
    description = state.description
    qna_text = "\n".join(state.questionsAnswers)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_START),
            (
                "human",
                f"""
First description: {description}\n\n
qa_history : {qna_text}
        """,
            ),
        ]
    )

    # print(prompt)

    chain = prompt | llm | parser
    result = chain.invoke({"description": description, "qna_text": qna_text})
    # print("Raw LLM output:", result)

    if result.get("enough") is True:
        goto = "startProject"
    else:
        goto = "askFromUser"

    return Command(
        update={
            "enough": result.get("enough"),
            "questions": result.get("questions"),
            "summary": result.get("summary"),
            "TZ": result.get("TZ"),
        },
        goto=goto,
    )


def askFromUser(state: OverallState):
    qa_history = state.questionsAnswers or []
    questions = state.questions or []

    print(
        "Your description of the project is not sufficient. Please answer the following questions: "
    )

    for question in questions:
        answer = input(question + "\n")
        qa_history.append(f"{question} {answer}")

    print("\n\nQuesitons finished, thanks for asnwering\n\n")

    return {"questionsAnswers": qa_history}


def startProject(state: OverallState):
    project_name = state.name
    telegram_token = state.telegramToken
    telegram_bot_username = state.telegram_bot_username

    project_dir = os.path.abspath(f"projects/{telegram_bot_username}")
    print(f"Creating project files in {str(telegram_bot_username)} directory")
    os.makedirs(project_dir, exist_ok=True)

    env_path = os.path.join(project_dir, ".env")
    print("Writing .env")
    with open(env_path, "w") as f:
        f.write(f"TELEGRAM_BOT_TOKEN={telegram_token}\n")


def generateCode(state: OverallState) -> dict:
    TZ = state.TZ

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_GENERATE),
            (
                "human",
                f"""
        Description: {TZ}
        """,
            ),
        ]
    )
    chain = prompt | llm | parser
    fullCode = chain.invoke({"TZ": TZ})
    return {"fullCode": fullCode}


def save(state: OverallState):
    code = state.fullCode if state.fullCode else {}

    # we gotta be more restrictive here
    # for example user can but symbols here, our program generates files with that name
    # could be error when generating files or directories with extra symbols as their names
    project_dir = os.path.abspath(
        os.path.join("projects", str(state.telegram_bot_username))
    )

    for filename, file_content in code.items():
        clean_name = filename.strip()
        file_path = os.path.join(project_dir, clean_name)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        print(f"Writing file: {file_path}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content.strip())


def run(state: OverallState) -> Command:
    telegram_bot_username = str(state.telegram_bot_username)
    project_dir = os.path.abspath(os.path.join("projects", telegram_bot_username))

    # Install deps
    print("Creating virtual environment")
    if not state.is_docker_created:
        image = initialize_project(
            project_path=project_dir, project_name=telegram_bot_username
        )
        container = run_project(
            project_name=telegram_bot_username, env_file=project_dir.join(".env")
        )
    else:
        container = restart_project(
            project_name=telegram_bot_username,
            has_changes=True,
            project_path=project_dir,
        )

    time.sleep(3)
    logs = get_logs(telegram_bot_username)
    message = f"""
Here is the logs of docker container that running telegram bot in python (aiogram)
is logs fine or is there any error
GIVE THE RESULT STRICT JSON FORMAT WITH FIELD need_to_debug: bool, problem_summary: str
{logs}
"""
    qna_text = "\n".join(state.questionsAnswers)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", message),
            (
                "human",
                f"""
qa_history : {qna_text}
        """,
            ),
        ]
    )
    state.is_docker_created = True

    # print(prompt)

    chain = prompt | llm | parser
    result = chain.invoke({"qna_text": qna_text})
    if result.get("need_to_debug"):
        print(
            f"I can see the error in the logs, i'm fixing it\n{result.get('problem_summary')}"
        )
        return Command(
            update={
                "problem_summary": result.get("problem_summary"),
                "questions": result.get("questions"),
                "summary": result.get("summary"),
                "TZ": result.get("TZ"),
                "is_docker_created": True,
            },
            goto="debug",
        )

    first_feedback_or_finish = input(
        f"So your bot {telegram_bot_username} is working check it and ask me any updates or errors\nIf everything is ok just type (finish)"
    )
    goto = "debug"
    if first_feedback_or_finish.strip().lower() == "finish":
        goto = "finish"

    return Command(
        update={
            "problem_from_user": first_feedback_or_finish,
            "questions": result.get("questions"),
            "summary": result.get("summary"),
            "TZ": result.get("TZ"),
            "is_docker_created": True,
        },
        goto=goto,
    )


def debug(state: OverallState):  # debugging the existing code
    project_name = str(state.telegram_bot_username)
    logs = get_logs(project_name=project_name)
    problem_from_user = state.problem_from_user or ""
    problem_summary = state.problem_summary or ""

    qna_text = "\n".join(state.questionsAnswers)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_WRITE_CODE),
            (
                "human",
                f"""
qa_history : {qna_text}
logs : {logs}
problem_summary (may be blank) : {problem_summary}
info from user (may be blank) : {problem_from_user}
        """,
            ),
        ]
    )

    # print(prompt)

    chain = prompt | llm | parser
    result = chain.invoke({"qna_text": qna_text})
    print(result)
    return {"fullCode": result}


# Build the state graph
builder = StateGraph(OverallState)
builder.add_node(createSummary)
builder.add_node(askFromUser)
builder.add_node(startProject)
builder.add_node(generateCode)
builder.add_node(debug)  # added debug node
builder.add_node(save)
builder.add_node(run)

builder.add_edge(START, "createSummary")
builder.add_edge("askFromUser", "createSummary")
builder.add_edge("startProject", "generateCode")
builder.add_edge("generateCode", "save")
builder.add_edge("save", "run")
builder.add_edge(
    "debug", "save"
)  # if debug is triggered, after debugging we run the bot directly for loop effect
builder.add_edge("run", END)
graph = builder.compile()

if __name__ == "__main__":
    print(
        "Hey, I am Bot Builder and I am here to help you to build your bot! To start, you need to give me some information. \n "
    )
    name = input("What is the name of the project? \n\n")
    description = input(
        "\n\nGive me the description of the project. Include the workflow of the bot, the required information that bot needs to collect, and main objective of the bot. The more details you provide, the better results you will receive. \n\n"
    )

    telegram_token = None
    telegram_bot_username = None
    while not telegram_token or not telegram_bot_username:
        telegram_token = input("\n\nPlease, provide Telegram Bot token? \n\n")
        response = requests.get(f"https://api.telegram.org/bot{telegram_token}/getMe")

        if response.status_code == 200:
            telegram_bot_username = response.json().get("result", {}).get("username")

    result = graph.invoke(
        {
            "name": name,
            "description": description,
            "telegramToken": telegram_token,
            "telegram_bot_username": telegram_bot_username,
            "questions": [],
        }
    )
    for message in result["messages"]:
        message.pretty_print()

    with open("state_graph.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
    print("Graph Image generated.")


"""
Example prompt:
name:
elephant image gen bot
description:
 The bot needs to generate or find image of elephant from public source and send to user after they press /start or write any text or send any signal in general. No matter what bot should reply with random elephant picture
bot_token: 5845005240:AAEp-dcOK9WhORoOTPmFjhMaJ12iyshHz6E (i am gonna revoke it anyway. github guys, don't get excited)
bot username: @credentis_bot
"""
