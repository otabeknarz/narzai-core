from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated, Optional
from IPython.display import Image, display
from langgraph.types import Command
from typing_extensions import TypedDict, Literal
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# LLM
llm = init_chat_model("google_genai:gemini-2.0-flash")
parser = StrOutputParser()


# The overall state of the graph (this is the public state shared across nodes)
class OverallState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages] 
    name: str
    description: Optional[str] = None
    enough: Optional[bool] = None
    summary: Optional[str] = None
    TZ: Optional[str] = None
    questions: Annotated[list[dict], add_messages] 
    finished: Optional[bool] = None

def createSummary(state: OverallState) -> Command[Literal["startProject", "askFromUser"]]:
    description = state.description

    prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant that determines whether a project description is sufficient to start building a Telegram bot. "
        "If not, you must say what’s missing."
    ),
    (
        "human",
        "Project description:\n\n{description}\n\n"
        "Based on this, answer the following in JSON format:\n"
        "{{"
        "\"enough\": true/false, "
        "\"summary\": brief summary of the goal, "
        "\"TZ\": the time zone of the user if provided or inferred, else null"
        "}}"
    ),
    ])

    chain = prompt | llm | parser
    result = chain.invoke({"description": description})

    try:
        import json
        llm_reply = json.loads(result)
    except json.JSONDecodeError:
        llm_reply = {
            "enough": False,
            "summary": None,
            "TZ": None
        }

    goto = "startProject" if llm_reply.get("enough") else "askFromUser"

    return Command(
        update={
            "summary": llm_reply.get("summary"),
            "TZ": llm_reply.get("TZ"),
        },
        goto=goto,
    )


def askFromUser(state: OverallState):
    messages = state.messages
    description = state.description
    question_answers = state.questions

    print("Your description of the project is not sufficient. Please answer the following questions: ")
    questions = ["What kind of info should we collect?"]

    for question in questions:
        answer = input(question + "\n")
        question_answers += [question + " " + answer]

    return {"questions": question_answers}

def startProject(state: OverallState):
    return state

# Build the state graph
builder = StateGraph(OverallState)
builder.add_node(createSummary) 
builder.add_node(askFromUser) 
builder.add_node(startProject) 


builder.add_edge(START, "createSummary")  
builder.add_edge("createSummary", "askFromUser")  
builder.add_edge("createSummary", "startProject")  

builder.add_edge("startProject", END)  
graph = builder.compile()

# Test the graph with a valid input

print("Hey, I am Bot Builder and I am here to help you to build your bot! To start, you need to give me some information. ")
name = input("What is the name of the project? ")
description = input("Give me the description of the project. Include the workflow of the bot, the required information that bot needs to collect, and main objective of the bot. The more details you provide, the better results you will receive.")


result = graph.invoke({"name": name, "description": description})
for message in result["messages"]:
    message.pretty_print()

display(Image(graph.get_graph().draw_mermaid_png()))
with open("state_graph.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())

"""
llm = init_chat_model("google_genai:gemini-2.0-flash")


class Feedbakck(BaseModel):
    evaluation: Litaral["enough", "not enough"] = Field(
        description="Decide whether the desctiption is sufficient or not to start the project."
    )
"""

# The bot needs to generate or find image of elephant from public source and send to user after they press /start or write any text or send any signal in general. No matter what bot should reply with random elephant picture
# ideally, no info. just react to any info from user with free image of elephant animal (maybe from wikipedia or etc)