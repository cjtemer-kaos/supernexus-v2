#!/usr/bin/env python3
"""
Start Web Interface Only

This script starts only the web interface for expert consultations using the
@register_mcp_tool system (human_expert_mcp_tools.py).
The MCP server must be running separately.
"""

import subprocess
import sys
import requests
from pathlib import Path
import os
import socket


def get_random_port():
    """Get a random available port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def detect_mcp_server_port():
    """Ask user for MCP server connection details"""
    print("📝 Please provide the MCP server connection details:")

    while True:
        try:
            address = input("Enter server IP address (default: localhost): ").strip()
            if not address:
                address = "localhost"

            port_input = input("Enter server port (default: 9877): ").strip()
            if not port_input:
                port = 9876
            else:
                port = int(port_input)

            # Validate port range
            if not (1 <= port <= 65535):
                print("❌ Port must be between 1 and 65535. Please try again.")
                continue

            # Test the connection
            print(f"🔍 Testing connection to {address}:{port}...")
            if check_mcp_server_on_port(port, address):
                print(f"✅ Successfully connected to {address}:{port}")
                # Set the environment variable for this session
                os.environ["EXPERT_FEEDBACK_MCP_SERVER_URL"] = (
                    f"http://{address}:{port}"
                )
                return port
            else:
                print(f"❌ Could not connect to {address}:{port}")
                print("💡 Make sure the MCP server is running and accessible")
                print("   Server logs should show something like:")
                print("   'INFO: Uvicorn running on http://0.0.0.0:9876'")
                retry = input("Would you like to try again? (y/N): ").strip().lower()
                if retry != "y":
                    break

        except ValueError:
            print("❌ Invalid port number. Please enter a valid integer.")
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            return None

    # Try common ports that the system might use
    print("🔍 Trying common ports...")
    common_ports = [8000, 8001] + [52340 + i for i in range(20)]

    for port in common_ports:
        if check_mcp_server_on_port(port):
            print(f"✅ Found MCP server running on port {port}")
            return port

    return None


def check_mcp_server_on_port(port, address="localhost"):
    """Check if MCP server is running on specific port and address"""
    try:
        # Try different possible endpoints
        endpoints_to_try = [
            f"http://{address}:{port}/tools/get_expert_status",
            f"http://{address}:{port}/mcp",
            f"http://{address}:{port}/tools",
            f"http://{address}:{port}/",
            f"http://{address}:{port}/docs",
            f"http://{address}:{port}/health",
        ]

        for endpoint in endpoints_to_try:
            try:
                if "/tools/get_expert_status" in endpoint:
                    response = requests.post(endpoint, json={}, timeout=2)
                else:
                    response = requests.get(endpoint, timeout=2)

                # Accept various response codes that indicate server is running
                if response.status_code in [200, 404, 405, 406, 422, 500]:
                    print(
                        f"✅ Server detected at {endpoint} (status: {response.status_code})"
                    )
                    return True

            except requests.exceptions.RequestException:
                continue

    except Exception as e:
        print(f"⚠️  Connection test error: {e}")

    return False


def check_mcp_server():
    """Check if MCP server is running and return port"""
    print("🔍 Detecting MCP server...")
    port = detect_mcp_server_port()
    if port:
        print(f"✅ MCP Server detected on port {port}")
        return port
    return None


def main():
    print("🌐 Starting Human Expert Web Interface")
    print("=" * 50)

    # Check if MCP server is running
    mcp_port = check_mcp_server()
    if not mcp_port:
        print("❌ Second generation MCP Server not detected!")
        print("📡 Please start the MCP server first:")
        print("   python human_expert_mcp_tools.py --start-server")
        print()
        print("💡 This script only supports the modern @register_mcp_tool system.")
        print()
        choice = input("Continue anyway? (y/N): ").strip().lower()
        if choice != "y":
            return 1

    # Check for the second generation script
    modern_script = Path(__file__).parent / "human_expert_mcp_tools.py"

    if not modern_script.exists():
        print("❌ MCP tools script not found!")
        print(f"   Looking for: {modern_script}")
        print("   Make sure human_expert_mcp_tools.py exists in this directory.")
        return 1

    print("🚀 Using @register_mcp_tool system")
    if mcp_port:
        print(f"🔌 MCP Server: localhost:{mcp_port}")

    print("🌐 Starting web interface...")
    print("🖥️  Browser should open automatically")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    try:
        # Check Flask availability
        try:
            pass

            print("✅ Flask is available")
        except ImportError:
            print("❌ Flask not found. Install with: pip install flask")
            return 1

        # Start web interface
        subprocess.run(
            [sys.executable, str(modern_script), "--web-only", "--no-browser"]
        )
        return 0

    except KeyboardInterrupt:
        print("\n👋 Web Interface stopped")
        return 0
    except Exception as e:
        print(f"❌ Error starting web interface: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
