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


def query_api(
    method: str, path: str, body: str = None, include_auth: bool = True
) -> str:
    """
    Call the deployed backend API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path (e.g., '/items/')
        body: JSON request body for POST/PUT (optional)
        include_auth: Whether to include LMS_API_KEY in Authorization header (default: True)

    Returns:
        JSON string with status_code and body, or error message
    """
    # Read configuration from environment
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.getenv("LMS_API_KEY")

    if not lms_api_key:
        # Try to load from .env.docker.secret
        docker_env_path = Path(__file__).parent / ".env.docker.secret"
        if docker_env_path.exists():
            load_dotenv(docker_env_path)
            lms_api_key = os.getenv("LMS_API_KEY")

    if include_auth and not lms_api_key:
        return "Error: LMS_API_KEY not set in environment"

    # Build URL
    url = f"{base_url}{path}"

    headers = {
        "Content-Type": "application/json",
    }

    # Only include Authorization header if requested
    if include_auth and lms_api_key:
        headers["Authorization"] = f"Bearer {lms_api_key}"

    print(f"Calling API: {method} {url} (auth: {include_auth})", file=sys.stderr)

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                json_body = json.loads(body) if body else None
                response = client.post(url, headers=headers, json=json_body)
            elif method.upper() == "PUT":
                json_body = json.loads(body) if body else None
                response = client.put(url, headers=headers, json=json_body)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            elif method.upper() == "PATCH":
                json_body = json.loads(body) if body else None
                response = client.patch(url, headers=headers, json=json_body)
            else:
                return f"Error: Unsupported method: {method}"

            # Return JSON string with status_code and body
            result = {
                "status_code": response.status_code,
                "body": response.text,
            }
            return json.dumps(result)

    except httpx.HTTPError as e:
        return f"Error: HTTP request failed: {e}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON body: {e}"
    except Exception as e:
        return f"Error: API call failed: {e}"


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
    "query_api": {
        "schema": {
            "name": "query_api",
            "description": "Call the deployed backend API to fetch data or check endpoints. Use include_auth=false to test unauthenticated access.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/scores')",
                    },
                    "body": {
                        "type": "string",
                        "description": "JSON request body for POST/PUT (optional)",
                    },
                    "include_auth": {
                        "type": "boolean",
                        "description": "Whether to include authentication header (default: true). Set to false to test unauthenticated access.",
                    },
                },
                "required": ["method", "path"],
            },
        },
        "function": query_api,
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
        # Execute based on tool type
        if tool_name == "query_api":
            method = args.get("method", "GET")
            path = args.get("path", "")
            body = args.get("body")
            # Handle both boolean and string values for include_auth
            include_auth_raw = args.get("include_auth", True)
            if isinstance(include_auth_raw, bool):
                include_auth = include_auth_raw
            elif isinstance(include_auth_raw, str):
                include_auth = include_auth_raw.lower() != "false"
            else:
                include_auth = bool(include_auth_raw)
            return func(method, path, body, include_auth)
        elif tool_name in ("read_file", "list_files"):
            path = args.get("path", "")
            return func(path)
        else:
            return f"Error: Unknown tool type: {tool_name}"
    except Exception as e:
        return f"Error executing tool: {e}"


# ---------------------------------------------------------------------------
# LLM Communication with Retry Logic
# ---------------------------------------------------------------------------


MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1


