# USPTO Downloader Tool Setup

This tutorial will Tutorial you through setting up and running MCP (Model Context Protocol) server-based tools for USPTO patent document downloading. This tool requires GPUs to run optical character recognition on the patent PDFs and extract the patent text.

## Overview

This directory contains the following MCP server implementation:
- **uspto_downloader_MCP.py**: Enables patent document downloading and processing from USPTO

## Prerequisites

### Hardware Requirements
- **GPU**: NVIDIA A100 or H100 GPU recommended

### System Requirements
- Linux-based system (tested on Ubuntu/CentOS)
- CUDA-compatible GPU drivers
- Network access for API calls

## Setup Instructions

### 1. Environment Setup
```bash
conda create -n tooluniverse-env python=3.11 -c conda-forge -y
conda activate tooluniverse-env

# Verify CUDA support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 2. Install ToolUniverse and MCP Dependencies

```bash
# Install compatible NumPy version first
pip install "numpy==2.0"

# Install ToolUniverse
git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse

python -m pip install . --no-cache-dir

# Install additional dependencies
pip install requests pymupdf easyocr python-docx Pillow pyarrow fastparquet lxml aiohttp
pip install -U sentence-transformers
```

### 4. Environment Configuration

#### Set Environment Variables
Set the required environment variables on the **client machine** where you're calling the MCP tool from ToolUniverse (not on the GPU server where the tool is running):

```bash
# For USPTO server (running on port 7000)
export USPTO_MCP_SERVER_HOST="your-gpu-hostname"

# USPTO API key
export USPTO_API_KEY="your-uspto-api-key"
```

**Important**: Set these variables on the machine where you're executing your ToolUniverse code, even if the MCP server is running on a different GPU machine.

**Finding your GPU hostname:**
```bash
# Get current hostname by running this command on the GPU where your MCP server will run.
hostname

# Example hostnames:
# - gpu-node-01
# - compute-a100-001.cluster.edu
# - localhost (if running locally)
```

## Running the MCP Servers

### 1. Start USPTO MCP Server

```bash
### 1. Start USPTO MCP Server on the GPU where you want it to run.
python uspto_downloader_mcp_server.py
```

The server will start on `http://0.0.0.0:7000` but will be accessible via your GPU hostname (e.g., `http://your-gpu-hostname:7000`) for patent document retrieval.

## Usage Examples
For comprehensive usage examples and testing patterns, please refer to the test file:

```bash
# View MCP tool usage examples
cat ToolUniverse/src/tooluniverse/test/test_mcp_tool.py
```

This test file contains detailed examples of how to interact with the USPTO patent downloader MCP server, including proper API calls and parameter formatting.
