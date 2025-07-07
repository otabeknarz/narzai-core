from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated, Optional
from langgraph.types import Command
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import Literal
from prompts import SYSTEM_PROMPT_START, SYSTEM_PROMPT_SUMMARY

import re
import json

# LLM
llm = init_chat_model("google_genai:gemini-2.0-flash")
parser = StrOutputParser()



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
    enough: Optional[bool] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    questionsAnswers: Annotated[list[str], merge_questions]
    questions: Optional[list[str]] = None
    finished: Optional[bool] = None

def createSummary(state: OverallState) -> Command[Literal["askFromUser", "startProject"]]: 
    description = state.description
    if state.questions:
        qna_text = "\n".join(state.questions)
        description = description + "\n\nAdditional user answers:\n" + qna_text
    
    prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant that determines whether a project description is sufficient to start building a Telegram bot. "
        "If not, you must say what’s missing. For now let's say these three info are required for collection: name, telegram_id, age. If they don't include other than those three data, you can excuse them."
    ),
    (
        "human",
        "Project description:\n\n{description}\n\n"
        "Based on this, answer the following in JSON format, don't add anything:\n"
        "{{"
        "\"enough\": true/false, "
        "\"summary\": brief summary of the goal, "
        "\"TZ\": the time zone of the user if provided or inferred, else null"
        "}}"
    ),
    ])

    chain = prompt | llm | parser
    result = chain.invoke({"description": description})[8:-3]
    print("Raw LLM output:", result)

    llm_reply = get_cleaned_dict(result or "{}")

    print(llm_reply.get("enough"))
    if llm_reply.get("enough")==True:
        goto = "startProject" 
    else: 
        goto = "askFromUser"

    return Command(
        update={
            "enough": llm_reply.get("enough"),
            "summary": llm_reply.get("summary"),
            "TZ": llm_reply.get("TZ"),
        },
        goto=goto,
    )


def askFromUser(state: OverallState):

    questions_responses = state.questions or []
    questions = state.questions or []

    print("Your description of the project is not sufficient. Please answer the following questions: ")

    for question in questions:
        answer = input(question + "\n")
        question_answers.append(f"{question} {answer}")

    return Command(update={"questions": question_answers}, goto="createSummary")

def startProject(state: OverallState): # UNFINISHED
    final_message = f"Project started! Summary:\n\n{state.summary} \n\n TZ: {state.TZ}"
    print("Project Started")
    return Command(
        update={
            "messages": state.messages + [AIMessage(content=final_message)],
            "finished": True
        }
    )


# Build the state graph
builder = StateGraph(OverallState)
builder.add_node(createSummary) 
builder.add_node(askFromUser) 
builder.add_node(startProject) 

# TIP: really think about the graph structure. i think there is too much going on. connections between nodes makes it ez to go to other notes somehow.
# UPD: i was right
builder.add_edge(START, "createSummary")
builder.add_edge("askFromUser", "createSummary")
builder.add_edge("startProject", END)

graph = builder.compile()

# Test the graph with a valid input

print("Hey, I am Bot Builder and I am here to help you to build your bot! To start, you need to give me some information. \n ")
name = input("What is the name of the project? \n\n")
description = input("\n\nGive me the description of the project. Include the workflow of the bot, the required information that bot needs to collect, and main objective of the bot. The more details you provide, the better results you will receive. \n\n ")


result = graph.invoke({"name": name, "description": description, "questions": [],})
for message in result["messages"]:
   message.pretty_print()

with open("state_graph.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())
print("Graph Image generated.")

"""
llm = init_chat_model("google_genai:gemini-2.0-flash")


class Feedback(BaseModel):
    evaluation: Litaral["enough", "not enough"] = Field(
        description="Decide whether the desctiption is sufficient or not to start the project."
    )
"""
# example prompt
# name:
# elephant image gen bot
# description:
# The bot needs to generate or find image of elephant from public source and send to user after they press /start or write any text or send any signal in general. No matter what bot should reply with random elephant picture
# data to collect:
# ideally, just name, age, and telegram_id. decide on your own for other information. just react to any info from user with free image of elephant animal (maybe from wikipedia or etc). 
