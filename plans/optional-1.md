# Plan for Optional Task 1: Advanced Agent Features

## Chosen Extensions

### 1. Retry Logic with Exponential Backoff

**Purpose**: Handle API rate limits (429) and transient errors (5xx) gracefully.

**Implementation**:
- Wrap LLM API calls in a retry loop
- Exponential backoff: wait 1s, 2s, 4s, 8s between retries
- Maximum 3 retry attempts
- Log retry attempts to stderr

**Expected Improvement**:
- Better reliability during API hiccups
- No more immediate failures on temporary errors

### 2. Caching Layer for Tool Results

**Purpose**: Avoid redundant tool calls within the same agent run.

**Implementation**:
- In-memory cache (dict) keyed by tool name + arguments
- Check cache before executing tool
- Cache hit → return cached result instantly
- Cache miss → execute tool, store result, return

**Expected Improvement**:
- Faster responses when LLM calls same tool twice
- Reduced API calls (cost savings)
- Prevents infinite loops where LLM re-reads same file

## Why These Extensions?

| Extension | Benefit | Complexity |
|-----------|---------|------------|
| Retry logic | Reliability | Low |
| Caching | Speed + cost reduction | Low |
| query_db | New capability | Medium |
| Multi-step reasoning | Accuracy | High |

Retry + caching provide immediate value with minimal complexity.

## Implementation Steps

1. Create `plans/optional-1.md` (this file)
2. Add retry wrapper for `call_llm()`
3. Add cache dict and cache-aware `execute_tool()`
4. Write tests for retry and caching
5. Update `AGENT.md` with documentation
6. Create PR with git workflow

## Testing Strategy

### Retry Logic Test
- Mock API to return 429, then success
- Verify agent retries and eventually succeeds
- Verify backoff delays (capture stderr logs)

### Caching Test
- Call agent with question that triggers same tool twice
- Verify second call uses cache (faster, no duplicate tool_call)
- Or: manually test `read_file` twice, verify cache hit

## Demo Scenarios

### Demo 1: Retry Logic
```bash
# Simulate API failure then recovery
# Agent should retry and succeed
uv run agent.py "What is FastAPI?"
```

### Demo 2: Caching
```bash
# Ask a question that requires reading the same file twice
# Second read should be instant (cache hit)
uv run agent.py "Compare the items and learners routers"
```

## Success Criteria

- ✅ Retry logic handles 429/5xx errors
- ✅ Cache prevents duplicate tool calls
- ✅ Tests pass
- ✅ AGENT.md updated
- ✅ PR merged following git workflow
