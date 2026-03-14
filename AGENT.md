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

1. Ensure `.env.agent.secret` is configured
2. Run: `uv run agent.py "Your question here"`
3. Check stdout for JSON response

## Future Enhancements (Tasks 2-3)

- **Task 2**: Add tools (file operations, API queries)
- **Task 3**: Add agentic loop (plan → act → observe)
- Add system prompt for lab assistant behavior
- Add conversation history support
- Add streaming responses
