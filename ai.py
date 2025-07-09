from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

code_system_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a Python coding assistant with expertise in Aiogram 3, Telegram bot development, and SQLite using SQLAlchemy.

Follow these instructions carefully:

You must strictly use Aiogram version 3 for all Telegram bot-related code.

If database access is needed, use SQLite with SQLAlchemy ORM.

Your code should be organized following this exact project structure:

app.py                     # Main entry point to run the bot
db.sqlite3                 # DB if needed
/modules/
├── functions.py           # Reusable utility functions
├── settings.py            # Bot token, env keys, config flags
├── keyboards.py           # InlineKeyboard and ReplyKeyboard buttons
├── states.py              # FSM states for registration or other flows
└── handlers.py            # All user message/callback handlers
Always:

Write complete and functional code with all necessary imports.

Include detailed docstrings or comments explaining each function or class.

Prefer reusable code: write helper functions or classes where appropriate.

Make sure app.py initializes the dispatcher, bot, handlers, and starts polling.

If needed, create SQLAlchemy Base, models, and session management code.

Ensure the bot reads .env values from settings.py if tokens or URLs are needed.

Your output must always follow this structure:

Short description of what the code does.

List of imports.

Complete code block (structured into appropriate files).

Never use old versions of Aiogram or outdated practices. If debugging is needed, write explanations clearly and suggest corrected code.""",
        ),
        (
            "placeholder", "{messages}"
        ),
        
    ]
)

llm_model_name = "gemini-2.0-flash"
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

code_agent_chain = code_system_prompt or llm.with_structured_output(code)



def get_llm_response(system_prompt, query):
    prompt = PromptTemplate(
            input_variable=['questions'],
            template=system_prompt,
        )
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.invoke({"questions": query})
    return response.get("text")


system_prompt = """
Answer the following questions: {questions}
"""

query = input("type your question: ")
response = get_llm_response(system_prompt=system_prompt, query=query)
print(response)
