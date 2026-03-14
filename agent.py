#!/usr/bin/env python3
"""
CLI agent that connects to an LLM and answers questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with "answer" and "tool_calls" fields to stdout.
"""

import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os


def load_config() -> dict:
    """Load configuration from .env.agent.secret file."""
    # Find .env.agent.secret in the project root
    env_path = Path(__file__).parent / ".env.agent.secret"
    
    if not env_path.exists():
        print(f"Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)
    
    # Load environment variables from the file
    load_dotenv(env_path)
    
    # Read required configuration
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")
    
    # Validate configuration
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


def call_llm(question: str, config: dict) -> str:
    """
    Call the LLM API and return the answer.
    
    Args:
        question: The user's question
        config: Configuration dict with api_key, api_base, model
        
    Returns:
        The LLM's answer as a string
    """
    url = f"{config['api_base']}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    
    body = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": question}
        ],
    }
    
    print(f"Calling LLM at {url}...", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            
            # Extract answer from response
            answer = data["choices"][0]["message"]["content"]
            return answer
            
    except httpx.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Unexpected response format: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    # Parse command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    print(f"Question: {question}", file=sys.stderr)
    
    # Load configuration
    config = load_config()
    
    # Call LLM and get answer
    answer = call_llm(question, config)
    
    # Format and print output
    output = {
        "answer": answer,
        "tool_calls": [],
    }
    
    # Print JSON to stdout (only valid JSON, no extra text)
    print(json.dumps(output))


if __name__ == "__main__":
    main()
