# Research and Modelling Team
A multi-agent research team for designing and building complex modelling frameworks.

## Init
1. Check tmux is available: run tmux -V. If not found, stop and prompt the user to install tmux.
2. Ensure teammateMode is set to tmux in ~/.claude.json. Set it if missing.
3. Read @.agents/orchestrator.md first.
4. If objective or active team are empty, prompt the user for:
   - Project objective (one sentence minimum)
   - Which agents to involve (suggest from ## Agents below if unsure)
5. Once confirmed, write the objective and active team into @.agents/orchestrator.md.
6. Read @agent-docs/agent-teams.md to understand how to build effective agent teams.
7. Do not dispatch any agent until @.agents/orchestrator.md is fully populated.

## Tmux Layout
Split pane mode is strictly enforced. On init, set teammateMode to tmux in ~/.claude.json:

  { "teammateMode": "tmux" }

Or launch with: claude --teammate-mode tmux

If tmux is not available, abort and prompt the user to install it before continuing.
Do not fall back to in-process mode.

Pane layout:
- Left pane: orchestrator (persistent for the full session)
- Right pane: split vertically, one pane per active agent
- Each pane is labelled with the agent role name
- Close agent panes when an agent completes and is no longer active

## Stages
Staged execution is optional. By default the orchestrator follows the objective end-to-end
and dispatches all active agents as needed without requiring stage confirmation.

If the user explicitly requests staged delivery, typical stage patterns are:

  Research stage:   researcher, curator, data-analyst, code-analyst
  Design stage:     orchestrator reviews research outputs and writes implementation plan
  Build stage:      backend-engineer, frontend-engineer
  QA stage:         qa-engineer
  Report stage:     reporter

- The user may signal entering a new stage at any time. Orchestrator pauses, confirms the
  new stage scope and active agents, then continues.
- Reporter may be called at the end of any stage, not just the final one.
- Custom or combined stages are allowed at user discretion.

## Agent Spawning
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 is set in .claude/settings.json to enable Claude Code
to spawn subagents. This is required for the orchestrator to dispatch agents autonomously.

## Permissions
Agents may execute the following autonomously without prompting the user.
Actual enforcement is via .claude/settings.json.

All agents:
- Read, Edit, Write, Glob within their designated directories
- Bash: mkdir, ls, find, du, git status, git diff, git log, git add, git commit

Researcher agent:
- WebSearch, WebFetch
- Bash: curl, wget (lightweight checks only, curator handles downloads)
- Agent: spawn sub-agents for parallel domain research

Curator agent:
- WebFetch, WebSearch
- Bash: curl, wget, git clone (files under 50MB only)

Analyst agents (code, data):
- Bash: uv, ruff, rustfmt, pytest, markdownlint, static analysis tools

Engineer agents (backend, frontend):
- Bash: uv, cargo, ruff, rustfmt, clippy, npx, node, vitest, pytest, markdownlint

QA engineer:
- Bash: pytest, cargo test, vitest

Always requires user approval (enforced via deny rules in .claude/settings.json):
- git push
- rm -rf
- git reset --hard
- git rebase
- Any destructive database operation
- Any download exceeding 50MB

## Models
- Default model for all agents: claude-sonnet-4-6
- Use claude-opus-4-6 only when the user explicitly requests complex or high-stakes output.
- Orchestrator always runs on claude-opus-4-6 as it is the central decision-maker.

## Rules
- All tasks route through the orchestrator.
- No agent modifies another agent's output directly.
- Agents run in parallel workstreams where possible.
- Each agent has read-only access to teammates' outputs.
- Agents may request information from teammates via the orchestrator only.
- Ask the user before deleting files or pushing to remote. Commits are autonomous.
- Never run git push, rm -rf, git reset --hard, or git rebase without explicit user approval.
- If blocked, report to orchestrator. Do not proceed unilaterally.
- Orchestrator and Reporter are mandatory in every team configuration.
- No non-ASCII characters in any agent output or agent file.

## Code Style
- Python: max line length 88, linter Ruff
- Rust: max line length 100, linter rustfmt
- Markdown: max line length 100, linter markdownlint
- All other files: wrap naturally at 100 chars where appropriate
- Do not use Python scripts to enforce line length. Write naturally and break at a sensible point.

## Commit Cadence
Agents commit independently and autonomously. Do not batch all work into a single commit at the end.

Commit after each discrete, self-contained unit of work:
- Researcher: after completing each findings file or summary
- Curator: after cataloguing each resource and updating the index
- Code analyst: after completing analysis of each file or module
- Data analyst: after completing profiling and analysis of each dataset
- Backend engineer: after each function, module, or feature is implemented and linted
- Frontend engineer: after each component or interface unit is implemented and linted
- QA engineer: after writing each test suite and after each test run result is recorded
- Reporter: after each report is written

Do not commit broken, partial, or unlinted work.
Run linter before every commit. If linter fails, fix before committing.
Use the commit convention and scope defined below for every commit.

## Commit Convention
All engineer agents use standard conventional commits:
- feat: new feature
- fix: bug fix
- docs: documentation only
- refactor: restructure without behaviour change
- test: tests only
- perf: performance improvement
- chore: build, deps, tooling
- ci: CI/CD config
- style: formatting, linting, no logic change
Scope in parentheses where helpful, e.g. feat(model): or fix(api):

## Citations
- All agents must cite every external source they use.
- Code: reference file path and line range, or show full code block.
- Quotes: include source and page number if available.

## Repos
- Backend and frontend each live in user-specified repos confirmed by orchestrator on init.
- schema/ lives at project root and is written by backend, read by frontend and QA.
- Backend produces schema/ whenever frontend-engineer is in the active team.
- Frontend builds strictly from schema/. Never assumes backend internals.
- QA reads both repos and schema/ but does not modify application code.
- A project may contain backend only. Frontend is optional.

## Workspace
- Orchestrator writes an implementation plan to agent-plan/ before dispatching any task.
- agent-plan/ is gitignored by default. It is a local working directory only.
- Plan file named after the objective, e.g. agent-plan/objective-name.md.
- All agents and the user may read agent-plan/ at any time.
- Orchestrator updates the plan if scope changes during execution.
- Researcher writes to agent-findings/ only. No default subdirectories. Researcher may create
  subdirectories at its own discretion for high-volume distinct topics.
- Curator writes to agent-catalogue/code/ and agent-catalogue/data/ only. These directories are
  exclusive to the curator. No other agent writes to agent-catalogue/.
- Code analyst writes to agent-analysis/code/ only.
- Data analyst writes to agent-analysis/data/ only.
- All agents may read from agent-findings/, agent-catalogue/, agent-analysis/code/, and
  agent-analysis/data/ but only the designated agent writes to each directory.
- Reporter writes all outputs to agent-report/ (create if it does not exist).
- agent-docs/ is read-only for all agents. It is a reference library, not a working directory.
- No agent writes outside their designated directory.

## Output Format
Every agent returns:
- status: done | blocked | needs_review
- summary: what was done
- next_agent: who should act next (if applicable)

## Agents
- @.agents/orchestrator.md
- @.agents/researcher.md
- @.agents/curator.md
- @.agents/data-analyst.md
- @.agents/code-analyst.md
- @.agents/backend-engineer.md
- @.agents/frontend-engineer.md
- @.agents/qa-engineer.md
- @.agents/reporter.md
