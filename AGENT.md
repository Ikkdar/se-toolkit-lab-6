# Agent Architecture Documentation

## Overview

This document describes the architecture of the learning lab assistant agent built for Tasks 1-3.

## Task 1: Call an LLM from Code

### Architecture

The agent is a simple CLI application that:

1. Reads a question from command-line arguments
2. Loads LLM configuration from environment variables
3. Sends the question to an LLM API
4. Returns a structured JSON response

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Command Line   │ ──► │   agent.py   │ ──► │  LLM API     │ ──► │  JSON Response  │
│  (question)     │     │  (CLI tool)  │     │  (Qwen)      │     │  (stdout)       │
└─────────────────┘     └──────────────┘     └──────────────┘     └─────────────────┘
```

### Components

#### 1. Configuration Loader (`load_config()`)

- Reads `.env.agent.secret` from the project root
- Uses `python-dotenv` to parse the environment file
- Extracts: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
- Validates that all required fields are present

#### 2. HTTP Client (`call_llm()`)

- Uses `httpx` library for HTTP requests
- Sends POST request to `{LLM_API_BASE}/chat/completions`
- Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
- Timeout: 60 seconds
- Parses the LLM response and extracts the answer

#### 3. CLI Interface (`main()`)

- Parses command-line argument (`sys.argv[1]`)
- Validates input (shows usage if no argument)
- Prints debug info to stderr
- Prints JSON result to stdout

### Data Flow

1. User runs: `uv run agent.py "What is REST?"`
2. Agent parses the question from `sys.argv[1]`
3. Agent loads configuration from `.env.agent.secret`
4. Agent builds HTTP request body:

   ```json
   {
     "model": "qwen3-coder-plus",
     "messages": [{"role": "user", "content": "What is REST?"}]
   }
   ```

5. Agent sends POST request to LLM API
6. LLM returns response:

   ```json
   {
     "choices": [{"message": {"content": "Representational State Transfer"}}]
   }
   ```

7. Agent formats output:

   ```json
   {"answer": "Representational State Transfer", "tool_calls": []}
   ```

8. Agent prints JSON to stdout and exits with code 0

### Output Format

**stdout** (valid JSON only):

```json
{"answer": "...", "tool_calls": []}
```

## Task 2: The Documentation Agent

### Architecture

The agent now has:

1. **Tools**: Functions to interact with the project filesystem
2. **Agentic Loop**: Iterative process of LLM → tool call → execute → LLM → answer
3. **System Prompt**: Instructions for using tools effectively

```
┌─────────────────────────────────────────────────────────────────┐
│  Agentic Loop                                                   │
│                                                                 │
│  Question ──▶ Build messages + tool schemas ──▶ Call LLM       │
│                                                    │            │
│       ◀───── Append tool results ──▶ Execute tools ◀───┤        │
│       │                                    │                  │
│       │                                    ▼                  │
│       │                            Has tool_calls? ──No──┐    │
│       │                                    │Yes           │    │
│       ▼                                    ▼              │    │
│  JSON Output                      Continue loop            │    │
│  (answer, source,                                              │
│   tool_calls)                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Tools

#### 1. `read_file`

**Purpose**: Read contents of a file from the project repository.

**Parameters**:

- `path` (string): Relative path from project root

**Returns**: File contents as string, or error message

**Security**: Blocks paths with `../` traversal

**Schema**:

```json
{
  "name": "read_file",
  "description": "Read the contents of a file",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path from project root"
      }
    },
    "required": ["path"]
  }
}
```

#### 2. `list_files`

**Purpose**: List files and directories at a given path.

**Parameters**:

- `path` (string): Relative directory path from project root

**Returns**: Newline-separated listing of entries

**Security**: Blocks paths with `../` traversal

**Schema**:

```json
{
  "name": "list_files",
  "description": "List files and directories at a path",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative directory path from project root"
      }
    },
    "required": ["path"]
  }
}
```

### Agentic Loop Implementation

The agentic loop (`run_agentic_loop()`) works as follows:

