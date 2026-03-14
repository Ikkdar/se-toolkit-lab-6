"""Regression tests for Task 3: System Agent.

These tests verify that the agent:
1. Uses query_api tool correctly
2. Uses read_file for source code questions
3. Returns proper JSON with answer, source, and tool_calls

Run with: uv run pytest tests/test_agent_task3.py -v
"""

import json
import subprocess
import sys
from pathlib import Path


def get_agent_path() -> Path:
    """Get the path to agent.py in the project root."""
    project_root = Path(__file__).parent.parent
    return project_root / "agent.py"


def run_agent(question: str) -> dict:
    """Run agent.py with a question and return parsed JSON output."""
    agent_path = get_agent_path()

    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Agent failed: {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")


class TestSystemAgent:
    """Test the system agent with query_api and source code questions."""

    def test_agent_uses_read_file_for_framework_question(self):
        """Test that agent uses read_file when asked about the backend framework."""
        output = run_agent("What Python web framework does the backend use?")

        # Check required fields
        assert "answer" in output, "Output missing 'answer' field"
        assert "tool_calls" in output, "Output missing 'tool_calls' field"

        # Check that tool_calls is non-empty
        tool_calls = output["tool_calls"]
        assert len(tool_calls) > 0, "Expected agent to use tools for framework question"

        # Check that read_file was used
        tools_used = [tc["tool"] for tc in tool_calls]
        assert "read_file" in tools_used, "Expected read_file to be used for source code question"

        # Check that answer mentions FastAPI
        answer_lower = output["answer"].lower()
        assert "fastapi" in answer_lower, f"Expected answer to mention FastAPI, got: {output['answer']}"

    def test_agent_uses_query_api_for_data_question(self):
        """Test that agent uses query_api when asked about database items."""
        output = run_agent("How many items are in the database?")

        # Check required fields
        assert "answer" in output, "Output missing 'answer' field"
        assert "tool_calls" in output, "Output missing 'tool_calls' field"

        # Check that tool_calls is non-empty
        tool_calls = output["tool_calls"]
        assert len(tool_calls) > 0, "Expected agent to use tools for data question"

        # Check that query_api was used
        tools_used = [tc["tool"] for tc in tool_calls]
        assert "query_api" in tools_used, "Expected query_api to be used for data question"

        # Check that answer contains a number
        import re
        numbers = re.findall(r'\d+', output["answer"])
        assert len(numbers) > 0, f"Expected answer to contain a number, got: {output['answer']}"

    def test_agent_output_structure(self):
        """Test that agent output has correct structure for all tool types."""
        # Test with a simple question
        output = run_agent("What files are in the wiki directory?")

        # Check field types
        assert isinstance(output["answer"], str), "'answer' should be a string"
        assert isinstance(output["tool_calls"], list), "'tool_calls' should be an array"

        # Check tool_calls structure
        for tc in output["tool_calls"]:
            assert "tool" in tc, "Tool call missing 'tool' field"
            assert "args" in tc, "Tool call missing 'args' field"
            assert "result" in tc, "Tool call missing 'result' field"
            assert isinstance(tc["args"], dict), "'args' should be a dict"

            # Check that result is a string
            assert isinstance(tc["result"], str), "'result' should be a string"
