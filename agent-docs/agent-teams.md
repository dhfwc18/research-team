# Agent Teams Reference Guide

Source: https://code.claude.com/docs/en/agent-teams
Purpose: Reference for the orchestrator to build effective agent teams in this project.

---

## What Are Agent Teams

Agent teams coordinate multiple Claude Code instances working together. One session acts as the
team lead, coordinating work, assigning tasks, and synthesising results. Teammates work
independently, each in its own context window, and communicate directly with each other.

Unlike subagents (which run within a single session and only report back to the main agent),
teammates can message each other directly without going through the lead.

Requires Claude Code v2.1.32 or later. Check with: claude --version

---

## Enabling Agent Teams

Already enabled in this project via .claude/settings.json:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

---

## Subagents vs Agent Teams

| | Subagents | Agent Teams |
|---|---|---|
| Context | Own context window; results return to caller | Own context window; fully independent |
| Communication | Report results back to main agent only | Teammates message each other directly |
| Coordination | Main agent manages all work | Shared task list with self-coordination |
| Best for | Focused tasks where only the result matters | Complex work requiring discussion and collaboration |
| Token cost | Lower: results summarised back to main context | Higher: each teammate is a separate Claude instance |

Use subagents for quick focused workers. Use agent teams when teammates need to share
findings, challenge each other, and coordinate on their own.

---

## When to Use Agent Teams

Best use cases:
- Research and review: multiple teammates investigate different aspects simultaneously
- New modules or features: teammates each own a separate piece without conflicts
- Debugging with competing hypotheses: teammates test different theories in parallel
- Cross-layer coordination: changes spanning frontend, backend, and tests

Avoid agent teams for:
- Sequential tasks
- Same-file edits
- Work with many interdependencies
Use a single session or subagents for these instead.

---

## Display Modes

| Mode | Description | Requirement |
|---|---|---|
| in-process | All teammates run inside main terminal. Shift+Down to cycle. | Any terminal |
| split panes | Each teammate gets its own pane. Click to interact. | tmux or iTerm2 |

Default is "auto": uses split panes if already in a tmux session, in-process otherwise.

Override in ~/.claude.json:
```json
{ "teammateMode": "in-process" }
```

Or per session:
```bash
claude --teammate-mode in-process
```

This project uses tmux split pane mode when available. See CLAUDE.md ## Tmux Layout.

---

## Architecture

| Component | Role |
|---|---|
| Team lead | Main Claude Code session. Creates team, spawns teammates, coordinates work. |
| Teammates | Separate Claude Code instances. Each works on assigned tasks. |
| Task list | Shared list of work items that teammates claim and complete. |
| Mailbox | Messaging system for communication between agents. |

Storage locations:
- Team config: ~/.claude/teams/{team-name}/config.json (auto-managed, do not edit by hand)
- Task list: ~/.claude/tasks/{team-name}/

---

## Spawning Teammates

Tell the lead in natural language. Example:

```
Create an agent team with three teammates:
- One for literature research
- One for data analysis
- One for code analysis
Use Sonnet for each teammate.
```

To use a subagent definition (role defined in .agents/):

```
Spawn a teammate using the data-analyst agent type to profile the dataset.
```

The teammate honours that definition's tools and model. The definition body is appended to the
teammate's system prompt. Team coordination tools (SendMessage, task management) are always
available regardless of tools restriction.

Note: skills and mcpServers frontmatter fields in subagent definitions are NOT applied when
running as a teammate. Teammates load these from project and user settings instead.

---

## Task Management

Tasks have three states: pending, in-progress, completed.
Tasks can depend on other tasks. A pending task with unresolved dependencies cannot be claimed
until those dependencies are completed.

Task claiming uses file locking to prevent race conditions.

The lead can assign tasks explicitly or teammates can self-claim after finishing their current
task. Having 5-6 tasks per teammate keeps everyone productive without excessive context switching.

---

## Communication Between Agents

- message: send to one specific teammate by name
- broadcast: send to all teammates simultaneously (use sparingly, costs scale with team size)

