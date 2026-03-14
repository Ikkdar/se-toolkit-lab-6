# Plan for Task 1: Call an LLM from Code

## LLM Provider and Model

- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: `qwen3-coder-plus`
- **API Endpoint**: `http://10.93.26.63:42005/v1` (OpenAI-compatible)
- **Authentication**: Bearer token from `.env.agent.secret`

## Agent Architecture

The agent will have the following components:

### 1. Configuration Loader
- Read environment variables from `.env.agent.secret`
- Use `python-dotenv` library to load `.env` file
- Extract: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

### 2. HTTP Client
- Use `httpx` library for making HTTP requests (async-capable, modern API)
- Send POST request to `{LLM_API_BASE}/chat/completions`
- Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
- Timeout: 60 seconds

### 3. Request Builder
- Build the chat completion request body:
  ```json
  {
    "model": "qwen3-coder-plus",
    "messages": [{"role": "user", "content": "<user question>"}]
  }
  ```

### 4. Response Parser
- Parse LLM response JSON
- Extract answer from `choices[0].message.content`
- Format output as: `{"answer": "...", "tool_calls": []}`

### 5. CLI Interface
- Parse command-line argument (user question)
- Use `sys.argv[1]` to get the question
- Print JSON to stdout
- Print debug info to stderr

## Data Flow

```
Command line → Parse argument → Load config → Build request → 
Call LLM API → Parse response → Format JSON → Print to stdout
```

## Error Handling

- Missing arguments → print error to stderr, exit code 1
- Network errors → print error to stderr, exit code 1
- Invalid response → print error to stderr, exit code 1

## Testing Strategy

- Run `agent.py "test question"` as subprocess
- Parse stdout JSON
- Verify `answer` field exists and is non-empty
- Verify `tool_calls` field exists and is array
