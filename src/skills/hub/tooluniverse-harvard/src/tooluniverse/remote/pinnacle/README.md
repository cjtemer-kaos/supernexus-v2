# PINNACLE Protein-Protein Interaction Tool

## Overview

The [PINNACLE](https://github.com/mims-harvard/PINNACLE) tool provides access to cell-type-specific protein-protein interaction embeddings. These embeddings capture functional relationships between proteins in different cellular contexts, enabling advanced analysis for drug discovery, disease research, and systems biology.

PINNACLE generates dense vector representations of proteins that encode both direct physical interactions and functional associations within specific cell types. This contextualization allows for more accurate modeling of biological processes in tissue-specific environments.

## Data Acquisition

### 1. Download PINNACLE Embeddings

The PINNACLE embeddings are hosted on Hugging Face at: https://huggingface.co/datasets/mims-harvard/ToolSpace

Use the following shell commands to download only the PINNACLE files from the `pinnacle_cge` directory:

```bash
# Install CLI if not already
uvx --from huggingface_hub hf

# Download only the pinnacle_cge folder
uvx --from huggingface_hub hf download mims-harvard/ToolSpace \
  --repo-type dataset \
  --include "pinnacle_cge/*" \
  --local-dir ./path/to/your/pinnacle/
```

### 2. Set Environment Variable

After downloading, set the `PINNACLE_DATA_PATH` environment variable:

```bash
export PINNACLE_DATA_PATH="/path/to/ToolSpace"
```

## Tool Input and Output

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cell_type` | string | Yes | Target cell type for embedding retrieval |
| `embed_path` | string | No | Custom path to embedding file (optional) |

The tool performs fuzzy matching to handle various naming conventions, spaces, hyphens, and capitalization differences.

### Output Format

The tool returns a JSON object with the following structure:

#### Successful Response
```json
{
  "embeddings": {
    "TP53": [0.1234, -0.5678, 0.9012, ...],
    "EGFR": [-0.2345, 0.6789, -0.1234, ...],
    "BRCA1": [0.3456, -0.7890, 0.2345, ...],
    "...": "..."
  },
  "context_info": [
    "Successfully retrieved embeddings for 15234 proteins/genes.",
    "Embedding dimensionality: 256 features per protein.",
    "Cell type context: b_cell (matched and processed)."
  ]
}
```


### Embedding Properties

- **Dimensionality**: A 328-dimensional vector (200 structure-based protein representation + 128 contextaware/-free protein representation)
- **Coverage**: 394,760 protein representations from 156 cell type contexts across 24 tissues
- **Format**: Dense numerical vectors (list of floats)

## MCP Server Setup

### Prerequisites

```bash
# create a uv virtual enviroment for COMPASS setup
uv venv pinnacle --python 3.10
source pinnacle/bin/activate
uv pip install -r requirements.txt
```

### Configuration

1. **Set up the environment**:
```bash
# Ensure PINNACLE_DATA_PATH points to your ToolSpace directory
export PINNACLE_DATA_PATH="/path/to/ToolSpace"
```

2. **Verify embedding files exist**:
```bash
ls -la $PINNACLE_DATA_PATH/pinnacle_embeds/ppi_embed_dict.pth
ls -la $PINNACLE_DATA_PATH/pinnacle_cge/
```

### Running the MCP Server
```bash
# Run the MCP server
python pinnacle_tool.py
```

### Server Configuration

- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Port**: `7001` (configured to avoid conflicts)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP for scalability
