from fastmcp import FastMCP
import sys
import os
from .uspto_downloader_tool import USPTOPatentDocumentDownloader
import json

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "uspto_downloader_client_tools.json"),
        "r",
    ) as f:
        uspto_downloader_tools = json.load(f)
except FileNotFoundError as e:
    print(f"\033[91mError: {e}\033[0m")
    print(
        f"\033[91mIs uspto_downloader_client_tools.json in the parent directory of {__file__}?\033[0m"
    )
    sys.exit(1)

server = FastMCP("Your MCP Server")
agents = {}
for tool_config in uspto_downloader_tools:
    agents[tool_config["name"]] = USPTOPatentDocumentDownloader(tool_config=tool_config)


@server.tool()
def download_abst(query: dict):
    """Retrieve the abstract of a patent application by its application number.
    Args:
        "query" dict: A dictionary containing the application number under the key "applicationNumberText".
    Returns
        dict: A dictionary containing the abstract text under the 'result' key or an error message under the 'error' key if the document could not be retrieved.
    """
    return agents["get_abstract_from_patent_app_number"].run(query)


@server.tool()
def download_claims(query: dict):
    """Retrieve the claims of a patent application by its application number.
    Args:
        "query" dict: A dictionary containing the application number under the key "applicationNumberText".
    Returns
        dict: A dictionary containing the claims text under the 'result' key or an error message under the 'error' key if the document could not be retrieved.
    """
    return agents["get_claims_from_patent_app_number"].run(query)


@server.tool()
def download_full_text(query: dict):
    """Retrieve the full text of a patent application by its application number.
    Args:
        "query" dict: A dictionary containing the application number under the key "applicationNumberText".
    Returns
        dict: A dictionary containing the full text under the 'result' key or an error message under the 'error' key if the document could not be retrieved.
    """
    return agents["get_full_text_from_patent_app_number"].run(query)


if __name__ == "__main__":
    server.run(
        transport="streamable-http", host="0.0.0.0", port=8081, stateless_http=True
    )
