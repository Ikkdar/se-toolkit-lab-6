"""Regression tests for Task 2: Documentation Agent.

These tests verify that the agent:
1. Uses tools (read_file, list_files) correctly
2. Returns proper JSON with answer, source, and tool_calls
3. Can answer documentation questions

Run with: uv run pytest tests/test_agent_task2.py -v
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


class TestDocumentationAgent:
    """Test the documentation agent with tool usage."""

    def test_agent_uses_read_file_for_merge_conflict_question(self):
        """Test that agent uses read_file when asked about merge conflicts."""
        output = run_agent("How do you resolve a merge conflict?")

        # Check required fields
        assert "answer" in output, "Output missing 'answer' field"
        assert "source" in output, "Output missing 'source' field"
        assert "tool_calls" in output, "Output missing 'tool_calls' field"

        # Check that tool_calls is non-empty (agent should use tools)
        tool_calls = output["tool_calls"]
        assert len(tool_calls) > 0, "Expected agent to use tools for documentation question"

        # Check that read_file was used
        tools_used = [tc["tool"] for tc in tool_calls]
        assert "read_file" in tools_used, "Expected read_file to be used"

        # Check that source references git-workflow.md or similar
        source = output["source"]
        assert "wiki/" in source or any("wiki/" in tc.get("args", {}).get("path", "") for tc in tool_calls), \
            "Expected source to reference wiki files"

    def test_agent_uses_list_files_for_wiki_listing_question(self):
        """Test that agent uses list_files when asked about wiki contents."""
        output = run_agent("What files are in the wiki?")

        # Check required fields
        assert "answer" in output, "Output missing 'answer' field"
        assert "source" in output, "Output missing 'source' field"
        assert "tool_calls" in output, "Output missing 'tool_calls' field"

        # Check that tool_calls is non-empty
        tool_calls = output["tool_calls"]
        assert len(tool_calls) > 0, "Expected agent to use tools for wiki listing question"

        # Check that list_files was used
        tools_used = [tc["tool"] for tc in tool_calls]
        assert "list_files" in tools_used, "Expected list_files to be used"

        # Check that list_files was called with wiki path
        list_files_calls = [tc for tc in tool_calls if tc["tool"] == "list_files"]
        wiki_paths = [tc["args"].get("path", "") for tc in list_files_calls if "wiki" in tc["args"].get("path", "")]
        assert len(wiki_paths) > 0, "Expected list_files to be called with wiki path"

    def test_agent_output_has_correct_structure(self):
        """Test that agent output has correct JSON structure."""
        output = run_agent("What is the project about?")

        # Check field types
        assert isinstance(output["answer"], str), "'answer' should be a string"
        assert isinstance(output["source"], str), "'source' should be a string"
        assert isinstance(output["tool_calls"], list), "'tool_calls' should be an array"

        # Check tool_calls structure
        for tc in output["tool_calls"]:
            assert "tool" in tc, "Tool call missing 'tool' field"
            assert "args" in tc, "Tool call missing 'args' field"
            assert "result" in tc, "Tool call missing 'result' field"
            assert isinstance(tc["args"], dict), "'args' should be a dict"