Teammates receive messages automatically. The lead does not need to poll.
When a teammate finishes and goes idle, it automatically notifies the lead.

---

## Plan Approval Mode

For complex or risky tasks, require teammates to plan before implementing:

```
Spawn a backend-engineer teammate to refactor the auth module.
Require plan approval before they make any changes.
```

The teammate works in read-only plan mode until the lead approves. If rejected, the teammate
revises and resubmits. Give the lead criteria in the prompt, e.g.:
"Only approve plans that include test coverage."

---

## Quality Gates with Hooks

- TeammateIdle: runs when a teammate is about to go idle. Exit code 2 to send feedback and keep working.
- TaskCreated: runs when a task is being created. Exit code 2 to prevent creation with feedback.
- TaskCompleted: runs when a task is being marked complete. Exit code 2 to prevent completion with feedback.

---

## Shutdown and Cleanup

Shut down a teammate:
```
Ask the data-analyst teammate to shut down
```

Clean up the full team:
```
Clean up the team
```

Always use the lead to clean up. Teammates should not run cleanup themselves.
Shut down all teammates before running cleanup.

---

## Best Practices

### Team size
- Start with 3-5 teammates for most workflows
- Token costs scale linearly with teammate count
- 5-6 tasks per teammate is a productive ratio
- Scale up only when work genuinely benefits from parallelism

### Task sizing
- Too small: coordination overhead exceeds the benefit
- Too large: teammates work too long without check-ins
- Just right: self-contained units with a clear deliverable (a function, a test file, a review)

### Context for teammates
Teammates do NOT inherit the lead's conversation history. Include task-specific details in the
spawn prompt:

```
Spawn a literature-researcher teammate with the prompt:
"Search for papers on Bayesian hierarchical models applied to ecological data.
Focus on sources from arXiv and government datasets published after 2020.
Write findings to agent-findings/literature/bayesian-ecology.md."
```

### Avoiding file conflicts
Two teammates editing the same file leads to overwrites. Each teammate should own a different
set of files or directories. This project enforces this via designated output directories per
agent role. See CLAUDE.md ## Workspace.

### Monitoring
- Check in on teammates regularly
- Redirect approaches that are not working
- If the lead starts doing work instead of delegating, tell it: "Wait for your teammates to
  finish before proceeding."

### Start simple
If new to agent teams, start with research and review tasks before parallel implementation.
These show the value of parallel exploration without coordination challenges.

---

## Permissions

Teammates start with the lead's permission settings. If the lead runs with
--dangerously-skip-permissions, all teammates do too. You can change individual teammate modes
after spawning but not at spawn time.

This project's permission settings are in .claude/settings.json.

---

## Limitations (Experimental)

- No session resumption with in-process teammates: /resume and /rewind do not restore teammates
- Task status can lag: teammates sometimes fail to mark tasks complete, blocking dependents
- Shutdown can be slow: teammates finish their current request before shutting down
- One team per session: clean up the current team before starting a new one
- No nested teams: teammates cannot spawn their own teams
- Lead is fixed: the session that creates the team is lead for its lifetime
- Permissions set at spawn: cannot set per-teammate modes at spawn time
- Split panes require tmux or iTerm2: not supported in VS Code terminal, Windows Terminal, Ghostty

---

## Troubleshooting

### Teammates not appearing
- In in-process mode, press Shift+Down to cycle through active teammates
- Check tmux is installed: which tmux
- Ensure the task was complex enough to warrant a team

### Too many permission prompts
Pre-approve common operations in .claude/settings.json before spawning teammates.

### Teammates stopping on errors
Use Shift+Down to check output, then give additional instructions directly or spawn a replacement.

### Lead shuts down before work is done
Tell it: "Keep going, not all tasks are complete."

### Orphaned tmux sessions
```bash
tmux ls
tmux kill-session -t <session-name>
```

---

## Related

- Subagents: https://code.claude.com/docs/en/sub-agents
- Git worktrees for manual parallel sessions: https://code.claude.com/docs/en/common-workflows
- Permissions: https://code.claude.com/docs/en/permissions
- Token costs: https://code.claude.com/docs/en/costs
