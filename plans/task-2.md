# Plan for Task 2: The Documentation Agent

## Overview

Transform the CLI chatbot from Task 1 into an agentic system that can:
1. Use tools (`read_file`, `list_files`) to interact with the project wiki
2. Execute an agentic loop: LLM → tool call → execute → LLM → answer
3. Return structured JSON with `answer`, `source`, and `tool_calls`

## LLM Provider and Model

- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: `qwen3-coder-plus` (supports function calling)
- **API**: OpenAI-compatible chat completions endpoint

## Tool Definitions

### 1. `read_file`
**Purpose**: Read contents of a file from the project repository.

**Parameters**:
- `path` (string): Relative path from project root

**Returns**: File contents as string, or error message

**Security**: Block paths with `../` traversal

**Schema**:
```json
{
  "name": "read_file",
  "description": "Read the contents of a file",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

### 2. `list_files`
**Purpose**: List files and directories at a given path.

**Parameters**:
- `path` (string): Relative directory path from project root

**Returns**: Newline-separated listing of entries

**Security**: Block paths with `../` traversal

**Schema**:
```json
{
  "name": "list_files",
  "description": "List files and directories at a path",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative directory path from project root"}
    },
    "required": ["path"]
  }
}
```

## Agentic Loop Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Agentic Loop                                                    │
│                                                                  │
│  1. Build messages array with:                                   │
│     - System prompt (role + tool instructions)                   │
│     - User question                                              │
│                                                                  │
│  2. Call LLM with tool schemas                                   │
│                                                                  │
│  3. Check response:                                              │
│     ┌─────────────────────────────────────────────────────┐     │
│     │ Has tool_calls?                                     │     │
│     │  YES → Execute tools, append results, loop to step 2│     │
│     │  NO  → Extract answer, format JSON, exit            │     │
│     └─────────────────────────────────────────────────────┘     │
│                                                                  │
│  4. Max 10 iterations (safety limit)                             │
└──────────────────────────────────────────────────────────────────┘
```

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files when the question is about documentation
2. Use `read_file` to read relevant files and find the answer
3. Include the source reference (file path + section anchor) in the answer
4. Only respond with the final answer when sufficient information is gathered

Example:
```
You are a documentation assistant for a software engineering lab.
You have access to two tools:
- list_files: List files in a directory
- read_file: Read contents of a file

When answering questions:
1. First use list_files to discover relevant wiki files
2. Then use read_file to find the specific information
3. Cite your source as "wiki/filename.md#section-anchor"
4. Only give your final answer after gathering enough information
```

## Data Flow

```
User Question
     │
     ▼
┌─────────────────┐
│ Build messages  │
│ + tool schemas  │
└─────────────────┘
     │
     ▼
┌─────────────────┐
│   Call LLM      │
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Has tool_calls? │──Yes──▶ Execute tools → Append results → Loop
└─────────────────┘
     │
     No
     │
     ▼
┌─────────────────┐
│ Extract answer  │
│ + source        │
└─────────────────┘
     │
     ▼
JSON Output
```

## Output Format

```json
{
  "answer": "Answer text here.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Path traversal attempt (`../`) | Return error message, don't execute |
| File not found | Return error message |
| LLM returns invalid tool call | Return error, continue loop |
| Max iterations (10) reached | Return partial answer with error |

## Testing Strategy

Create 2 regression tests:

1. **Test merge conflict question**:
   - Question: "How do you resolve a merge conflict?"
   - Expected: `read_file` in tool_calls, `wiki/git-workflow.md` in source

2. **Test wiki listing question**:
   - Question: "What files are in the wiki?"
   - Expected: `list_files` in tool_calls

## Implementation Steps

1. Create `plans/task-2.md` (this file)
2. Implement tool functions (`read_file`, `list_files`)
3. Add tool schemas for LLM function calling
4. Implement agentic loop with max 10 iterations
5. Update system prompt
6. Update output format to include `source` field
7. Write 2 regression tests
8. Update `AGENT.md` documentation
