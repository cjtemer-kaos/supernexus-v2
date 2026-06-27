"""
Transcriptformer Gene Embedding Tool - MCP Server

This module provides an MCP (Model Context Protocol) server for retrieving
pre-computed gene embeddings from the Transcriptformer model. Transcriptformer
is a transformer-based architecture trained on single-cell RNA sequencing data
to learn contextualized gene representations that capture cell-type-specific
and disease-state-specific expression patterns.

The tool provides access to disease-specific embedding stores that enable:
- Gene similarity analysis in specific cellular contexts
- Biomarker discovery and validation
- Pathway analysis and functional annotation
- Drug target identification and prioritization
- Precision medicine applications
- Systems biology research
"""

from fastmcp import FastMCP
import os
import asyncio
import uuid
import gzip
import json
import numpy as np
from typing import Union, List, Dict, Tuple, Optional, Any


# Initialize MCP Server for Transcriptformer gene embedding retrieval
server = FastMCP("Transcriptformer SMCP Server")


class TranscriptformerEmbeddingTool:
    """
    Comprehensive tool for retrieving contextualized gene embeddings from Transcriptformer models.

    This class provides functionality to:
    - Load and manage disease-specific embedding stores
    - Retrieve gene embeddings for specific cellular contexts (cell type + disease state)
    - Handle both gene symbols and Ensembl IDs with intelligent mapping
    - Cache metadata for efficient repeated queries
    - Support bulk embedding retrieval for pathway analysis

    Transcriptformer embeddings encode gene expression patterns learned from
    single-cell RNA sequencing data, capturing:
    - Cell-type-specific expression signatures
    - Disease-state-dependent gene regulation
    - Co-expression relationships and functional modules
    - Temporal dynamics and developmental trajectories

    The tool supports various disease contexts and cell types, enabling
    precision medicine applications and systems biology research.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the Transcriptformer embedding tool by discovering available disease stores.

        The tool automatically scans the embedding store directory to identify
        available disease-specific embedding collections and prepares metadata
        caching infrastructure for efficient access.

        Raises:
            FileNotFoundError: If the embedding store base directory cannot be found.
        """
        # Construct path to embedding stores
        if data_dir is None:
            transcriptformer_data_path = os.getenv(
                "TRANSCRIPTFORMER_DATA_PATH", "/root/PrismDB"
            )
        else:
            transcriptformer_data_path = data_dir
        self.base_dir = os.path.join(
            transcriptformer_data_path, "transcriptformer_embedding", "embedding_store"
        )

        # Validate base directory exists
        if not os.path.exists(self.base_dir):
            raise FileNotFoundError(
                f"Transcriptformer embedding store directory not found at {self.base_dir}. Please check your TRANSCRIPTFORMER_DATA_PATH."
            )

        # Discover available disease-specific embedding stores
        self.available_diseases: List[str] = [
            d.lower().replace(" ", "_")
            for d in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, d))
        ]

        # Initialize metadata cache for performance optimization
        self.metadata_cache: Dict[str, Dict[str, Any]] = {}

        print(
            f"Transcriptformer tool initialized with {len(self.available_diseases)} disease contexts: {self.available_diseases}"
        )

    def _load_metadata(self, disease: str) -> Dict:
        """
        Load and cache metadata for a specific disease embedding store.

        This method loads comprehensive metadata including gene mappings, available
        cell types, disease states, and embedding matrix organization. Metadata
        is cached to avoid repeated file I/O operations for the same disease.

        Args:
            disease (str): Disease identifier (normalized to lowercase with underscores).

        Returns
            Dict: Cached metadata dictionary containing:
                - store_path: Path to disease-specific embedding store
                - ensembl_ids_ordered: Ordered list of Ensembl gene IDs
                - gene_to_idx: Mapping from Ensembl IDs to matrix indices
                - symbol_to_ensembl: Mapping from gene symbols to Ensembl IDs
                - available_symbols: Sorted list of available gene symbols
                - groups_meta: Metadata for available cell type + disease state combinations
                - available_cell_types: Sorted list of available cell types
                - available_states: Sorted list of available disease states

        Raises:
            FileNotFoundError: If disease is not available or metadata file is missing.
        """
        # Return cached metadata if already loaded
        if disease in self.metadata_cache:
            return self.metadata_cache[disease]

        # Validate disease availability
        if disease not in self.available_diseases:
            raise FileNotFoundError(
                f"Disease '{disease}' is not available. Please choose from available diseases: {self.available_diseases}"
            )

        # Construct paths to disease-specific store and metadata
        store_path = os.path.join(self.base_dir, disease.replace(" ", "_"))
        metadata_path = os.path.join(store_path, "metadata.json.gz")

        # Validate metadata file exists
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(
                f"Metadata file not found at: {metadata_path}. Please ensure embedding store is properly prepared."
            )

        # Load compressed metadata file
        print(
            f"Loading Transcriptformer metadata from embedding store: {os.path.basename(store_path)}..."
        )
        with gzip.open(metadata_path, "rt", encoding="utf-8") as f:
            metadata = json.load(f)

        # Process and cache metadata with normalized keys
        self.metadata_cache[disease] = {
            "store_path": store_path,
            "ensembl_ids_ordered": metadata["ensembl_ids_ordered"],
            "gene_to_idx": {
                gene: i for i, gene in enumerate(metadata["ensembl_ids_ordered"])
            },
            "symbol_to_ensembl": metadata["gene_map_symbol_to_ensembl"],
            "available_symbols": sorted(
                list(metadata["gene_map_symbol_to_ensembl"].keys())
            ),
            "groups_meta": {
                k.lower().replace(" ", "_"): v for k, v in metadata["groups"].items()
            },
            "available_cell_types": sorted(
                list(
                    set(
                        details["cell_type"].lower().replace(" ", "_")
                        for details in metadata["groups"].values()
                    )
                )
            ),
            "available_states": sorted(
                list(
                    set(
                        details["disease_state"].lower().replace(" ", "_")
                        for details in metadata["groups"].values()
                    )
                )
            ),
        }

        cached_data = self.metadata_cache[disease]
        print(
            f"Metadata loaded successfully: {len(cached_data['available_symbols'])} genes, "
            f"{len(cached_data['available_cell_types'])} cell types, "
            f"{len(cached_data['available_states'])} disease states."
        )

        return self.metadata_cache[disease]

    def get_embedding_for_context(
        self,
        state: str,
        cell_type: str,
        gene_names: Union[List[str], None],
        disease: str,
    ) -> Tuple[Optional[Dict[str, np.ndarray]], List[str]]:
        """
        Retrieve contextualized gene embeddings for specific cellular and disease contexts.

        This method loads pre-computed Transcriptformer embeddings that capture gene
        expression patterns in specific combinations of cell type and disease state.
        The embeddings are loaded on-demand from compressed numpy matrices for
        memory efficiency and fast access.

        Args:
            state (str): Disease state context (e.g., 'control', 'disease', 'treated').
                        Must be normalized (lowercase, underscores for spaces).
            cell_type (str): Cell type context (e.g., 'b_cell', 'macrophage', 'epithelial_cell').
                           Must be normalized (lowercase, underscores for spaces).
            gene_names (Union[List[str], None]): Gene identifiers to retrieve embeddings for.
                                               Can be gene symbols (e.g., 'TP53') or Ensembl IDs (e.g., 'ENSG00000141510').
                                               If None, returns embeddings for all available genes.
            disease (str): Disease context identifier (e.g., 'breast_cancer', 'diabetes').
                         Must match available disease stores.

        Returns
            Tuple[Optional[Dict[str, np.ndarray]], List[str]]: A tuple containing:
                - Dictionary mapping gene names to embedding vectors (None if failed)
                - List of context information and error messages

        The embedding vectors are float32 numpy arrays representing learned gene
        representations in the specified cellular context.
        """
        # Normalize input parameters for consistent matching
        disease = disease.lower().replace(" ", "_")
        state = state.lower().replace(" ", "_")
        cell_type = cell_type.lower().replace(" ", "_")

        # Load metadata for the specified disease
        metadata = self._load_metadata(disease)

        context_info = []
        embeddings = {}
        invalid_genes = []

        # Validate disease state parameter
        if state not in metadata["available_states"]:
            context_info.append(
                f"Invalid disease state '{state}'. Available states for {disease}: {metadata['available_states']}"
            )
            return None, context_info

        # Validate cell type parameter
        if cell_type not in metadata["available_cell_types"]:
            context_info.append(
                f"Invalid cell type '{cell_type}'. Available cell types for {disease}: {metadata['available_cell_types']}"
            )
            return None, context_info

        # Process gene names parameter (None means retrieve all genes)
        if gene_names is None:
            # Retrieve embeddings for all genes in this context
            print(
                f"Loading complete gene embedding set for context: {disease} - {state} - {cell_type}"
            )

            # Create gene mapping using symbols as primary keys when available
            for ensembl_id in metadata["ensembl_ids_ordered"]:
                # Find corresponding gene symbol for this Ensembl ID
                gene_symbol = None
                for symbol, ens_id in metadata["symbol_to_ensembl"].items():
                    if ens_id == ensembl_id:
                        gene_symbol = symbol
                        break

                # Use gene symbol as key if available, otherwise use Ensembl ID
                if gene_symbol:
                    embeddings[gene_symbol] = ensembl_id
                else:
                    embeddings[ensembl_id] = ensembl_id
        else:
            # Validate and process specific gene identifiers
            for gene_name in gene_names:
                ensembl_id = None

                # Check if input is an Ensembl ID (starts with 'ENSG')
                if gene_name.upper().startswith("ENSG"):
                    ensembl_id = gene_name.upper()
                    if ensembl_id not in metadata["gene_to_idx"]:
                        invalid_genes.append(gene_name)
                else:
                    # Treat as gene symbol and lookup corresponding Ensembl ID
                    ensembl_id = metadata["symbol_to_ensembl"].get(gene_name.upper())
                    if not ensembl_id:
                        invalid_genes.append(gene_name)

                # Add valid gene to embedding request
                if ensembl_id:
                    embeddings[gene_name] = ensembl_id

            # Report invalid gene identifiers
            if invalid_genes:
                context_info.append(
                    f"Invalid or unavailable gene identifiers: {invalid_genes}"
                )
                context_info.append(
                    f"Please use valid gene symbols or Ensembl IDs from the {disease} dataset."
                )

        # Check if any valid genes were found
        if not embeddings:
            return None, context_info

        # Construct group key for embedding matrix lookup
        # Format: celltype_diseasestate (normalized, no special characters)
        group_key = (
            f"{cell_type}_{state}".replace(" ", "_").replace("(", "").replace(")", "")
        )

        # Validate that the requested context combination exists
        if group_key not in metadata["groups_meta"]:
            available_keys = list(metadata["groups_meta"].keys())
            context_info.append(
                f"Context combination not available: state='{state}', cell_type='{cell_type}'"
            )
            context_info.append(
                f"Available context combinations for {disease}: {available_keys}"
            )
            return None, context_info

        # Load embedding matrix on-demand from compressed numpy file
        npy_path = os.path.join(metadata["store_path"], f"{group_key}.npy")
        if not os.path.exists(npy_path):
            context_info.append(
                f"Embedding matrix file not found for context '{group_key}' at {npy_path}"
            )
            return None, context_info

        print(f"Loading embedding matrix for context: {group_key}")
        embedding_matrix = np.load(npy_path)

        # Extract embeddings for requested genes
        final_embeddings = {}
        for gene_name, ensembl_id in embeddings.items():
            gene_idx = metadata["gene_to_idx"].get(ensembl_id)
            if gene_idx is not None:
                # Extract and dequantize embedding vector to float32
                embedding_vector = embedding_matrix[gene_idx].astype(np.float32)
                final_embeddings[gene_name] = embedding_vector

        # Add success information to context
        context_info.append(
            f"Successfully retrieved {len(final_embeddings)} gene embeddings for context: {disease} - {state} - {cell_type}"
        )
        if len(final_embeddings) > 0:
            embedding_dim = final_embeddings[next(iter(final_embeddings))].shape[0]
            context_info.append(
                f"Embedding dimensionality: {embedding_dim} features per gene"
            )

        return final_embeddings, context_info


