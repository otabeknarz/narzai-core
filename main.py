import os
import docker
import time
import uuid

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
from langchain_core.output_parsers.json import JsonOutputParser
from functions import merge_questions, get_username
from dotenv import load_dotenv

from file_tools import FileAgent
from prompts import (
    SYSTEM_PROMPT_START,
    SYSTEM_PROMPT_GENERATE,
    SYSTEM_PROMPT_DESCRIBE,
    SYSTEM_PROMPT_DEBUG
)
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

# State
class OverallState(BaseModel):
    name: str
    project_id: str = str(uuid.uuid4().hex[:8])
    telegram_bot_username: Optional[str] = None
    telegramToken: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    messages: Annotated[list[AnyMessage], add_messages]
    questionsAnswers: Annotated[list[str], merge_questions] = []
    questions: Optional[list[str]] = None
    user_suggestion: Optional[str] = None
    suggestion_summary: Optional[str] = None
    enough: Optional[bool] = False
    is_docker_created: bool = False


def createSummary(state: OverallState) -> Command[Literal["askFromUser", "startProject"]]:
    description = state.description
    qna_text = "\n".join(state.questionsAnswers)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_START),
            ("human",
            f"""
            First description: {description}\n\n
            qa_history : {qna_text}
            """),
        ]
    )

    chain = prompt | llm | parser
    result = chain.invoke({"description": description, "qna_text": qna_text})

    return Command(
        update={
            "enough": result.get("enough"),
            "questions": result.get("questions"),
            "summary": result.get("summary"),
            "TZ": result.get("TZ"),
        },
        goto="startProject" if result.get("enough") is True else "askFromUser",
    )


def askFromUser(state: OverallState) -> OverallState:
    qa_history = state.questionsAnswers or []
    questions = state.questions or []

    print("Your description of the project is not sufficient. Please answer the following questions: ")

    for question in questions:
        answer = input(question + "\n")
        qa_history.append(f"{question} {answer}")

    print("\n\nQuestions finished, thanks for answering\n\n")

    return {"questionsAnswers": qa_history}


def startProject(state: OverallState):
    telegram_token = state.telegramToken
    telegram_bot_username = state.telegram_bot_username
    project_id = state.project_id

    # writing .env file
    file_agent = FileAgent(project_id=project_id, bot_username=telegram_bot_username)
    file_agent.write_to_file(".env/TELEGRAM_BOT_TOKEN", telegram_token)


def generate(state: OverallState) -> None:
    telegram_bot_username = state.telegram_bot_username
    project_id = state.project_id

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_GENERATE),
            ("human",
            f"""
            Description: {state.TZ}
            """),
        ]
    )
    chain = prompt | llm | parser
    code = chain.invoke({"TZ": state.TZ})
    
    print("code:", code)

    # save
    file_agent = FileAgent(project_id=project_id, bot_username=telegram_bot_username)
    for filename, file_content in code.items():
        file_agent.write_to_file(filename.strip(), file_content.strip())
    print("Project files generated successfully.")


def run(state: OverallState) -> Command[Literal["debug", "__end__"]]:
    telegram_bot_username = state.telegram_bot_username
    project_id = state.project_id
        
    project_dir = os.path.abspath(os.path.join("projects", project_id, telegram_bot_username))

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
    logs = get_logs(project_name=telegram_bot_username)
    if logs:
        print("Reading logs...")
        description = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT_DESCRIBE),
                ("human", f"""
                logs : {logs}
                """),
            ]
        )
        chain = description | llm | parser
        result = chain.invoke({"logs": logs})
        
        return Command(
            update={
                "suggestion_summary": result.get("suggestion_summary"),
                "summary": state.summary,
                "is_docker_created": True,
            },
            goto="debug" if result.get("has_errors") else "__end__",
        )

    # feedback = input(f"{telegram_bot_username} is updated! If you like the changes, type (finish)")

    # goto = "debug" if feedback.strip().lower() != "finish" else "__end__"

    return Command(
        update={
            "summary": result.get("summary"),
            "TZ": result.get("TZ"),
            "is_docker_created": True,
        },
        goto=goto,
    )


def debug(state: OverallState):
    telegram_bot_username = state.telegram_bot_username
    project_id = state.project_id

    logs = get_logs(project_name=telegram_bot_username)
    suggestion_summary = state.suggestion_summary
    user_suggestion = state.user_suggestion

    qna_text = "\n".join(state.questionsAnswers)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT_DEBUG),
            ("human", f"""
            logs : {logs}
            suggestion_summary: {suggestion_summary}
            user_suggestion: {user_suggestion}
            """),
        ]
    )

    chain = prompt | llm | parser
    result = chain.invoke({"qna_text": qna_text})
    print(result)

    # read files and copy into code
    file_agent = FileAgent(project_id=project_id, bot_username=telegram_bot_username)
    code = {}
    for filename in file_agent.get_project_structure().keys():
        code[filename] = file_agent.read_file(filename)

    return Command(
        update={
            "questions": result.get("questions"),
            "summary": result.get("summary"),
            "TZ": result.get("TZ"),
            "is_docker_created": True,
        },
        goto="generate",
    )


# Build the state graph
builder = StateGraph(OverallState)
builder.add_node(createSummary)
builder.add_node(askFromUser)
builder.add_node(startProject)
builder.add_node(generate)
builder.add_node(debug)
builder.add_node(run)

builder.add_edge(START, "createSummary")
builder.add_edge("askFromUser", "createSummary")
builder.add_edge("startProject", "generate")
builder.add_edge("generate", "run")
builder.add_edge("debug", "run") 
builder.add_edge("run", END)
graph = builder.compile()

if __name__ == "__main__":
    print("Hey, I am Bot Builder and I am here to help you to build your bot! To start, you need to give me some information. \n ")
    name = input("What is the name of the project? \n\n")
    description = input("\n\nGive me the description of the project. Include the workflow of the bot, the required information that bot needs to collect, and main objective of the bot. The more details you provide, the better results you will receive. \n\n")


    telegram_token = input("\n\nPlease, provide Telegram Bot token? \n\n")
    telegram_bot_username = get_username(telegram_token)

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
