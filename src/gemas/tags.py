"""
Tags — XML Tag model for structured LLM I/O in gemas.

Portado de Confucius (Meta) con adaptaciones para SuperNEXUS:
  - Sin dependencia de LangChain ni Pydantic v1
  - bs4.BeautifulSoup como backend de serialización
  - TagLike: Tag | str | list[Tag | str]

Patrón: Tag → prettify() → system prompt
           → to_bs4() → parse from LLM response
"""

from __future__ import annotations

import html
from textwrap import dedent
from typing import Any, Dict, List, Union

import bs4
from pydantic import BaseModel, Field


class Tag(BaseModel):
    name: str = Field(..., description="Tag name")
    attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Tag attributes"
    )
    contents: str | Tag | List[str | Tag] | None = Field(
        default_factory=list, description="Tag contents"
    )

    def to_bs4(self, soup: bs4.BeautifulSoup) -> bs4.Tag:
        new_tag = soup.new_tag(self.name, attrs=self.attributes)
        if self.contents:
            if isinstance(self.contents, (str, Tag)):
                self.contents = [self.contents]
            for content in self.contents:
                if isinstance(content, Tag):
                    new_tag.append(content.to_bs4(soup))
                elif isinstance(content, str):
                    new_tag.append(bs4.NavigableString(content))
                else:
                    raise TypeError(f"Unsupported content type: {type(content)}")
        return new_tag

    def prettify(self, parser: str = "html.parser", unescape: bool = True, **kwargs: Any) -> str:
        soup = bs4.BeautifulSoup("", parser)
        soup.append(self.to_bs4(soup))
        if "formatter" not in kwargs:
            kwargs["formatter"] = bs4.formatter.HTMLFormatter(indent=0)
        result = soup.prettify(**kwargs)
        return html.unescape(result) if unescape else result


TagLike = Union[Tag, str, List[Union[Tag, str]]]


def unescape(content: str) -> str:
    while content != html.unescape(content):
        content = html.unescape(content)
    return content


def unescaped_tag_content(tag: bs4.element.Tag) -> str:
    return dedent(unescape(tag.decode_contents())).strip()


class Example(Tag):
    name: str = "example"


class Examples(Tag):
    name: str = "examples"


class Thinking(Tag):
    name: str = "thinking"


class ToolUse(Tag):
    name: str = "tool_use"


class AssistantResponse(Tag):
    name: str = "assistant_response"


class UserQuery(Tag):
    name: str = "user_query"
