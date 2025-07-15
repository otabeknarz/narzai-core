import os
import subprocess
import sys
import docker
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
from prompts import SYSTEM_PROMPT_START, SYSTEM_PROMPT_GENERATE
from langchain_core.output_parsers.json import JsonOutputParser
from functions import merge_questions, get_username
from dotenv import load_dotenv
load_dotenv()

# LLM
llm = init_chat_model("google_genai:gemini-2.0-flash")
parser = JsonOutputParser()
docker_client = docker.from_env()



# The overall state of the graph (this is the public state shared across nodes)
class OverallState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    name: str 
    description: Optional[str] = None
    telegramToken: Optional[str] = None
    enough: Optional[bool] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    fullCode: Optional[dict] = None 
    questionsAnswers: Annotated[list[str], merge_questions] = []
    questions: Optional[list[str]] = None
    finished: Optional[str] = None

def createSummary(state: OverallState) -> Command[Literal["askFromUser", "startProject"]]: 
    description = state.description
    qna_text = "\n".join(state.questionsAnswers)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_START),
        ("human", f"""
        First description: {description}\n\n
        qa_history : {qna_text}
        """),
    ])

    # print(prompt)

    chain = prompt | llm | parser
    result = chain.invoke({"description": description, "qna_text": qna_text})
    # print("Raw LLM output:", result)

    print(result.get("enough"))
    if result.get("enough")==True:
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

    print("Your description of the project is not sufficient. Please answer the following questions: ")

    for question in questions:
        answer = input(question + "\n")
        qa_history.append(f"{question} {answer}")

    print("\n\nQuesitons finished, thanks for asnwering\n\n")

    return {"questionsAnswers": qa_history}


def startProject(state: OverallState):
    project_name = state.name 
    telegram_token = state.telegramToken

    project_dir = os.path.abspath(f"projects/{project_name}")
    print(f"Creating project files in {str(project_dir)} directory")
    os.makedirs(project_dir, exist_ok=True)

    env_path = os.path.join(project_dir, '.env')
    print("Writing .env")
    with open(env_path, 'w') as f:
        f.write(f"TELEGRAM_BOT_TOKEN={telegram_token}\n")

    # Create venv
    venv_path = os.path.join(project_dir, 'venv')
    print(f"Creating virtual environment using {sys.executable}")
    try:
        subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Venv creation failed: {e}")
        raise
    

def generateCode(state: OverallState) -> OverallState:
    TZ = state.TZ

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_GENERATE),
        ("human", f"""
        Description: {TZ}
        """),
    ])
    print(TZ)
    chain = prompt | llm | parser
    fullCode = chain.invoke({"TZ": TZ})
    print("LLM response:", fullCode)
    print(type(fullCode))
    return {"fullCode" : fullCode}

def save(state: OverallState) -> OverallState: 
    code = state.fullCode 
    project_name = get_username(state.telegramToken)
        
    # we gotta be more restrictive here 
    # for example user can but symbols here, our program generates files with that name
    # could be error when generating files or directories with extra symbols as their names
    project_dir = os.path.abspath(os.path.join("projects", project_name))

    
    for filename, file_content in code.items():
        clean_name = filename.strip()
        file_path = os.path.join(project_dir, clean_name)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        print(f"Writing file: {file_path}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content.strip())
 

def run(state: OverallState) -> OverallState:
    project_name = state.name
    project_dir = os.path.abspath(os.path.join("projects", project_name))
    venv_path = os.path.join(project_dir, 'venv')
    entrypoint = os.path.join(project_dir, 'main.py')

    # Install deps
    pip_exec = os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin', 'pip')
    if not os.path.isfile(pip_exec+'.exe'):
        print(f"Pip executable not found in venv at {pip_exec}")
        return {'status': 'error', 'logs': 'pip not found in venv'}
    print(f"Installing dependencies using {pip_exec}")
    proc = subprocess.run([pip_exec, 'install', '-r', os.path.abspath(f"projects/{project_name}/requirements.txt")], capture_output=True, text=True)
    print(f"Pip install stdout: {proc.stdout}")
    print(f"Pip install stderr: {proc.stderr}")
    
    # Determine venv python executable
    py_exec = os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin', 'python')
    if not os.path.isfile(py_exec+'.exe'):
        print(f"Python executable not found in venv at {py_exec}")
        return {'status': 'error', 'logs': 'python not found in venv'}
    cmd = [py_exec, entrypoint]
    print(f"Running bot locally: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Bot stdout: {proc.stdout}")
    print(f"Bot stderr: {proc.stderr}")

    needs_debug = input("Do you need to debug the bot? (yes/no) ").strip().lower() == 'yes'
    goto = "run"
    if needs_debug:
        goto = "debug"
        
    return Command(
        update={
            "debug": needs_debug,
            "questions": result.get("questions"),
            "summary": result.get("summary"),
            "TZ": result.get("TZ"),
        },
        goto=goto,
    )


def debug(state: OverallState) -> OverallState: # debugging the existing code
    code = state.fullCode
    print("Debugging the following code:")
    # UNFINISHED


# Build the state graph
builder = StateGraph(OverallState)
builder.add_node(createSummary) 
builder.add_node(askFromUser) 
builder.add_node(startProject) 
builder.add_node(generateCode)
builder.add_node(debug) # added debug node
builder.add_node(save)
builder.add_node(run)

builder.add_edge(START, "createSummary")
builder.add_edge("askFromUser", "createSummary")
builder.add_edge("startProject", "generateCode")
builder.add_edge("generateCode", "save")
builder.add_edge("save", "run")
builder.add_edge("debug", "run") # if debug is triggered, after debugging we run the bot directly for loop effect
builder.add_edge("run", END)
graph = builder.compile()

if __name__ == "__main__":
    print("Hey, I am Bot Builder and I am here to help you to build your bot! To start, you need to give me some information. \n ")
    name = input("What is the name of the project? \n\n")
    description = input("\n\nGive me the description of the project. Include the workflow of the bot, the required information that bot needs to collect, and main objective of the bot. The more details you provide, the better results you will receive. \n\n")
    telegram_token = input("\n\nPlease, provide Telegram Bot token? \n\n")
    result = graph.invoke({"name": name, "description": description, "telegramToken": telegram_token, "questions": [],})
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
