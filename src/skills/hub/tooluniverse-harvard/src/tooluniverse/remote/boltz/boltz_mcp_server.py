from fastmcp import FastMCP
import sys
import os
from tooluniverse.boltz_tool import Boltz2DockingTool
import json

# Read the tool config dicts from the JSON file
try:
    with open(
        os.path.join(os.path.dirname(__file__), "boltz_client_tools.json"), "r"
    ) as f:
        boltz_tools = json.load(f)
except FileNotFoundError as e:
    print(f"\033[91mError: {e}\033[0m")
    print(
        f"\033[91mIs boltz_client_tools.json in the parent directory of {__file__}?\033[0m"
    )
    sys.exit(1)

server = FastMCP("Your MCP Server")
agents = {}
for tool_config in boltz_tools:
    agents[tool_config["name"]] = Boltz2DockingTool(tool_config=tool_config)


@server.tool()
def run_boltz2(query: dict):
    """Run the Boltz2 docking tool.
    Args:
        "query" dict: A dictionary containing:
            - protein_sequence (str): Protein sequence using single-letter amino acid codes
            - ligands (list): List of ligand dictionaries, each containing:
                - id (str): Unique identifier for the ligand
                - smiles (str): SMILES representation of the ligand molecule
            - without_potentials (bool): Whether to run without potentials (default: False)
            - diffusion_samples (int): Number of diffusion samples to generate (default: 1)
            - Additional constraint keys may be included as needed
    Returns
        dict: A dictionary containing the docking results with the following structure:
            - predicted_structure (str): The predicted protein-ligand complex structure in CIF format
            - structure_format (str): Format of the structure file (typically 'cif')
            - structure_error (str): Error message if structure file is missing
            - affinity_prediction (object): JSON object containing affinity predictions and related data
            - affinity_error (str): Error message if affinity file is missing
    """
    return agents["boltz2_docking"].run(query)


if __name__ == "__main__":
    server.run(
        transport="streamable-http", host="0.0.0.0", port=8080, stateless_http=True
    )
