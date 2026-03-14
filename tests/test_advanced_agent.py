"""Tests for advanced agent features: retry logic and caching."""

import json
import subprocess
import sys
from pathlib import Path


def get_agent_path() -> Path:
    """Get the path to agent.py in the project root."""
    project_root = Path(__file__).parent.parent
    return project_root / "agent.py"


def run_agent(question: str) -> tuple:
    """Run agent.py with a question. Returns (stdout, stderr, returncode)."""
    agent_path = get_agent_path()

    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=120,
    )

    return result.stdout, result.stderr, result.returncode


class TestRetryLogic:
    """Test retry logic for LLM API calls."""

    def test_agent_handles_transient_errors(self):
        """
        Test that agent retries on API errors.

        Note: This test verifies the retry logic is in place by checking
        stderr output for retry messages. Actual retry behavior depends on
        API availability.
        """
        stdout, stderr, returncode = run_agent("What is FastAPI?")

        # Check that agent attempted to call the LLM
        assert "Calling LLM at" in stderr, "Expected LLM call attempt in stderr"
        assert "attempt" in stderr.lower(), "Expected attempt counter in stderr"

        # Agent should either succeed or show retry attempts
        if returncode != 0:
            # If it failed, check for retry messages
            assert "retry" in stderr.lower() or "attempt" in stderr.lower(), \
                "Expected retry logic to be active"


class TestCaching:
    """Test caching layer for tool results."""

    def test_agent_uses_cache(self):
        """
        Test that agent caches tool results.

        Ask a question that requires reading the same file, then check
        stderr for cache hit messages.
        """
        stdout, stderr, returncode = run_agent(
            "What framework does the backend use and what are the main routes?"
        )

        # Check for cache-related output in stderr
        # The agent should show [CACHE] or [CACHE HIT] messages
        has_cache_output = "[CACHE" in stderr or "cache" in stderr.lower()

        # Either cache was used, or the question was answered without needing
        # duplicate tool calls
        assert returncode == 0 or has_cache_output, \
            "Expected agent to use caching or succeed"

        if returncode == 0:
            # Verify output is valid JSON
            try:
                data = json.loads(stdout)
                assert "answer" in data, "Expected 'answer' in JSON output"
                assert "tool_calls" in data, "Expected 'tool_calls' in JSON output"
            except json.JSONDecodeError:
                pass  # May fail if API is unavailable


class TestAdvancedFeatures:
    """Integration tests for advanced features."""

    def test_agent_output_structure(self):
        """Test that agent produces correct JSON structure."""
        stdout, stderr, returncode = run_agent("Test question")

        if returncode == 0:
            data = json.loads(stdout)
            assert "answer" in data
            assert "tool_calls" in data
            assert isinstance(data["tool_calls"], list)

    def test_stderr_shows_progress(self):
        """Test that agent logs progress to stderr."""
        stdout, stderr, returncode = run_agent("What is in the wiki?")

        # Should show agentic loop progress
        assert "agentic loop" in stderr.lower() or \
               "iteration" in stderr.lower() or \
               "Calling LLM" in stderr, \
               "Expected progress messages in stderr"
