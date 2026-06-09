# Agent Patterns

This document explores autonomous agent architectures for local AI execution.

## Overview

Agents are LLM systems that can:
- Plan multi-step tasks
- Execute tools/actions
- Observe results
- Reason about next steps
- Self-correct when failures occur

```
┌─────────────────────────────────────────────────┐
│                   AGENT LOOP                     │
│                                                 │
│   Goal ──► Plan ──► Execute ──► Observe         │
│              ▲                    │            │
│              └────── Reflect ◄────┘            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Agent Architectures

### 1. ReAct (Reasoning + Acting)

**Pattern**: Think → Act → Observe → Repeat

**Example**:
```
Question: How much space is used by Downloads folder?

Thought: I need to check the Downloads folder size.
Action: run_shell
Action Input: "du -sh ~/Downloads"
Observation: 15G    /Users/user/Downloads

Thought: I have the answer.
Answer: The Downloads folder uses 15GB.
```

**Implementation**:
```python
def react_agent(question: str, max_iterations: int = 10):
    context = f"Question: {question}\n"

    for _ in range(max_iterations):
        response = query_ollama(f"{context}\nThink step-by-step and choose an action.")
        action = parse_action(response)

        if action["type"] == "answer":
            return action["content"]

        observation = execute_tool(action["name"], action["args"])
        context += f"\nAction: {action['name']}\nObservation: {observation}"

    return "Max iterations reached without answer"
```

---

### 2. Plan-and-Solve

**Pattern**: Generate full plan → Execute steps

**Implementation**:
```python
def plan_and_solve(goal: str):
    plan_response = query_ollama(f"""
    Goal: {goal}

    Create a numbered step-by-step plan.
    Each step should be a single action.

    Plan:
    """)

    steps = parse_plan(plan_response)
    results = []

    for step in steps:
        action = identify_action(step)
        result = execute_tool(action["name"], action["args"])
        results.append({"step": step, "result": result})

    return results
```

---

### 3. Tool Use (Function Calling)

**Pattern**: LLM selects and invokes tools with parameters

**Tool Definition**:
```python
TOOLS = [
    {
        "name": "read_file",
        "description": "Read contents of a file",
        "parameters": {
            "path": {"type": "string", "required": True}
        }
    },
    {
        "name": "list_directory",
        "description": "List files in a directory",
        "parameters": {
            "path": {"type": "string", "required": True},
            "recursive": {"type": "boolean", "default": False}
        }
    },
    {
        "name": "move_file",
        "description": "Move or rename a file",
        "parameters": {
            "source": {"type": "string", "required": True},
            "destination": {"type": "string", "required": True}
        }
    }
]
```

---

## Safety Guardrails

### Sandboxing

```python
SAFE_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Downloads",
]

def safe_path(path: str) -> bool:
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(d) for d in SAFE_DIRS)

def safe_read(path: str) -> str:
    if not safe_path(path):
        raise PermissionError(f"Access denied: {path}")
    return Path(path).read_text()
```

### Confirmation for Dangerous Operations

```python
DANGEROUS_TOOLS = {"delete_file", "move_file", "run_command"}

def execute_tool(name: str, args: dict, require_confirm: bool = True):
    if name in DANGEROUS_TOOLS and require_confirm:
        confirm = input(f"Confirm {name}({args})? [y/N]: ")
        if confirm.lower() != "y":
            return "Operation cancelled by user"
    return TOOLS[name](**args)
```

---

## Memory and Context

### Conversation Memory

```python
class ConversationMemory:
    def __init__(self, max_tokens: int = 4000):
        self.messages = []
        self.max_tokens = max_tokens

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.trim_if_needed()

    def trim_if_needed(self):
        while self.token_count() > self.max_tokens:
            self.messages.pop(0)

    def token_count(self) -> int:
        return sum(len(m["content"]) // 4 for m in self.messages)

    def get_context(self) -> str:
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.messages)
```

### Long-term Memory (with RAG)

```python
def remember_important(content: str):
    embedding = get_embedding(content)
    collection.add(
        embeddings=[embedding],
        documents=[content],
        ids=[f"memory_{time.time()}"],
        metadatas=[{"type": "agent_memory"}]
    )

def recall_relevant(query: str) -> list[str]:
    results = collection.query(
        query_embeddings=[get_embedding(query)],
        n_results=5,
        where={"type": "agent_memory"}
    )
    return results["documents"][0]
```

---

## Current Status

**Phase**: Research and prototyping

**Immediate steps**:
- [ ] Implement basic ReAct agent
- [ ] Define safe tool set
- [ ] Test with file organization tasks
- [ ] Add reflection and self-correction

**Future**:
- [ ] Hierarchical agents
- [ ] Tool learning
- [ ] Multi-agent collaboration
- [ ] Integration with n8n workflows

---

## Resources

- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [Tool Learning with LLMs](https://arxiv.org/abs/2305.10034)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)

---

Next: [Roadmap](roadmap.md) for long-term evolution.
