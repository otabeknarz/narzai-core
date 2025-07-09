import logging
import shutil
import sys
import os
import re
import subprocess
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, AnyMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser
from typing import Annotated, Optional
from typing_extensions import Literal
from langgraph.types import Command
from prompts import SYSTEM_PROMPT_START, SYSTEM_PROMPT_SUMMARY

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Load environment for LLM credentials
load_dotenv()

# Initialize LLM and parser
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


class OverallState(BaseModel):
    messages: Annotated[list[AnyMessage], Field(default_factory=list)]
    name: str
    description: Optional[str] = None
    telegram_token: Optional[str] = None
    enough: Optional[bool] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    questionsAnswers: Annotated[list[str], merge_questions] = []
    questions: Optional[list[str]] = None
    finished: Optional[bool] = None


def createSummary(state: OverallState) -> Command[Literal['askFromUser', 'startProject']]:
    qna_text = "\n".join(state.questionsAnswers)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_START),
        ("human", f"First description: {state.description}\n\nqa_history: {qna_text}")
    ])
    chain = prompt | llm | parser
    result = chain.invoke({"description": state.description, "qna_text": qna_text})
    goto = 'startProject' if result.get('enough') else 'askFromUser'
    return Command(
        update={
            'enough': result.get('enough'),
            'questions': result.get('questions'),
            'summary': result.get('summary'),
            'TZ': result.get('TZ'),
        },
        goto=goto
    )


def askFromUser(state: OverallState):
    for question in state.questions or []:
        answer = input(question + '\n')
        state.questionsAnswers.append(f"{question} {answer}")
    return {'questionsAnswers': state.questionsAnswers}


def generate_bot_code(summary: str) -> str:
    prompt = (
        "You are a Python developer.\n"
        "Generate a complete aiogram-based Telegram bot project.\n"
        "Include python-dotenv setup, handlers, entrypoint.\n\n"
        f"Project summary:\n{summary}\n\n"
        "Return code files in separate markdown blocks labeled with filename."
    )
    logger.info("Requesting bot code generation from LLM...")
    response = llm.invoke(prompt)
    logger.debug("LLM response: %s", response.content)
    return response.content


def save_code_to_disk(code_blocks: str, project_name: str, telegram_token: str) -> str:
    project_dir = os.path.abspath(project_name)
    logger.info("Creating project directory at %s", project_dir)
    os.makedirs(project_dir, exist_ok=True)

    # Write .env
    env_path = os.path.join(project_dir, '.env')
    logger.info("Writing .env with token")
    with open(env_path, 'w') as f:
        f.write(f"TELEGRAM_BOT_TOKEN={telegram_token}\n")

    # Create venv
    venv_path = os.path.join(project_dir, 'venv')
    logger.info("Creating virtual environment using %s", sys.executable)
    try:
        subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error("Venv creation failed: %s", e)
        raise

    # Write requirements
    requirements = ['aiogram', 'python-dotenv']
    req_path = os.path.join(project_dir, 'requirements.txt')
    logger.info("Writing requirements.txt")
    with open(req_path, 'w') as f:
        f.write('\n'.join(requirements))

    # Install deps
    pip_exec = shutil.which('pip', path=os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin'))
    if not pip_exec:
        pip_exec = os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin', 'pip')
    logger.info("Installing dependencies using %s", pip_exec)
    proc = subprocess.run([pip_exec, 'install', '-r', req_path], capture_output=True, text=True)
    logger.debug("Pip install stdout: %s", proc.stdout)
    logger.debug("Pip install stderr: %s", proc.stderr)

    # Write code files
    logger.info("Parsing and writing code files from LLM output")
    matches = re.findall(r"```([^\n]+)\n([\s\S]*?)```", code_blocks)
    entrypoint = None
    for fname, content in matches:
        path = os.path.join(project_dir, fname.strip())
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info("Writing file %s", path)
        with open(path, 'w') as f:
            f.write(content)
        if fname.strip().endswith('main.py') or fname.strip().endswith('__main__.py'):
            entrypoint = path

    return venv_path, entrypoint


def run_bot_locally(venv_path: str, entrypoint: str) -> dict:
    # Determine venv python executable
    py_exec = os.path.join(venv_path, 'Scripts' if os.name=='nt' else 'bin', 'python')
    if not os.path.isfile(py_exec):
        logger.error("Python executable not found in venv at %s", py_exec)
        return {'status': 'error', 'logs': 'python not found in venv'}
    cmd = [py_exec, entrypoint]
    logger.info("Running bot locally: %s", ' '.join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()
    logger.debug("Bot stdout: %s", stdout)
    logger.debug("Bot stderr: %s", stderr)
    return {'status': 'running' if proc.returncode == 0 else 'error', 'logs': stderr or stdout}


def startProject(state: OverallState):
    code_blocks = generate_bot_code(state.summary)
    venv_path, entrypoint = save_code_to_disk(code_blocks, state.name, state.telegram_token or '')
    run_info = run_bot_locally(venv_path, entrypoint)  # run bot instead of Docker
    msg = (
        f"✅ Workspace '{state.name}' ready at {os.path.abspath(state.name)}\n"
        f"Venv & deps installed. Bot status: {run_info['status']}"
    )
    logger.info(msg)
    return Command(
        update={
            'messages': state.messages + [AIMessage(content=msg)],
            'finished': True
        }
    )

# Build graph
builder = StateGraph(OverallState)
builder.add_node(createSummary)
builder.add_node(askFromUser)
builder.add_node(startProject)
builder.add_edge(START, 'createSummary')
builder.add_edge('askFromUser', 'createSummary')
builder.add_edge('startProject', END)
graph = builder.compile()

if __name__ == '__main__':
    print("Welcome to BotBuilder! Provide project name, description, and bot token.")
    name = input("Project name: ")
    description = input("Description: ")
    token = input("Telegram Bot Token: ")
    result = graph.invoke({
        'name': name,
        'description': description,
        'telegram_token': token,
        'questions': []
    })
    for m in result['messages']:
        m.pretty_print()
    with open('state_graph.png', 'wb') as f:
        f.write(graph.get_graph().draw_mermaid_png())
    print("Done.")