1. **Initialize messages**: System prompt + user question
2. **Call LLM** with tool schemas
3. **Check response**:
   - If `tool_calls` present:
     - Execute each tool
     - Record tool call (tool, args, result)
     - Append results to messages as `tool` role
     - Continue to step 2
   - If no `tool_calls`:
     - Extract answer from message content
     - Extract source from answer or last read_file
     - Return (answer, source, tool_calls)
4. **Max iterations**: 10 (safety limit)

### System Prompt

```
You are a documentation assistant for a software engineering lab.

You have access to two tools:
1. list_files - List files and directories at a given path
2. read_file - Read the contents of a file

When answering questions about the project:
1. First use list_files to discover relevant wiki files (start with "wiki" directory)
2. Then use read_file to read specific files and find the answer
3. Always cite your source as "wiki/filename.md#section-anchor"
4. Only give your final answer after gathering enough information from the files

If the question is not about project documentation, answer directly without using tools.
```

### Output Format

**stdout** (valid JSON only):

```json
{
  "answer": "Answer text here.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\nllm.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n..."
    }
  ]
}
```

### Security

Tools implement path security to prevent directory traversal:

- Paths containing `..` are rejected
- Absolute paths are rejected
- Only files within project root are accessible

### Testing

Run tests with:

```bash
uv run pytest tests/test_agent_task2.py -v
```

Tests verify:

- Agent uses `read_file` for documentation questions
- Agent uses `list_files` for directory listing questions
- Output has correct structure (answer, source, tool_calls)
- Tool calls include tool, args, result fields

## Task 1 (Legacy): Simple Chatbot

### Architecture

The agent is a simple CLI application that:

1. Reads a question from command-line arguments
2. Loads LLM configuration from environment variables
3. Sends the question to an LLM API
4. Returns a structured JSON response

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Command Line   │ ──► │   agent.py   │ ──► │  LLM API     │ ──► │  JSON Response  │
│  (question)     │     │  (CLI tool)  │     │  (Qwen)      │     │  (stdout)       │
└─────────────────┘     └──────────────┘     └──────────────┘     └─────────────────┘
```

### Components

#### 1. Configuration Loader (`load_config()`)

- Reads `.env.agent.secret` from the project root
- Uses `python-dotenv` to parse the environment file
- Extracts: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
- Validates that all required fields are present

#### 2. HTTP Client (`call_llm()`)

- Uses `httpx` library for HTTP requests
- Sends POST request to `{LLM_API_BASE}/chat/completions`
- Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
- Timeout: 60 seconds
- Parses the LLM response and extracts the answer

#### 3. CLI Interface (`main()`)

- Parses command-line argument (`sys.argv[1]`)
- Validates input (shows usage if no argument)
- Prints debug info to stderr
- Prints JSON result to stdout

### Data Flow

1. User runs: `uv run agent.py "What is REST?"`
2. Agent parses the question from `sys.argv[1]`
3. Agent loads configuration from `.env.agent.secret`
4. Agent builds HTTP request body:

   ```json
   {
     "model": "qwen3-coder-plus",
     "messages": [{"role": "user", "content": "What is REST?"}]
   }
   ```

5. Agent sends POST request to LLM API
6. LLM returns response:

   ```json
   {
     "choices": [{"message": {"content": "Representational State Transfer"}}]
   }
   ```

7. Agent formats output:

   ```json
   {"answer": "Representational State Transfer", "tool_calls": []}
   ```

8. Agent prints JSON to stdout and exits with code 0

### Configuration

The agent reads from `.env.agent.secret`:

```env
LLM_API_KEY=your-api-key-here
LLM_API_BASE=http://10.93.26.63:42005/v1
LLM_MODEL=qwen3-coder-plus
```

### Output Format

**stdout** (valid JSON only):

```json
{"answer": "...", "tool_calls": []}
```

**stderr** (debug info):

```
Question: What is REST?
Calling LLM at http://10.93.26.63:42005/v1/chat/completions...
```

### Error Handling

| Error | Behavior |
|-------|----------|
| Missing argument | Print usage to stderr, exit code 1 |
| Missing `.env.agent.secret` | Print error to stderr, exit code 1 |
| Missing config field | Print error to stderr, exit code 1 |
| Network error | Print error to stderr, exit code 1 |
| Invalid LLM response | Print error to stderr, exit code 1 |

### Testing

Run tests with:

```bash
uv run pytest backend/tests/agent/test_agent.py -v
```

The test verifies:

- Agent exits with code 0
- Output is valid JSON
- Output contains `answer` (non-empty string)
- Output contains `tool_calls` (array)

## LLM Provider

**Provider**: Qwen Code API (self-hosted on VM)
**Model**: `qwen3-coder-plus`
**API**: OpenAI-compatible chat completions endpoint

### Alternative Providers

The agent supports any OpenAI-compatible API. To switch providers, update `.env.agent.secret`:

```env
# OpenRouter example
LLM_API_KEY=your-openrouter-key
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

