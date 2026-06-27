# Transcriptformer Gene Embedding Tool

## Overview

The [Transcriptformer](https://github.com/czi-ai/transcriptformer) tool provides access to contextualized gene embeddings learned from single-cell RNA sequencing data. Transcriptformer uses transformer architecture to capture cell-type-specific and disease-state-specific gene expression patterns, enabling precise analysis of gene behavior in relevant biological contexts. In Prism ToolSpace, we pre-inferenced the transcriptformer CGE (contextualized gene embeddings) across 5 single-cell disease atlas, while can be ealisy access and retrivel via this tool.

## Data Acquisition

### 1. Download Transcriptformer Embeddings

The Transcriptformer embeddings are hosted on Hugging Face at: https://huggingface.co/datasets/mims-harvard/ToolSpace

Use the following shell commands to download only the Transcriptformer files from the `transcriptformer_cge` directory:

```bash
# Install CLI if not already
uvx --from huggingface_hub hf

# Download only the transcriptformer_cge folder
uvx --from huggingface_hub hf download mims-harvard/ToolSpace \
  --repo-type dataset \
  --include "transcriptformer_cge/*" \
  --local-dir ./ToolSpace/
```

### File Structure

The Transcriptformer directory contains disease-specific embedding stores:

```
transcriptformer_cge/
├── follicular_lymphoma/
│   ├── metadata.json.gz
│   ├── b_cell_normal.npy
│   ├── b_cell_follicular_lymphoma.npy
│   ├── t_cell_normal.npy
│   ├── t_cell_follicular_lymphoma.npy
│   └── ... (other cell type × disease state combinations)
├── rheumatoid_arthritis/
├── type_1_diabetes_mellitus/
├── sjogren_syndrome/
└── hepatoblastoma/
```

### 2. Set Environment Variable

After downloading, set the `TRANSCRIPTFORMER_DATA_PATH` environment variable:

```bash
# Set environment variable to point to your data directory
export TRANSCRIPTFORMER_DATA_PATH="/path/to/ToolSpace"
```

## Tool Input and Output

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `disease` | string | Yes | Disease/dataset identifier (e.g., "follicular_lymphoma") |
| `state` | string | Yes | Disease state context ("normal", "disease_name", etc.) |
| `cell_type` | string | Yes | Cell type context for embeddings |
| `gene_names` | List[str] | Yes | Gene identifiers (symbols or Ensembl IDs) |

#### Supported Disease Contexts
Available disease datasets include:
- `follicular_lymphoma` - Follicular lymphoma vs normal tissue
- `rheumatoid_arthritis` - Rheumatoid arthritis vs healthy controls
- `type_1_diabetes_mellitus` - Type 1 diabetes vs normal pancreatic tissue
- `sjogren_syndrome` - Sjögren's syndrome vs healthy controls
- `hepatoblastoma` - Hepatoblastoma vs normal liver tissue

#### Disease State Options
- `normal` - Healthy/control condition
- `[disease_name]` - Disease-affected state (matches the disease identifier)


#### Gene Identifier Formats
- **Gene symbols**: `["TP53", "BRCA1", "EGFR", "MYC"]`
- **Ensembl IDs**: `["ENSG00000141510", "ENSG00000139618"]`
- **Mixed formats**: Supported in the same request
- **Empty list**: Retrieves all available genes

### Output Format

The tool returns a JSON object with the following structure:

#### Successful Response
```json
{
  "embeddings": {
    "TP53": [0.1234, -0.5678, 0.9012, ...],
    "BRCA1": [-0.2345, 0.6789, -0.1234, ...],
    "EGFR": [0.3456, -0.7890, 0.2345, ...],
    "...": "..."
  },
  "context_info": [
    "Successfully retrieved 1247 gene embeddings for context: follicular_lymphoma - normal - b_cell",
    "Embedding dimensionality: 512 features per gene",
    "Disease context: follicular_lymphoma (validated and processed)"
  ]
}
```

#### Error Response
```json
{
  "error": "Disease 'unknown_disease' not found in available stores",
  "context_info": [
    "Available diseases: ['follicular_lymphoma', 'rheumatoid_arthritis', 'type_1_diabetes_mellitus', 'sjogren_syndrome', 'hepatoblastoma']",
    "Please check disease identifier and ensure data is downloaded"
  ]
}
```

### Embedding Properties

- **Dimensionality**: 512-dimensional vectors per gene
- **Format**: Dense numerical vectors (list of float32 values)
- **Context-specific**: Embeddings vary by cell type and disease state
- **Precision**: Float32 for optimal balance of accuracy and efficiency

## MCP Server Setup

### Prerequisites

```bash
# create a uv virtual enviroment
uv venv transcriptformer --python 3.10
source transcriptformer/bin/activate
uv pip install -r requirements.txt
```

### Configuration

1. **Set up the environment**:
```bash
# Ensure TRANSCRIPTFORMER_DATA_PATH points to your ToolSpace directory
export TRANSCRIPTFORMER_DATA_PATH="/path/to/ToolSpace"
```

2. **Verify embedding files exist**:
```bash
ls -la $TRANSCRIPTFORMER_DATA_PATH/transcriptformer_cge/
ls -la $TRANSCRIPTFORMER_DATA_PATH/transcriptformer_cge/follicular_lymphoma/
```

### Running the MCP Server

```bash
# Run the MCP server
python transcriptformer_tool.py
```

### Server Configuration

- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Port**: `7002` (configured to avoid conflicts with other tools)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP for scalability
