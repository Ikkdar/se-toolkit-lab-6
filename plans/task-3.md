# Plan for Task 3: The System Agent

## Overview

Extend the Documentation Agent from Task 2 with a new tool `query_api` to interact with the deployed backend API. The agent will answer:
1. **Static system facts** - framework, ports, status codes (from source code)
2. **Data-dependent queries** - item count, scores (from live API)
3. **Bug diagnosis** - API errors + source code analysis

## New Tool: query_api

### Purpose
Call the deployed backend API to fetch data or check endpoints.

### Parameters
- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., `/items/`)
- `body` (string, optional): JSON request body for POST/PUT

### Returns
JSON string with `status_code` and `body`

### Authentication
- Use `LMS_API_KEY` from `.env.docker.secret`
- Header: `Authorization: Bearer {LMS_API_KEY}`

### Schema
```json
{
  "name": "query_api",
  "description": "Call the deployed backend API to fetch data or check endpoints",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {
        "type": "string",
        "description": "HTTP method (GET, POST, etc.)",
        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
      },
      "path": {
        "type": "string",
        "description": "API endpoint path (e.g., '/items/')"
      },
      "body": {
        "type": "string",
        "description": "JSON request body for POST/PUT (optional)"
      }
    },
    "required": ["method", "path"]
  }
}
```

### Implementation
```python
def query_api(method: str, path: str, body: str = None) -> str:
    """Call the backend API with authentication."""
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.getenv("LMS_API_KEY")
    
    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {lms_api_key}",
        "Content-Type": "application/json",
    }
    
    # Make request with httpx
    # Return JSON string with status_code and body
```

## Environment Variables

The agent reads from TWO files:

### `.env.agent.secret` (LLM config)
- `LLM_API_KEY` - LLM provider API key
- `LLM_API_BASE` - LLM API endpoint URL
- `LLM_MODEL` - Model name

### `.env.docker.secret` (Backend config)
- `LMS_API_KEY` - Backend API key for query_api auth

### Optional
- `AGENT_API_BASE_URL` - Base URL for query_api (default: `http://localhost:42002`)

**Important:** All values must be read from environment, NOT hardcoded. The autochecker injects its own values.

## System Prompt Update

The system prompt must guide the LLM to choose the right tool:

```
You are a documentation and system assistant for a software engineering lab.

You have access to three tools:
1. list_files - List files and directories at a given path
2. read_file - Read the contents of a file
3. query_api - Call the deployed backend API

Tool selection guidelines:
- Use list_files to discover project structure
- Use read_file to read documentation (wiki/), source code (backend/), or config files
- Use query_api to:
  - Get live data from the database (item counts, scores)
  - Check HTTP status codes
  - Test API endpoints
  - Diagnose API errors

When answering questions:
1. First understand what type of question it is:
   - Wiki/documentation question → use list_files, then read_file
   - Source code question → use read_file on backend/ files
   - Live data question → use query_api
   - Bug diagnosis → use query_api first, then read_file on error location

2. Always cite your source:
   - Wiki files: "wiki/filename.md#section"
   - Source files: "backend/path/to/file.py:function"
   - API data: "API endpoint /path/"

3. For bug diagnosis:
   - First reproduce the error with query_api
   - Then read the source code at the error location
   - Explain the root cause and suggest a fix
```

## Agentic Loop

The loop remains the same as Task 2, now with 3 tools:

```
Question → Build messages + 3 tool schemas → Call LLM
                                      │
                                      ▼
                              Has tool_calls? ──No──▶ Answer
                                      │Yes
                                      ▼
                              Execute tools (including query_api)
                                      │
                                      ▼
                              Append results → Loop
```

**Max iterations:** 10

## Benchmark Evaluation

### Running the benchmark
```bash
uv run run_eval.py
```

### Question categories
| # | Type | Example | Tool |
|---|------|---------|------|
| 0-1 | Wiki lookup | "What steps to protect a branch?" | read_file |
| 2-3 | Source code | "What framework?" | read_file |
| 4-5 | API data | "How many items?" | query_api |
| 6-7 | Bug diagnosis | "Query /analytics/... what error?" | query_api + read_file |
| 8-9 | Reasoning | "Explain request lifecycle" | read_file (multiple) |

### Grading modes
1. **Keyword match** - Answer must contain specific keywords
2. **LLM judge** - LLM grades with rubric (for open-ended questions)

### Iteration strategy
1. Run `run_eval.py`
2. Note failing questions
3. For each failure:
   - Check which tool was called
   - Check tool arguments
   - Check answer extraction
4. Fix one issue at a time
5. Re-run benchmark

## Implementation Steps

1. Create `plans/task-3.md` (this file)
2. Add `query_api` tool function with authentication
3. Add `query_api` schema to tool registry
4. Update system prompt for tool selection
5. Ensure all config is read from environment variables
6. Run `run_eval.py` and iterate
7. Add 2 regression tests for Task 3
8. Update `AGENT.md` with final architecture and lessons learned
9. Create PR and complete git workflow

## Testing Strategy

Create 2 regression tests:

1. **Test source code question**:
   - Question: "What framework does the backend use?"
   - Expected: `read_file` in tool_calls, answer contains "FastAPI"

2. **Test API data question**:
   - Question: "How many items are in the database?"
   - Expected: `query_api` in tool_calls, answer contains a number

## Expected Challenges

| Challenge | Solution |
|-----------|----------|
| LLM calls wrong tool | Improve system prompt with clearer guidelines |
| query_api returns 401 | Check LMS_API_KEY is loaded correctly |
| Agent loops infinitely | Add max iteration limit, improve tool descriptions |
| Answer extraction fails | Parse LLM response more carefully |
| API base URL wrong | Default to http://localhost:42002 (Caddy port) |

## Success Criteria

- ✅ All 10 benchmark questions pass
- ✅ `query_api` tool works with authentication
- ✅ Agent reads all config from environment variables
- ✅ 2 new regression tests pass
- ✅ `AGENT.md` updated with 200+ words
- ✅ PR merged following git workflow
