# Research and Modelling Team
A multi-agent research team for designing and building complex modelling frameworks.

## Init
1. Read @.agents/orchestrator.md first.
2. If objective or active team are empty, prompt the user for:
   - Project objective (one sentence minimum)
   - Which agents to involve (suggest from ## Agents below if unsure)
3. Once confirmed, write the objective and active team into @.agents/orchestrator.md.
4. Do not dispatch any agent until @.agents/orchestrator.md is fully populated.

## Tmux Layout
If running inside a Tmux session, use split pane mode:
- Left pane: orchestrator (persistent across all stages)
- Right pane: split vertically per active agent in the current stage
- Each agent gets its own pane labelled with its role name
- Close agent panes when an agent completes its stage and is no longer active
- Orchestrator pane stays open for the full session

## Stages
Staged execution is optional. By default the orchestrator follows the objective end-to-end
and dispatches all active agents as needed without requiring stage confirmation.

If the user explicitly requests staged delivery, typical stage patterns are:

  Research stage:   literature-researcher, resource-researcher, data-analyst, code-analyst
  Design stage:     orchestrator reviews research outputs and writes implementation plan
  Build stage:      backend-engineer, frontend-engineer
  QA stage:         qa-engineer
  Report stage:     reporter

- The user may signal entering a new stage at any time. Orchestrator pauses, confirms the
  new stage scope and active agents, then continues.
- Reporter may be called at the end of any stage, not just the final one.
- Custom or combined stages are allowed at user discretion.

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
- Ask the user before deleting files, committing, or pushing to remote.
- If blocked, report to orchestrator. Do not proceed unilaterally.
- Orchestrator and Reporter are mandatory in every team configuration.
- No non-ASCII characters in any agent output or agent file.

## Code Style
- Python: max line length 88, linter Ruff
- Rust: max line length 100, linter rustfmt
- Markdown: max line length 100, linter markdownlint
- All other files: wrap naturally at 100 chars where appropriate
- Do not use Python scripts to enforce line length. Write naturally and break at a sensible point.

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
- Literature researcher writes to agent-findings/literature/ only.
- Resource researcher writes to agent-findings/resource/ only.
- Code analyst writes to agent-analysis/code/ only.
- Data analyst writes to agent-analysis/data/ only.
- All agents may read from agent-findings/, agent-analysis/code/, and agent-analysis/data/ but only
  the designated agent writes to each subdirectory.
- Reporter writes all outputs to agent-report/ (create if it does not exist).
- No agent writes outside their designated directory.

## Output Format
Every agent returns:
- status: done | blocked | needs_review
- summary: what was done
- next_agent: who should act next (if applicable)

## Agents
- @.agents/orchestrator.md
- @.agents/literature-researcher.md
- @.agents/resource-researcher.md
- @.agents/data-analyst.md
- @.agents/code-analyst.md
- @.agents/backend-engineer.md
- @.agents/frontend-engineer.md
- @.agents/qa-engineer.md
- @.agents/reporter.md
