from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser


class Project(BaseModel):
    name: str = Field(description="The name of the project")
    description: str = Field(description="The description from the user input")
    questions_answers: list = Field(description="All questions and answers from project chat history")
    summary: str = Field(description="The summary of the project generated by AI according to description")
    tz: str = Field(description="The summary by genereated AI for developers")
    dependencies: list = Field(description="Which dependencies to install and use with its versions")


class File(BaseModel):
    name: str = Field(description="The name of the file in project")
    description: str = Field(description="The description of the file: what should this file do")
    functions: list = Field(description="The list of every function in the file with small descriptions")


class Function(BaseModel):
    name: str = Field(description="The name of the function")
    description: str = Field(description="The description of the function")


project_parser = PydanticOutputParser(pydantic_object=Project)
file_parser = PydanticOutputParser(pydantic_object=File)
function_parser = PydanticOutputParser(pydantic_object=Function)
