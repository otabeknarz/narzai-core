import os
import shutil
import subprocess
import sys
from dotenv import load_dotenv
load_dotenv()

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
import re
import json

# LLM
llm = init_chat_model("google_genai:gemini-2.0-flash")
parser = JsonOutputParser()

def merge_questions(existing: list[str], new: list[str]) -> list[str]:
    return existing + new

def get_cleaned_dict(raw: str) -> dict:
    raw_clean = re.sub(r"^```json|```$", "", raw.strip(), flags=re.IGNORECASE).strip()
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError:
        raw_clean = raw_clean.replace("'", '"')
        return json.loads(raw_clean)

# The overall state of the graph (this is the public state shared across nodes)
class OverallState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    name: str
    description: Optional[str] = None
    telegram_token: Optional[str] = None
    enough: Optional[bool] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    questionsAnswers: Annotated[list[str], merge_questions] = []
    questions: Optional[list[str]] = None
    finished: Optional[bool] = None

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

def startProject(state: OverallState): # UNFINISHED
    final_message = f"Project started! Summary:\n\n{state.summary} \n\n TZ: {state.TZ}"
    print("Project Started")
    return Command(
        update={
            "messages": state.messages + [AIMessage(content=final_message)],
            "finished": True
        }
    )

# Generates codes
def generateCode(TZ: str) -> str:

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_GENERATE),
        ("human", f"""
        Description: {TZ}
        """),
    ])
    print(TZ)
    chain = prompt | llm | parser
    response = chain.invoke({"TZ": TZ})
    print("LLM response:", response)
    print(type(response))
    return response

def save(code: dict, project_name: str, telegram_token: str) -> str: # UNFINISHED
    project_dir = os.path.abspath(f"projects/{project_name}")
    print(f"Creating project files in {str(project_dir)} directory")
    os.makedirs(project_dir, exist_ok=True)

    # Write .env
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


    # Write code files
    print("Parsing and writing code files from LLM output")
    
    entrypoint = None
    for filename, file_content in code.items():
        # Clean up the filename and figure out where to save it
        clean_name = filename.strip()
        file_path = os.path.join(project_dir, clean_name)

        # Make sure the folder exists before writing the file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save the code into the file
        print(f"Writing file: {file_path}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content.strip())

        # Remember the entrypoint 
        if clean_name.endswith(("main.py")):
            entrypoint = file_path
    return venv_path, entrypoint

def run(venv_path: str, entrypoint: str, project_name: str) -> dict: #UNFINISHED
    # Install deps
    pip_exec = os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin', 'pip')
    print(f"Installing dependencies using {pip_exec}")
    proc = subprocess.run([pip_exec, 'install', '-r', os.path.abspath(f"projects/{project_name}/requirements.txt")], capture_output=True, text=True)
    print(f"Pip install stdout: {proc.stdout}")
    print(f"Pip install stderr: {proc.stderr}")
    # Determine venv python executable
    py_exec = os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin', 'python')
    if not os.path.isfile(py_exec):
        print(f"Python executable not found in venv at {py_exec}")
        return {'status': 'error', 'logs': 'python not found in venv'}
    cmd = [py_exec, entrypoint]
    print(f"Running bot locally: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()
    print(f"Bot stdout: {stdout}")
    print(f"Bot stderr: {stderr}")
    return {'status': 'running' if proc.returncode == 0 else 'error', 'logs': stderr or stdout}


def startProject(state: OverallState):
    code = generateCode(state.TZ)
    venv_path, entrypoint = save(code, state.name, state.telegram_token or '')
    run_info = run(venv_path, entrypoint, state.name)
    msg = (
        f"Workspace '{state.name}' ready at {os.path.abspath(state.name)}\n"
        f"Venv & deps installed. Bot status: {run_info['status']}"
    )
    print(msg)
    return Command(
        update={
            'messages': state.messages + [AIMessage(content=msg)],
            'finished': True
        }
    )

# Build the state graph
builder = StateGraph(OverallState)
builder.add_node(createSummary) 
builder.add_node(askFromUser) 
builder.add_node(startProject) 
builder.add_edge(START, "createSummary")
builder.add_edge("askFromUser", "createSummary")
builder.add_edge("startProject", END)
graph = builder.compile()

if __name__ == "__main__":
    print("Hey, I am Bot Builder and I am here to help you to build your bot! To start, you need to give me some information. \n ")
    name = input("What is the name of the project? \n\n")
    description = input("\n\nGive me the description of the project. Include the workflow of the bot, the required information that bot needs to collect, and main objective of the bot. The more details you provide, the better results you will receive. \n\n")
    telegram_token = input("\n\nPlease, provide Telegram Bot token? \n\n")
    result = graph.invoke({"name": name, "description": description, "telegram_token": telegram_token, "questions": [],})
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
data to collect:
ideally, just name, age, and telegram_id. decide on your own for other information. just react to any info from user with free image of elephant animal (maybe from wikipedia or etc).
"""