def call_llm_with_retry(
    messages: list, config: dict, tool_schemas: list = None
) -> dict:
    """
    Call the LLM API with exponential backoff retry logic.

    Retries on:
    - 429 Too Many Requests (rate limit)
    - 5xx Server Errors

    Args:
        messages: List of message dicts (role, content)
        config: Configuration dict
        tool_schemas: Optional list of tool schemas

    Returns:
        Parsed LLM response dict

    Raises:
        SystemExit: If all retries fail
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

    for attempt in range(MAX_RETRIES + 1):
        print(
            f"Calling LLM at {url}... (attempt {attempt + 1}/{MAX_RETRIES + 1})",
            file=sys.stderr,
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=body)

                # Check for rate limit or server error
                if response.status_code == 429:
                    if attempt < MAX_RETRIES:
                        backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                        print(
                            f"Rate limit hit (429). Retrying in {backoff}s...",
                            file=sys.stderr,
                        )
                        import time

                        time.sleep(backoff)
                        continue
                    else:
                        print("Max retries exceeded for rate limit", file=sys.stderr)
                        sys.exit(1)

                elif response.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                        print(
                            f"Server error ({response.status_code}). Retrying in {backoff}s...",
                            file=sys.stderr,
                        )
                        import time

                        time.sleep(backoff)
                        continue
                    else:
                        print(f"Max retries exceeded for server error", file=sys.stderr)
                        sys.exit(1)

                # Success or client error (4xx)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            if attempt < MAX_RETRIES:
                backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                print(f"HTTP error: {e}. Retrying in {backoff}s...", file=sys.stderr)
                import time

                time.sleep(backoff)
            else:
                print(f"HTTP error: {e}", file=sys.stderr)
                sys.exit(1)

    # Should not reach here, but just in case
    print("Unexpected error in LLM call", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Agentic Loop with Caching
# ---------------------------------------------------------------------------


class ToolCache:
    """In-memory cache for tool results."""

    def __init__(self):
        self._cache = {}

    def _make_key(self, tool_name: str, args: dict) -> str:
        """Create a cache key from tool name and arguments."""
        import json

        # Sort args for consistent keys
        args_str = json.dumps(args, sort_keys=True)
        return f"{tool_name}:{args_str}"

    def get(self, tool_name: str, args: dict) -> str | None:
        """Get cached result if exists."""
        key = self._make_key(tool_name, args)
        return self._cache.get(key)

    def set(self, tool_name: str, args: dict, result: str) -> None:
        """Cache a tool result."""
        key = self._make_key(tool_name, args)
        self._cache[key] = result
        print(f"  [CACHE] Stored result for {tool_name}", file=sys.stderr)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()


def execute_tool_cached(tool_name: str, args: dict, cache: ToolCache) -> str:
    """
    Execute a tool with caching.

    Args:
        tool_name: Name of the tool
        args: Tool arguments
        cache: ToolCache instance

    Returns:
        Tool result (from cache or fresh)
    """
    # Check cache first
    cached_result = cache.get(tool_name, args)
    if cached_result is not None:
        print(f"  [CACHE HIT] {tool_name} with args {args}", file=sys.stderr)
        return cached_result

    # Execute tool and cache result
    result = execute_tool(tool_name, args)
    cache.set(tool_name, args, result)
    return result


SYSTEM_PROMPT = """You are a documentation and system assistant for a software engineering lab.

You have access to three tools:
1. list_files - List files and directories at a given path
2. read_file - Read the contents of a file
3. query_api - Call the deployed backend API to fetch data or check endpoints

Tool selection guidelines:
- Use list_files to discover project structure (e.g., list files in wiki/ or backend/)
- Use read_file to read documentation (wiki/), source code (backend/), or config files (docker-compose.yml, etc.)
- Use query_api to:
  - Get live data from the database (item counts, scores, analytics)
  - Check HTTP status codes
  - Test API endpoints
  - Diagnose API errors

When using query_api:
- Always specify both "method" (e.g., "GET") and "path" (e.g., "/items/") parameters
- Common endpoints: /items/, /analytics/scores, /analytics/completion-rate
- The path must start with /
- Example: {"method": "GET", "path": "/items/"}
- Use include_auth=false to test unauthenticated access (e.g., check 401 status codes)

When answering questions:
1. First understand what type of question it is:
   - Wiki/documentation question → use list_files on wiki/, then read_file on relevant files
   - Source code question → use list_files on backend/app/, then read_file on specific files
   - Live data question → use query_api with correct endpoint
   - Bug diagnosis → use query_api first to reproduce error, then read_file on error location

2. For backend structure questions:
   - List files in backend/app/ to see the structure
   - List files in backend/app/routers/ to find API modules
   - Read each router file to understand its domain

3. Always cite your source:
   - Wiki files: "wiki/filename.md#section"
   - Source files: "backend/path/to/file.py"
   - API data: "API endpoint /path/"

4. For bug diagnosis:
   - First reproduce the error with query_api
   - Then read the source code at the error location
   - Explain the root cause and suggest a fix

5. Avoid infinite loops:
   - Don't call list_files on the same path twice
   - After listing files, read the relevant ones
   - If you've made 5+ tool calls without progress, provide your best answer

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

    # Initialize cache for this agent run
    cache = ToolCache()

    print(f"Starting agentic loop for question: {question}", file=sys.stderr)

    for iteration in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {iteration + 1}/{MAX_ITERATIONS} ---", file=sys.stderr)

        # Call LLM with retry logic
        response = call_llm_with_retry(messages, config, tool_schemas)

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

                # Execute tool with caching
                result = execute_tool_cached(tool_name, args, cache)

                # Record tool call
                tool_calls_list.append(
                    {
                        "tool": tool_name,
                        "args": args,
                        "result": result,
                    }
                )

                # Append tool result to messages as user message with tool output
                # Qwen-compatible format: use "user" role instead of "tool"
                messages.append(
                    {
                        "role": "user",
                        "content": f"[{tool_name} result]: {result}",
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
