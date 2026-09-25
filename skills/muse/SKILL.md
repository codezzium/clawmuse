---
name: muse
description: Delegate research and test runs to Muse (Meta's Muse Spark coding agent) with the `muse-ask` command, so file reading, searching, web lookups and long test/build output are spent on Muse instead of Claude's context and quota. Use for multi-file code exploration, "where/how does X work" questions, web or docs research, running test suites or builds and summarizing failures, and digesting long logs. Skip it for one small file you already know, for edits, and for quick one-line checks.
argument-hint: "[research|test] <what to find out or run>"
allowed-tools: Bash(muse-ask *)
---

# Delegating to Muse

`muse-ask` runs Muse headless and prints only Muse's final report plus one footer line. Muse cannot see this conversation: the brief must stand on its own.

```
muse-ask [-m research|test] [-C DIR] [-w WORDS] [-t SECS] [-c SESSION] [-i IMAGE] "brief"
```
(or pipe a longer brief on stdin: `muse-ask -m test - <<'EOF' ... EOF`)

- `-m research` (default) is read-only: Muse's edit tools are off and it is told not to change state. `-m test` may run tests, builds and containers but not edit source, commit or deploy.
- `-C` workspace (default: cwd). Muse always runs muse-spark-1.3 at max effort; this is fixed and there is no option to change it.
- `-w` report word budget (default 300). `-t` Muse timeout in seconds (default 540).
- `-c SESSION` asks a follow-up in the same Muse session, which still holds everything it read. Use it instead of re-briefing.
- Footer: `[muse · mode · time · N tools, X chars read · session ID · log PATH]`. The .md log holds every tool output Muse saw (test output, file reads). Grep it instead of re-running anything.

## Writing the brief
Say the goal, where to start (absolute paths), what you already know, the constraints (how tests run in this project, which container, what must not be touched), the exact questions, and the report shape you want. Put one independent question in each brief.

## Running it
- Calls take from ~20 s to several minutes. For anything beyond a quick lookup, run with `run_in_background: true` and keep working. In the foreground, give Bash a `timeout` of at least `-t` × 1000 + 30000 ms.
- Run independent briefs in parallel as separate background calls.
- Exit codes: 0 means a report. 1 means Muse failed (the reason is printed). 124 is a timeout and prints a `-c` resume hint. 2 is a usage error or a nested call.

## Trusting the report
Muse can be wrong, but re-reading what it already read throws the savings away. Verify only what you will act on, such as the line you are about to edit, a root cause you will fix, or "tests pass" before you call the work done. Check it with one narrow Grep, a Read with offset/limit, or a grep of the log; never re-read whole files. Relay explanations as they are. If the report is thin or vague, follow up with `-c SESSION` rather than redoing the work yourself. If Muse is unavailable (exit 127, or it keeps failing), fall back to your own tools.

## When invoked as /clawmuse:muse
If the arguments start with `research` or `test`, use that as the mode. Write a self-contained brief from the rest plus the conversation context, run it, then relay the result: `$ARGUMENTS`
