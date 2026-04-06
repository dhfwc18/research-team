# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A multi-agent research team framework. An orchestrator (Opus) coordinates specialized agents
(Sonnet) that run as Claude Code teammates in tmux split panes. Agents research, catalogue,
analyse, build, test, and report — each writing only to its designated directory.

## Init Sequence

1. Verify tmux: `tmux -V` (abort if missing)
2. Ensure `teammateMode: "tmux"` in `~/.claude.json`
3. Read `.agents/orchestrator.md` — if Objective or Active Team is empty, prompt the user
4. Read `agent-docs/agent-teams.md` for team coordination patterns
5. Do not dispatch agents until orchestrator.md is fully populated

Launch: `tmux new -s research && claude` (or `claude --teammate-mode tmux` for single-pane)

## Architecture

```
Orchestrator (Opus) ──┬── Research: Researcher ←→ Curator
                      ├── Analysis: Code Analyst, Data Analyst
                      ├── Engineering: Backend ←→ Frontend ←→ QA
                      └── Reporter (runs last every cycle)
```

All tasks route through the orchestrator. No agent modifies another's output directly.
Agents communicate via the orchestrator only. Parallel workstreams where agents are independent.

## Workspace Directories

| Directory | Owner | Notes |
|---|---|---|
| `agent-plan/` | Orchestrator | Gitignored. Plan written before any dispatch. |
| `agent-findings/` | Researcher | Subdirs at researcher discretion |
| `agent-catalogue/code/`, `data/` | Curator | Exclusive to curator |
| `agent-analysis/code/` | Code Analyst | |
| `agent-analysis/data/` | Data Analyst | |
| `schema/` | Backend Engineer | Read by Frontend and QA |
| `agent-report/` | Reporter | Created if missing |
| `agent-docs/` | Read-only | Reference library for all agents |

No agent writes outside its designated directory.

## Agent Definitions

All agent prompts live in `.agents/`. Each defines identity, model, tools, output directory,
instructions, and constraints. Orchestrator and Reporter are mandatory in every team.

Default model: `claude-sonnet-4-6`. Orchestrator always uses `claude-opus-4-6`.
Use Opus for other agents only when the user explicitly requests it.

## Key Rules

- Orchestrator writes implementation plan to `agent-plan/` before dispatching anything
- Researcher passes links to Curator (does not download). If no Curator, logs sources only.
- Backend produces `schema/` when Frontend is active. Frontend builds strictly from schema.
- QA does not modify application code — reports failures to orchestrator for engineer dispatch.
- Reporter returns `status: blocked` when facts are insufficient (never writes partial reports).
- Downloads over 50MB require user approval and are always gitignored.

## Code Style

- Python: line length 88, Ruff, type hints on all signatures, `uv` as package manager
- Rust: line length 100, rustfmt, clippy must pass
- Markdown: line length 100, markdownlint
- No non-ASCII characters in any agent output

## Commit Convention

Conventional commits required. Agents commit independently after each discrete unit of work.
Lint before every commit. Never commit broken or partial work.

Prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `perf:`, `chore:`, `ci:`, `style:`
Scope in parentheses where helpful, e.g. `feat(model):`, `docs(findings):`

## Permissions

Pre-approved in `.claude/settings.json`: file ops, git (status/diff/log/add/commit), build
tools (uv, cargo, ruff, rustfmt, clippy, pytest, vitest, npx, node), web access, curl/wget.

Always requires user approval: `git push`, `rm -rf`, `git reset --hard`, `git rebase`,
destructive database operations, downloads over 50MB.
