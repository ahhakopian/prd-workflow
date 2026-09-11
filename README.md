# RDP Workflow

## Iteration 1 operator CLI

Start a run from one UTF-8 Markdown Source PRD:

```console
rdp start path/to/source-prd.md
```

The command prints the run ID in `INTAKE`. Progress is always explicit: each
invocation below performs exactly one FSM step, so repeat it only when the
reported next action says to do so.

```console
rdp advance <run-id>
rdp status <run-id>
```

When the state is `WAITING_HUMAN`, `advance` and `status` show the complete
pending decision, all options and consequences, any superseded decision, and a
visibly advisory recommendation. Answer it in one of three forms:

```console
rdp answer <run-id> <decision-id> --option <option-id>
rdp answer <run-id> <decision-id> --option <option-id> --clarification "<human text>"
rdp answer <run-id> <decision-id> --custom "<human text>"
```

Runs are stored under `.rdp/runs/`. After a process or machine restart, run
`rdp status <run-id>` and continue with the reported `answer` or `advance`
command. Once the state is `DONE`, obtain the sole handoff artifact with:

```console
rdp handoff <run-id>
```

The handoff prints only the path to `canonical-rdp.md`. SpecKit is not executed
by this workflow and receives only that file from a `DONE` run.
