# DepMap Gene Correlation Analysis Tool - MCP Server

A MCP tool from [Prism ToolSpace](https://huggingface.co/datasets/mims-harvard/ToolSpace) for analyzing gene-gene correlations from the [DepMap (Dependency Map)](https://depmap.org/) CRISPR knockout screening dataset. This tool processes systematic CRISPR-Cas9 knockout data from over 1,320 cancer cell lines from DepMap 24Q2 to identify genetic dependencies and co-essential gene pairs.

## Prerequisites

### 1. Install Required Dependencies

Install the required Python packages for the DepMap correlation analysis:

```bash
# Create a virtual environment for DepMap setup
uv venv depmap --python 3.10
source depmap/bin/activate
uv pip install -r requirements.txt

```

## Data Setup

### 1. Download DepMap 24Q2 Dataset

Download the preprocessed DepMap correlation data from the Prism ToolSpace or prepare your own correlation matrices:

```bash
# Install CLI if not already
uvx --from huggingface_hub hf

# Download only the depmap_24q2 folder
uvx --from huggingface_hub hf download mims-harvard/ToolSpace \
  --repo-type dataset \
  --include "depmap_24q2/*" \
  --local-dir ./path/to/your/depmap/
```
**Required Files:**
- **Gene correlation matrix** - Pairwise correlations between genes
- **P-value matrix** - Statistical significance of correlations
- **Gene index** - Mapping of gene symbols to matrix indices
- **Adjusted p-values** (optional) - FDR-corrected p-values

**Data Sources:**
- **DepMap Portal**: https://depmap.org/portal/download/
- **DepMap 24Q2 Release**: Contains CRISPR knockout data for 1,320+ cell lines
- **CERES Algorithm**: Standardized gene effect scores for dependency analysis

### 2. Directory Structure Setup

Create the following directory structure for your DepMap data:

```
/path/to/your/depmap/
├── depmap_24q2/              # DepMap data directory
│   ├── corr_matrix.npy       # Gene correlation matrix (dense format)
│   ├── p_val_matrix.npy      # P-value matrix (dense format)
│   ├── p_adj_matrix.npy      # Adjusted p-values (optional)
│   ├── gene_idx_array.npy    # Gene symbol index array
│   └── gene_names.txt        # Gene symbols (alternative format)
│
│   # Alternative sparse format for large datasets:
│   └── gene_correlations.h5  # HDF5 sparse matrices
```

### 3. Set Environment Variable

Set the `DEPMAP_DATA_PATH` environment variable to point to your DepMap installation:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export DEPMAP_DATA_PATH="/path/to/your/depmap"
```

## Input and Output Specifications

### Input Format

The tool accepts gene symbol pairs for correlation analysis:

- **Gene Symbols**: Standard HUGO gene nomenclature (e.g., "BRAF", "TP53", "MAPK1")
- **Case Insensitive**: Tool automatically standardizes gene symbols
- **Validation**: Checks gene availability in the correlation matrix

### Output Format

The tool returns a structured JSON response with comprehensive correlation analysis:

```json
{
  "correlation_data": {
    "correlation": 0.756,
    "p_value": 1.23e-15,
    "adjusted_p_value": 4.56e-12
  },
  "interpretation": {
    "strength": "strong",
    "significance": "significant (FDR corrected)",
    "direction": "similar",
    "biological_relationship": "co-dependent relationship (shared essential functions)",
    "summary": "DepMap analysis reveals a strong, similar correlation (r=0.756) in knockout effects between BRAF and MAPK1, suggesting co-dependent relationship (shared essential functions). This finding is significant (FDR corrected)."
  },
  ...
}
```

**Output Fields:**
- `correlation_data` (dict): Statistical measures
  - `correlation` (float): Pearson correlation coefficient (-1.0 to 1.0)
  - `p_value` (float): Statistical significance of correlation
  - `adjusted_p_value` (float, optional): FDR-corrected p-value
- `interpretation` (dict): Biological and statistical context
  - `strength` (str): Correlation strength classification
  - `significance` (str): Statistical significance interpretation
  - `direction` (str): Relationship type (similar vs opposing effects)
  - `biological_relationship` (str): Biological interpretation
  - `summary` (str): Comprehensive analysis summary
- `context_info` (list): Analysis metadata and messages
- `error` (str, optional): Error description if analysis failed

## Running the MCP Server

### 1. Start the Server

```bash
# Activate the virtual environment
source depmap/bin/activate

# Set environment variable (if not in bashrc)
export DEPMAP_DATA_PATH="/path/to/your/depmap"

# Run the MCP server
python depmap_24q2_mcp_tool.py
```

### 2. Server Configuration

The server runs with the following default settings:
- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Port**: `7002` (configured to avoid conflicts)
- **Transport**: `streamable-http`
- **Mode**: Stateless HTTP


### Common Issues

1. **Data Directory Not Found**
   ```
   FileNotFoundError: DepMap data directory not found at /path/to/data
   ```
   - Ensure `DEPMAP_DATA_PATH` is set correctly
   - Verify the `depmap_24q2/` subdirectory exists
   - Check that correlation matrices are properly downloaded

2. **Gene Symbol Not Found**
   ```
   KeyError: Gene 'INVALID' not available in the DepMap correlation matrix
   ```
   - Verify gene symbol spelling (use standard HUGO nomenclature)
   - Check if gene is present in the DepMap 24Q2 dataset
   - Try alternative gene symbols or aliases

3. **Missing Correlation Data**
   ```
   FileNotFoundError: No correlation data found in directory
   ```
   - Ensure correlation matrices are in the correct format (.npy or .h5)
   - Verify gene index files are present (`gene_idx_array.npy` or `gene_names.txt`)
   - Check file permissions and accessibility


## References

- **DepMap Project**: [Broad Institute DepMap Portal](https://depmap.org/)
- **DepMap Paper**: [Mapping the Cancer Dependency Map](https://www.nature.com/articles/s41586-019-1103-9)
- **CERES Algorithm**: [Computational correction of copy number effect improves specificity of CRISPR-Cas9 essentiality screens in cancer cells](https://www.nature.com/articles/s41588-018-0194-x)
- **Data Portal**: https://depmap.org/portal/download/
