# clawmuse

[Türkçe](README.tr.md)

A Claude Code plugin that hands research and test runs to **Muse** (Meta's Muse Spark coding agent, the `muse` CLI), so Claude spends fewer tokens.

Claude writes a short brief. Muse does the reading, searching, web lookups and test runs on its own quota. Only Muse's compact report comes back into Claude's context: typically a few thousand characters, where Muse itself read tens or hundreds of thousands.

## How it works

| Part | What it does |
| --- | --- |
| `bin/muse-ask` | Runs `muse exec --json` headless and prints only Muse's final report plus a one-line footer. It is on `PATH` while the plugin is enabled. |
| `skills/muse` | Tells Claude when to delegate and how to write a brief. It loads only when used. |
| SessionStart hook | Tells Claude, once per session, that Muse is available. |
| UserPromptSubmit hook | When your message mentions Muse, tells Claude to delegate that turn instead of leaving it to its own judgement. |

Claude still does the edits and the final verification. Muse only investigates and runs things.

## Requirements

- Claude Code with plugin support.
- Muse Code: the `muse` CLI installed and logged in (`muse exec` must work in your terminal).
- Python 3.8 or newer.
- Linux or macOS. Windows is not supported.

If `muse` is not installed, the hooks stay silent and Claude works as usual.

## Install

In Claude Code:

```
/plugin marketplace add codezzium/clawmuse
/plugin install clawmuse@clawmuse
```

Or from a shell:

```
claude plugin marketplace add codezzium/clawmuse
claude plugin install clawmuse@clawmuse
```

Start a new session afterwards. To receive updates, turn on auto-update for the `clawmuse` marketplace in `/plugin`, or run `claude plugin update clawmuse@clawmuse`.

## Usage

- **Automatic:** work as usual. For multi-file questions ("where/how does X work"), web or docs research, running test suites or builds, and long logs, Claude delegates on its own.
- **By mention:** name Muse and the delegation is forced for that message, e.g. *"have Muse find where the cache is invalidated, then fix it"*.
- **Explicitly:** `/clawmuse:muse test run the unit tests and summarize the failures`.

### muse-ask

```
muse-ask [-m research|test] [-C DIR] [-w WORDS] [-t SECS] [-c SESSION] [-i IMAGE] "brief"
```

| Option | Meaning |
| --- | --- |
| `-m research` | Default. Muse's file-writing tools are off, and it is told not to change any state. |
| `-m test` | May run tests, builds and containers. Must not edit source, commit or deploy. |
| `-C DIR` | Workspace for Muse. Default: the current directory. |
| `-w WORDS` | Word budget for the report. Default: 300. |
| `-t SECS` | Stop Muse after this many seconds. Default: 540. |
| `-c SESSION` | Ask a follow-up in an earlier Muse session. Muse keeps everything it already read. |
| `-i IMAGE` | Attach an image. Can be repeated. |

Muse always runs `muse-spark-1.3` at `max` reasoning effort. This is fixed on purpose: neither Claude nor the user chooses it per call.

The brief can also come from stdin: `muse-ask -m test - <<'EOF' … EOF`.

The footer shows the mode, time taken, number of tool calls, characters Muse read, the session id and the log path. Every tool output Muse saw is kept in `~/.cache/clawmuse/runs/*.md` for 7 days, so Claude can grep a log instead of re-running anything.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Report delivered |
| 1 | Muse failed |
| 2 | Usage error, or a nested call from inside Muse |
| 124 | Timeout. A resume hint is printed. |
| 127 | `muse` not found |
| 143 | Interrupted |

## Sandbox and `CLAWMUSE_YOLO`

By default, Muse runs inside its own sandbox with approvals turned off (`--trust-workspace --approval-mode never`), because nobody can answer prompts in a headless run. Research mode also disables Muse's file-writing tools.

On some Linux hosts Muse's sandbox cannot start, for example where unprivileged user namespaces are restricted. Muse's shell commands then fail, and `muse-ask` adds a note to its report.

If you accept the risk, you can allow unsandboxed runs for Claude Code by setting this in `~/.claude/settings.json`:

```json
{ "env": { "CLAWMUSE_YOLO": "1" } }
```

Muse then runs with `--yolo`: no sandbox and no approvals. Research mode still turns off Muse's file-writing tools, but writes through the shell are then forbidden only by instruction, not enforced. Claude is told never to set this variable itself.

## Example numbers

These are single runs on one React Native game repository, not a benchmark.

| Task | Muse read | Claude received |
| --- | --- | --- |
| Full client test suite (528 tests) | 44k chars | 0.7k chars |
| "How do placement animations work?" across 3 source files | 68k chars | 3k chars |
| Web research on plugin distribution (30+ pages) | 297k chars | 4.5k chars |

The same codebase question was also asked of Claude in a headless session:

| | Turns | Cost | Time |
| --- | --- | --- | --- |
| Without Muse | 16 | $0.44 | 60 s |
| With Muse | 8 | $0.28 | 150 s |

Delegation costs wall-clock time, so quick one-file lookups stay with Claude.

## Development

```
python3 -m unittest discover -s tests -v   # uses a fake muse, no network
claude --plugin-dir /path/to/clawmuse       # try local changes in one session
```

Installed copies are cached. Bump `version` in `.claude-plugin/plugin.json` when you release changes, otherwise users will not receive them.

## License

MIT. See [LICENSE](LICENSE).