@server.tool()
async def run_transcriptformer_embedding_retrieval(
    state: str,
    cell_type: str,
    gene_names: List[str],
    disease: str,
    data_dir: Optional[str] = None,
):
    """
    MCP Tool: Retrieves contextualized gene embeddings from Transcriptformer models.

    This tool provides access to pre-computed Transcriptformer embeddings that capture
    gene expression patterns learned from single-cell RNA sequencing data. The embeddings
    are contextualized for specific combinations of disease states and cell types,
    enabling precise analysis of gene behavior in relevant biological contexts.

    Scientific Background:
    - Transcriptformer uses transformer architecture to learn gene representations
    - Embeddings capture cell-type-specific and disease-state-specific expression patterns
    - Model trained on large-scale single-cell RNA-seq datasets
    - Dense vector representations enable similarity analysis and downstream ML applications

    Applications:
    - Gene similarity analysis and functional annotation
    - Biomarker discovery and validation in disease contexts
    - Pathway analysis and systems biology research
    - Drug target identification and prioritization
    - Precision medicine and personalized therapeutics
    - Co-expression network analysis

    Technical Details:
    - Embeddings stored as compressed numpy matrices for efficient access
    - On-demand loading minimizes memory usage
    - Supports both gene symbols and Ensembl ID inputs
    - Float32 precision for optimal balance of accuracy and efficiency

    Args:
        state (str): Disease state context for embedding retrieval. Examples:
                    - 'control': Healthy/normal condition
                    - 'disease': Disease-affected state
                    - 'treated': Post-treatment condition
                    - 'untreated': Pre-treatment condition
                    Must match available states in the disease-specific store.

        cell_type (str): Cell type context for embeddings. Examples:
                    - 'b_cell': B lymphocytes
                    - 't_cell': T lymphocytes
                    - 'macrophage': Tissue macrophages
                    - 'epithelial_cell': Epithelial cells
                    - 'fibroblast': Connective tissue fibroblasts
                    Must match available cell types in the disease store.

        gene_names (List[str]): Gene identifiers for embedding retrieval:
                            - Gene symbols: ['TP53', 'BRCA1', 'EGFR', 'MYC']
                            - Ensembl IDs: ['ENSG00000141510', 'ENSG00000139618']
                            - Mixed formats supported
                            - Empty list retrieves all available genes

        disease (str): Disease/dataset identifier. Examples:
                    - 'breast_cancer': Breast cancer scRNA-seq data
                    - 'lung_cancer': Lung cancer contexts
                    - 'diabetes': Diabetes-related datasets
                    - 'alzheimer': Alzheimer's disease contexts
                    Must match available disease stores.

    Returns
        dict: Comprehensive embedding retrieval results containing:
            - 'embeddings' (dict, optional): Gene-to-embedding mapping where:
                * Keys: Gene identifiers (symbols or Ensembl IDs as provided)
                * Values: Embedding vectors as lists of float32 values
                Only present when embeddings are successfully retrieved.
            - 'context_info' (list): Detailed retrieval information including:
                * Validation results and parameter processing
                * Number of genes processed and embedding dimensions
                * Warnings about invalid gene identifiers
                * Context combination availability
            - 'error' (str, optional): Error description if retrieval failed

    Example Usage:
        # Retrieve specific cancer-related genes in breast cancer B cells
        result = await run_transcriptformer_embedding_retrieval(
            state="disease",
            cell_type="b_cell",
            gene_names=["TP53", "BRCA1", "EGFR", "MYC"],
            disease="breast_cancer"
        )

        # Get all gene embeddings for control hepatocytes
        result = await run_transcriptformer_embedding_retrieval(
            state="control",
            cell_type="hepatocyte",
            gene_names=[],
            disease="liver_disease"
        )

        # Mixed gene identifier formats
        result = await run_transcriptformer_embedding_retrieval(
            state="treated",
            cell_type="t_cell",
            gene_names=["CD8A", "ENSG00000153563", "IFNG"],
            disease="immunotherapy_response"
        )
    """

    # Generate unique request ID for tracking and logging
    request_id = str(uuid.uuid4())[:8]
    print(
        f"[{request_id}] Received Transcriptformer embedding retrieval request for {disease} - {state} - {cell_type}"
    )

    # Set default data directory if not provided
    if data_dir is None:
        data_dir = os.getenv("TRANSCRIPTFORMER_DATA_PATH", "/root/PrismDB")

    # Initialize global Transcriptformer tool instance for MCP server
    # This instance will be used by the MCP tool function to serve embedding requests
    try:
        transcriptformer_tool = TranscriptformerEmbeddingTool(data_dir=data_dir)
        print("Transcriptformer tool instance created and ready for MCP server")
    except Exception as e:
        print(f"Error creating Transcriptformer tool: {str(e)}")
        print(
            "Please ensure TRANSCRIPTFORMER_DATA_PATH is correctly set and embedding stores exist."
        )
        raise e

    try:
        # Brief async pause to allow for proper request handling
        await asyncio.sleep(0.1)

        # Validate input parameters
        if not disease or not disease.strip():
            raise ValueError(
                "Disease parameter cannot be empty. Please specify a valid disease identifier."
            )
        if not state or not state.strip():
            raise ValueError(
                "State parameter cannot be empty. Please specify a valid disease state."
            )
        if not cell_type or not cell_type.strip():
            raise ValueError(
                "Cell type parameter cannot be empty. Please specify a valid cell type."
            )

        print(
            f"[{request_id}] Processing embedding retrieval for {len(gene_names) if gene_names else 'all'} genes"
        )

        # Execute Transcriptformer embedding retrieval
        embeddings, context_info = transcriptformer_tool.get_embedding_for_context(
            state=state.strip(),
            cell_type=cell_type.strip(),
            gene_names=gene_names if gene_names else None,
            disease=disease.strip(),
        )

        # Handle retrieval failure
        if embeddings is None:
            print(
                f"[{request_id}] Embedding retrieval failed for context: {disease} - {state} - {cell_type}"
            )
            return {
                "error": "Failed to retrieve Transcriptformer embeddings for specified context",
                "context_info": context_info
                + [
                    "Please verify disease, state, and cell type parameters.",
                    "Check available contexts using the tool's metadata.",
                ],
            }

        # Convert numpy arrays to JSON-serializable lists
        # This enables downstream processing and API compatibility
        serializable_embeddings = {}
        for gene_name, embedding_vector in embeddings.items():
            serializable_embeddings[gene_name] = embedding_vector.tolist()

        # Log successful completion with key metrics
        num_genes = len(serializable_embeddings)
        embedding_dim = (
            len(next(iter(serializable_embeddings.values())))
            if serializable_embeddings
            else 0
        )
        print(
            f"[{request_id}] Transcriptformer embedding retrieval completed: {num_genes} genes, {embedding_dim}D embeddings"
        )

        return {
            "embeddings": serializable_embeddings,
            "context_info": context_info
            + [
                f"Embedding retrieval completed for {num_genes} genes.",
                f"Context: {disease} - {state} - {cell_type}",
                f"Embedding dimensionality: {embedding_dim} features per gene.",
            ],
        }

    except ValueError as e:
        error_message = (
            f"Transcriptformer embedding retrieval validation error: {str(e)}"
        )
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": ["Please verify input parameters and available contexts."],
        }
    except Exception as e:
        error_message = (
            f"Unexpected error during Transcriptformer embedding retrieval: {str(e)}"
        )
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": [
                "Internal server error occurred during embedding retrieval."
            ],
        }


if __name__ == "__main__":
    print("Starting MCP server for Transcriptformer Gene Embedding Tool...")
    print("Model: Transcriptformer (Transformer-based gene representation learning)")
    print("Application: Contextualized gene embedding retrieval from single-cell data")
    print("Features: Disease-specific and cell-type-specific gene representations")
    print("Server: FastMCP with streamable HTTP transport")
    print("Port: 7000 (configured for biomedical embedding services)")
    print("Timeout: Extended for large embedding matrix operations")

    # Launch the MCP server with Transcriptformer embedding capabilities
    # Extended timeout for handling large embedding matrices
    server.run(
        transport="streamable-http", host="0.0.0.0", port=7000, stateless_http=True
    )
