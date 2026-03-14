"""Regression tests for agent.py CLI.

These tests run agent.py as a subprocess and verify:
1. The output is valid JSON
2. The output contains 'answer' and 'tool_calls' fields
3. The agent exits with code 0 on success

Run with: uv run pytest tests/test_agent.py -v
"""

import json
import subprocess
import sys
from pathlib import Path


def get_agent_path() -> Path:
    """Get the path to agent.py in the project root."""
    project_root = Path(__file__).parent.parent
    return project_root / "agent.py"


class TestAgentOutput:
    """Test that agent.py produces correct JSON output."""

    def test_agent_returns_valid_json(self):
        """Test that agent.py outputs valid JSON with required fields."""
        agent_path = get_agent_path()
        
        # Run agent.py with a test question
        # Note: This test requires a working LLM API connection
        # If the API is unavailable, this test will fail
        result = subprocess.run(
            [sys.executable, "-m", "uv", "run", str(agent_path), "What is 2+2?"],
            capture_output=True,
            text=True,
            timeout=120,  # Give extra time for LLM response
        )
        
        # Check exit code
        assert result.returncode == 0, f"Agent failed: {result.stderr}"
        
        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")
        
        # Check required fields
        assert "answer" in output, "Output missing 'answer' field"
        assert "tool_calls" in output, "Output missing 'tool_calls' field"
        
        # Check field types
        assert isinstance(output["answer"], str), "'answer' should be a string"
        assert isinstance(output["tool_calls"], list), "'tool_calls' should be an array"
        
        # Check that answer is non-empty
        assert len(output["answer"]) > 0, "'answer' should not be empty"
