#!/usr/bin/env python3
"""
CLI agent with tools for documentation lookup.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with "answer", "source", and "tool_calls" fields to stdout.
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Load configuration from .env.agent.secret file."""
    env_path = Path(__file__).parent / ".env.agent.secret"

    if not env_path.exists():
        print(f"Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_path)

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key:
        print("Error: LLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not set", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: LLM_MODEL not set", file=sys.stderr)
        sys.exit(1)

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def is_safe_path(path: str) -> bool:
    """
    Check if a path is safe (no directory traversal).

    Args:
        path: Relative path from project root

    Returns:
        True if path is safe, False otherwise
    """
    # Block path traversal
    if ".." in path:
        return False
    # Block absolute paths
    if path.startswith("/"):
        return False
    return True


def read_file(path: str) -> str:
    """
    Read the contents of a file.

    Args:
        path: Relative path from project root

    Returns:
        File contents as string, or error message
    """
    if not is_safe_path(path):
        return f"Error: Access denied - path traversal not allowed: {path}"

    project_root = get_project_root()
    file_path = project_root / path

    if not file_path.exists():
        return f"Error: File not found: {path}"

    if not file_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root

    Returns:
        Newline-separated listing of entries, or error message
    """
    if not is_safe_path(path):
        return f"Error: Access denied - path traversal not allowed: {path}"

    project_root = get_project_root()
    dir_path = project_root / path

    if not dir_path.exists():
        return f"Error: Directory not found: {path}"

    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        entries = sorted(dir_path.iterdir())
        # Filter out hidden files and __pycache__
        visible = [
            e.name
            for e in entries
            if not e.name.startswith(".") and e.name != "__pycache__"
        ]
        return "\n".join(visible)
    except Exception as e:
        return f"Error listing directory: {e}"


# Tool registry
TOOLS = {
    "read_file": {
        "schema": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')",
                    }
                },
                "required": ["path"],
            },
        },
        "function": read_file,
    },
    "list_files": {
        "schema": {
            "name": "list_files",
            "description": "List files and directories at a given path in the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')",
                    }
                },
                "required": ["path"],
            },
        },
        "function": list_files,
    },
}


def get_tool_schemas() -> list:
    """Get list of tool schemas for LLM function calling."""
    return [tool["schema"] for tool in TOOLS.values()]


def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool

    Returns:
        Tool result as string
    """
    if tool_name not in TOOLS:
        return f"Error: Unknown tool: {tool_name}"

    tool = TOOLS[tool_name]
    func = tool["function"]

    try:
        # Extract arguments
        path = args.get("path", "")
        return func(path)
    except Exception as e:
        return f"Error executing tool: {e}"


# ---------------------------------------------------------------------------
# LLM Communication
# ---------------------------------------------------------------------------


def call_llm(messages: list, config: dict, tool_schemas: list = None) -> dict:
    """
    Call the LLM API with messages and optional tool schemas.

    Args:
        messages: List of message dicts (role, content)
        config: Configuration dict
        tool_schemas: Optional list of tool schemas

    Returns:
        Parsed LLM response dict
    """
    url = f"{config['api_base']}/chat/completions"

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    body = {
        "model": config["model"],
        "messages": messages,
    }

    # Add tool schemas if provided
    if tool_schemas:
        body["tools"] = tool_schemas

    print(f"Calling LLM at {url}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Agentic Loop
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = """You are a documentation assistant for a software engineering lab.

You have access to two tools:
1. list_files - List files and directories at a given path
2. read_file - Read the contents of a file

When answering questions about the project:
1. First use list_files to discover relevant wiki files (start with "wiki" directory)
2. Then use read_file to read specific files and find the answer
3. Always cite your source as "wiki/filename.md#section-anchor" where section-anchor is the relevant section
4. Only give your final answer after gathering enough information from the files

If the question is not about project documentation, answer directly without using tools.

Be concise and helpful in your responses."""


MAX_ITERATIONS = 10


def run_agentic_loop(question: str, config: dict) -> tuple:
    """
    Run the agentic loop to answer a question using tools.

    Args:
        question: User's question
        config: Configuration dict

    Returns:
        Tuple of (answer, source, tool_calls_list)
    """
    # Initialize messages with system prompt and user question
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_schemas = get_tool_schemas()
    tool_calls_list = []
    answer = ""
    source = ""

    print(f"Starting agentic loop for question: {question}", file=sys.stderr)

    for iteration in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {iteration + 1}/{MAX_ITERATIONS} ---", file=sys.stderr)

        # Call LLM
        response = call_llm(messages, config, tool_schemas)

        # Parse response
        choice = response["choices"][0]
        message = choice["message"]

        # Check for tool calls
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            # Execute tools
            print(f"LLM requested {len(tool_calls)} tool call(s)", file=sys.stderr)

            for tool_call in tool_calls:
                # Extract tool info (OpenAI-compatible format)
                function = tool_call.get("function", {})
                tool_name = function.get("name", "unknown")

                try:
                    args = json.loads(function.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {"path": function.get("arguments", "")}

                print(
                    f"  Executing tool: {tool_name} with args: {args}", file=sys.stderr
                )

                # Execute tool
                result = execute_tool(tool_name, args)

                # Record tool call
                tool_calls_list.append(
                    {
                        "tool": tool_name,
                        "args": args,
                        "result": result,
                    }
                )

                # Append tool result to messages
                messages.append(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": result,
                        "tool_call_id": tool_call.get("id", "unknown"),
                    }
                )

            # Continue loop - LLM will process tool results
            continue

        else:
            # No tool calls - LLM provided final answer
            answer = message.get("content", "")
            print(f"LLM provided final answer", file=sys.stderr)
            break
    else:
        # Max iterations reached
        print(f"Warning: Max iterations ({MAX_ITERATIONS}) reached", file=sys.stderr)
        if not answer:
            answer = (
                "I was unable to find a complete answer within the iteration limit."
            )

    # Extract source from answer (look for wiki/*.md patterns)
    import re

    source_match = re.search(r"wiki/[\w-]+\.md(?:#[\w-]+)?", answer)
    if source_match:
        source = source_match.group()
    elif tool_calls_list:
        # Use the last read_file as source
        for tc in reversed(tool_calls_list):
            if tc["tool"] == "read_file" and not tc["result"].startswith("Error"):
                source = tc["args"].get("path", "")
                break

    return answer, source, tool_calls_list


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "Your question here"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    print(f"Question: {question}", file=sys.stderr)

    # Load configuration
    config = load_config()

    # Run agentic loop
    answer, source, tool_calls_list = run_agentic_loop(question, config)

    # Format output
    output = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_list,
    }

    # Print JSON to stdout
    print(json.dumps(output))


if __name__ == "__main__":
    main()