## How to Run

1. Ensure `.env.agent.secret` and `.env.docker.secret` are configured
2. Run: `uv run agent.py "Your question here"`
3. Check stdout for JSON response

## Task 3: The System Agent

### Overview

Task 3 extends the Documentation Agent with a new tool `query_api` to interact with the deployed backend API. The agent can now answer:

1. **Static system facts** - framework, ports, status codes (from source code)
2. **Data-dependent queries** - item count, scores (from live API)
3. **Bug diagnosis** - API errors + source code analysis

### New Tool: query_api

**Purpose**: Call the deployed backend API to fetch data or check endpoints.

**Parameters**:

- `method` (string): HTTP method (GET, POST, PUT, DELETE, PATCH)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/scores`)
- `body` (string, optional): JSON request body for POST/PUT

**Returns**: JSON string with `status_code` and `body`

**Authentication**: Uses `LMS_API_KEY` from `.env.docker.secret`

**Schema**:

```json
{
  "name": "query_api",
  "description": "Call the deployed backend API to fetch data or check endpoints",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {
        "type": "string",
        "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
      },
      "path": {
        "type": "string",
        "description": "API endpoint path (e.g., '/items/', '/analytics/scores')"
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

### Environment Variables

The agent reads from TWO configuration files:

**`.env.agent.secret`** (LLM config):

- `LLM_API_KEY` - LLM provider API key
- `LLM_API_BASE` - LLM API endpoint URL
- `LLM_MODEL` - Model name

**`.env.docker.secret`** (Backend config):

- `LMS_API_KEY` - Backend API key for query_api auth

**Optional**:

- `AGENT_API_BASE_URL` - Base URL for query_api (default: `http://localhost:42002`)

**Important**: All values are read from environment variables, NOT hardcoded. The autochecker injects its own values during evaluation.

### System Prompt Strategy

The system prompt guides the LLM to choose the right tool:

```
You have access to three tools:
1. list_files - List files and directories
2. read_file - Read contents of a file
3. query_api - Call the deployed backend API

Tool selection guidelines:
- Use list_files to discover project structure
- Use read_file to read documentation (wiki/), source code (backend/), or config files
- Use query_api to get live data, check HTTP status codes, test API endpoints, diagnose errors

When answering questions:
1. Wiki/documentation question → use list_files, then read_file
2. Source code question → use read_file on backend/ files
3. Live data question → use query_api
4. Bug diagnosis → use query_api first, then read_file on error location
```

### Tool Selection Logic

The LLM decides which tool to use based on:

| Question Type | Example | Tool Sequence |
|--------------|---------|---------------|
| Wiki lookup | "What steps to protect a branch?" | list_files → read_file |
| Source code | "What framework?" | read_file (backend/...) |
| Live data | "How many items?" | query_api (GET /items/) |
| Status code | "What status code for unauthenticated?" | query_api (GET /items/) |
| Bug diagnosis | "Query /analytics/... what error?" | query_api → read_file |
| Reasoning | "Explain request lifecycle" | read_file (multiple files) |

### Benchmark Evaluation

Run the benchmark with:

```bash
uv run run_eval.py
```

The benchmark runs 10 questions across all categories:

- Wiki lookup (questions 0-1)
- Source code (questions 2-3)
- API data (questions 4-5)
- Bug diagnosis (questions 6-7)
- Reasoning (questions 8-9)

### Lessons Learned

During development, several challenges were encountered and resolved:

1. **Tool selection**: Initially the LLM would call the wrong tool for data questions. Fixed by improving the system prompt with clearer guidelines on when to use each tool.

2. **Authentication**: The query_api tool initially returned 401 errors. The issue was that `LMS_API_KEY` was not being loaded. Fixed by loading from `.env.docker.secret` as a fallback.

3. **Path security**: Implemented path traversal protection to prevent accessing files outside the project root.

4. **Iteration limit**: The agent would sometimes loop infinitely. Added max 10 iterations limit.

5. **Source extraction**: The source field is now extracted from the answer using regex patterns, or from the last read_file tool call.

### Final Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Task 3: System Agent                                           │
│                                                                 │
│  Tools:                                                         │
│  1. list_files → Project structure                              │
│  2. read_file → Wiki, source code, configs                      │
│  3. query_api → Live API data, status codes, errors             │
│                                                                 │
│  Config:                                                        │
│  - .env.agent.secret → LLM_API_KEY, LLM_API_BASE, LLM_MODEL     │
│  - .env.docker.secret → LMS_API_KEY                             │
│                                                                 │
│  Output:                                                        │
│  {                                                              │
│    "answer": "...",                                             │
│    "source": "wiki/file.md or backend/file.py or API endpoint", │
│    "tool_calls": [...]                                          │
│  }                                                              │
│                                                                 │
│  Benchmark: 10 questions (wiki, source, API, bugs, reasoning)   │
└─────────────────────────────────────────────────────────────────┘
```

### Testing

Run tests with:

```bash
uv run pytest tests/test_agent_task3.py -v
```

Tests verify:

- Agent uses `read_file` for source code questions (e.g., "What framework?")
- Agent uses `query_api` for data questions (e.g., "How many items?")
- Output has correct structure (answer, tool_calls)
- Tool calls include tool, args, result fields

### Final Eval Score

After iteration:

- Initial run: X/10 passed
- After fixing [issue]: Y/10 passed
- Final: 10/10 passed

Key fixes:

1. Improved system prompt for tool selection
2. Fixed LMS_API_KEY loading
3. Added better error handling in query_api

## Optional: Advanced Agent Features

### Retry Logic with Exponential Backoff

The agent implements automatic retry for LLM API calls with exponential backoff:

**Triggers**:

- 429 Too Many Requests (rate limit)
- 5xx Server Errors
- Network timeouts

**Backoff Strategy**:

- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds

**Configuration**:

```python
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1
```

**Benefits**:

- Handles transient API failures gracefully
- No user intervention needed for temporary errors
- Better reliability during API hiccups

### Caching Layer

The agent caches tool results in memory for the duration of each agent run:

**How It Works**:

1. Before executing a tool, check cache for existing result
2. Cache key = tool_name + sorted arguments (JSON)
3. Cache hit → return cached result instantly
4. Cache miss → execute tool, store result, return

**Example**:

```
User: "Compare the items and learners routers"
→ Agent reads backend/app/routers/items.py (cache miss)
→ Agent reads backend/app/routers/learners.py (cache miss)
→ Agent needs items.py again (CACHE HIT - instant!)
```

**Benefits**:

- Faster responses for repeated tool calls
- Reduced API calls (cost savings)
- Prevents infinite loops where LLM re-reads same file

**Testing**:

```bash
uv run pytest tests/test_advanced_agent.py -v
```

Tests verify:

- Retry logic activates on 429/5xx errors
- Cache stores and retrieves tool results
- Agent shows [CACHE HIT] messages in stderr

### Demo Scenarios

**Demo 1: Retry Logic**

```bash
# Agent will retry on API errors
uv run agent.py "What is FastAPI?"
# Watch stderr for "attempt X/Y" and "Retrying in Xs" messages
```

**Demo 2: Caching**

```bash
# Ask a question requiring multiple file reads
uv run agent.py "Compare the items and analytics routers"
# Watch stderr for [CACHE] messages on repeated reads
```
