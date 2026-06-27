"""
XMLOutputParser — Parse structured LLM responses into BeautifulSoup trees.

Portado de Confucius (Meta) con adaptaciones para SuperNEXUS:
  - Sin dependencia de LangChain (BaseOutputParser / Generation)
  - Trabaja con strings directamente (desde LLMResponse.content)
  - Async-first: aparse() como método principal

Uso:
    parser = XMLOutputParser(root_tag="response")
    output = await parser.aparse("<response><thinking>...</thinking></response>")
    tag = output.soup.find("thinking")
    content = unescaped_tag_content(tag)
"""

from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from .tags import unescaped_tag_content

DEFAULT_XML_FORMAT_INSTRUCTIONS = """\
The output should be formatted as a XML file. Remember to always open and close all the tags.

As an example, for the tags ["foo", "bar", "baz"]:
1. String "<foo>\\n   <bar>\\n      <baz></baz>\\n   </bar>\\n</foo>" is a well-formatted instance of the schema. 
2. String "<foo>\\n   <bar>\\n   </foo>" is a badly-formatted instance.
"""


class XMLOutput(BaseModel):
    soup: BeautifulSoup = Field(..., description="BeautifulSoup object")

    class Config:
        arbitrary_types_allowed = True


class XMLOutputParser(BaseModel):
    format_instructions: Optional[str] = Field(
        default=None,
        description="User-defined format instructions override",
    )
    parser: str = Field("lxml-xml", description="Parser to use (lxml-xml or html.parser)")
    root_tag: str = Field("root", description="Root tag to wrap orphan content")

    class Config:
        arbitrary_types_allowed = True

    async def aparse(self, text: str) -> XMLOutput:
        try:
            soup = BeautifulSoup(text, self.parser)
            if soup.find(self.root_tag) is None:
                soup = BeautifulSoup(
                    f"<{self.root_tag}>{text}</{self.root_tag}>", self.parser
                )
            return XMLOutput(soup=soup)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse XML using {self.parser} parser: {exc}"
            )

    def get_format_instructions(self) -> str:
        if self.format_instructions is not None:
            return self.format_instructions
        return DEFAULT_XML_FORMAT_INSTRUCTIONS

    def extract_tag(self, text: str, tag_name: str) -> Optional[str]:
        soup = BeautifulSoup(text, self.parser)
        tag = soup.find(tag_name)
        if tag is not None:
            return unescaped_tag_content(tag)
        return None

    def extract_all_tags(self, text: str, tag_name: str) -> List[str]:
        soup = BeautifulSoup(text, self.parser)
        return [unescaped_tag_content(tag) for tag in soup.find_all(tag_name)]
