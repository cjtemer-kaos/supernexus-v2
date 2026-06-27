#!/usr/bin/env python3
"""
List Azure OpenAI deployments (deployed models) for the current resource.

Environment variables used:
- AZURE_OPENAI_ENDPOINT (required)  e.g., https://<your-resource>.openai.azure.com
- AZURE_OPENAI_API_KEY (required)
- AZURE_OPENAI_API_VERSION (optional; default: 2024-12-01-preview)

This script queries the Azure OpenAI data-plane deployments endpoint:
  GET {endpoint}/openai/deployments?api-version={api_version}
It also tries alternative paths and versions if the first attempt fails.
If REST fails, it falls back to listing models via the SDK (client.models.list()).

CLI options:
  --rest-only       Only use REST
  --sdk-only        Only use SDK fallback
  --raw             Print raw JSON result for REST (when available)
  --versions v1 v2  Override API versions to try (space-separated)
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests


DEFAULT_VERSIONS = [
    # Common recent versions
    "2024-12-01-preview",
    "2024-10-21",
    # Add more if needed
]


def try_rest_once(
    endpoint: str, api_key: str, api_version: str, path_variant: str
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]], Optional[str]]:
    url = endpoint.rstrip("/") + f"{path_variant}?api-version={api_version}"
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") or data.get("value") or []
        deployments: List[Dict[str, Any]] = []
        for item in items:
            deployments.append(
                {
                    "id": item.get("id") or item.get("name"),
                    "name": item.get("name") or item.get("id"),
                    "model": (
                        (item.get("model") or {}).get("name")
                        if isinstance(item.get("model"), dict)
                        else item.get("model")
                    ),
                    "model_format": item.get("model_format"),
                    "created": item.get("created"),
                    "status": item.get("status")
                    or item.get("provisioningState")
                    or item.get("provisioning_state"),
                    "properties": item.get("properties"),
                }
            )
        return deployments, data, None
    except Exception as e:
        return None, None, f"{e} (url: {url})"


def list_deployments_via_rest(
    endpoint: str, api_key: str, versions: List[str]
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    raw: Optional[Dict[str, Any]] = None
    # Try two common path variants
    path_variants = ["/openai/deployments", "/deployments"]
    for v in versions:
        for pv in path_variants:
            deployments, raw_json, err = try_rest_once(endpoint, api_key, v, pv)
            if deployments is not None:
                raw = raw_json
                return deployments, raw, errors
            if err:
                errors.append(f"{v} {pv}: {err}")
    return [], raw, errors


def list_models_via_sdk(
    endpoint: str, api_key: str, api_version: str
) -> List[Dict[str, Any]]:
    try:
        from openai import AzureOpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Failed to import openai AzureOpenAI client: %s" % e)

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    resp = client.models.list()
    data = getattr(resp, "data", None) or []
    models: List[Dict[str, Any]] = []
    for m in data:
        models.append(
            {
                "id": getattr(m, "id", None) or getattr(m, "root", None),
                "owned_by": getattr(m, "owned_by", None),
                "created": getattr(m, "created", None),
            }
        )
    return models


def main() -> None:
    parser = argparse.ArgumentParser(description="List Azure OpenAI deployments/models")
    parser.add_argument("--rest-only", action="store_true", help="Use REST only")
    parser.add_argument("--sdk-only", action="store_true", help="Use SDK only")
    parser.add_argument(
        "--raw", action="store_true", help="Print raw JSON from REST when available"
    )
    parser.add_argument(
        "--versions", nargs="*", help="API versions to try for REST (override)"
    )
    args = parser.parse_args()

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    env_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not endpoint or not api_key:
        print("ERROR: Missing required environment variables.")
        print(" - AZURE_OPENAI_ENDPOINT (current: %s)" % (endpoint or "<unset>"))
        print(
            " - AZURE_OPENAI_API_KEY (current: %s)"
            % ("<set>" if api_key else "<unset>")
        )
        sys.exit(1)

    versions = (
        args.versions
        if args.versions
        else ([env_version] if env_version else DEFAULT_VERSIONS)
    )

    print("Listing Azure OpenAI deployments for resource:")
    print(f" - Endpoint : {endpoint}")
    print(f" - Versions : {', '.join([v for v in versions if v])}")
    print()

    deployments: List[Dict[str, Any]] = []
    rest_errors: List[str] = []
    raw: Optional[Dict[str, Any]] = None

    if not args.sdk_only:
        deployments, raw, rest_errors = list_deployments_via_rest(
            endpoint, api_key, [v for v in versions if v]
        )
        if deployments:
            print(f"Found {len(deployments)} deployment(s) via REST:")
            for d in deployments:
                print("- Deployment:")
                print(f"    name   : {d.get('name')}")
                print(f"    id     : {d.get('id')}")
                print(f"    model  : {d.get('model')}")
                print(f"    status : {d.get('status')}")
            if args.raw and raw is not None:
                print("\nRaw JSON (REST):")
                print(json.dumps(raw, indent=2, ensure_ascii=False))
            print(
                "\nTip: Use the 'name' (deployment name) as model_id in your requests."
            )
            return
        else:
            print("No deployments found via REST or REST not available.")
            if rest_errors:
                print("\nREST attempt details (for debugging):")
                for e in rest_errors[:5]:  # limit output
                    print(" -", e)
            print()

    if not args.rest_only:
        api_version_for_sdk = env_version or DEFAULT_VERSIONS[0]
        try:
            models = list_models_via_sdk(endpoint, api_key, api_version_for_sdk)
            if models:
                print(f"Found {len(models)} model(s) via SDK:")
                for m in models[:200]:
                    print("- Model (SDK):")
                    print(f"    id      : {m.get('id')}")
                    if m.get("owned_by") is not None:
                        print(f"    owned_by: {m.get('owned_by')}")
                    if m.get("created") is not None:
                        print(f"    created : {m.get('created')}")
                print()
                print(
                    "Note: SDK list may show global IDs; real calls require the deployment name."
                )
            else:
                print("No models found via SDK either.")
        except Exception as e:
            print("ERROR: Unable to list models via SDK: %s" % e)
            sys.exit(2)


if __name__ == "__main__":
    main()
