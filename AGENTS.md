# cpp-core

A small C++26 library: a logging module (`com.rsm.logging`), a string-catalog path, and C++26
static reflection. It builds with two compilers, GCC 16 (libstdc++) and clang-p2996 (libc++),
and it is deliberately conservative about what enters the module interface.

## Workflow facts

- **Check:** `mise run audit:verify` runs every check that does not need a compiler: the audit's
  item counts, duplicate and dangling IDs, the decisions sheet against the open list, the counts
  the prose claims, Markdown table shape, fence balance, relative links, the parts tables, the
  privacy scan, and the vendored upstream copies. It is fast, it needs nothing but Python, and it
  must pass before each commit.
- **Shipping:** a change is a local commit. **There is no git remote** - every commit in this
  repository is local and nothing has been pushed. Do not push, do not open a pull request, and do
  not create a branch for a change unless the owner asks for one.
- **Research:** the notes live in `docs/cxx26-features-audit/`. The open items are in
  `open-items.md`; the owner's decisions are in `decisions.md`; `PARKED.md` is the map of the
  whole effort and what each part changed.
- **Review approval:** there is no approval pane in this repository. The owner's decision on each
  open item is the approval, and it is recorded in `decisions.md` and `open-items.md`.
- **Content guard:** the privacy scan inside `mise run audit:verify` is the content guard. It
  checks the tracked files and the working tree for a machine name, a host name, a LAN or tailnet
  address, an account or organisation name, a real name and a private project name - and it
  **derives those values at run time**, from this machine's git identity, from this repository's
  own history and from the machine name, so that no private value is stored in the repository. An
  untracked `.audit/privacy-patterns.txt` can add more.

## The lane

**The build lane is parked.** As of 2026-11-12 the owner's decision is that this repository is
research-only:

- no builds, no compiler or toolchain installs or configuration, no CMake or preset runs, no test,
  sanitizer or coverage runs;
- **source files are out of scope** - the documentation is in scope;
- anything that would need a compile is written down as an open item instead of guessed at.

`PARKED.md` records what is parked and what the plan is when the lane reopens. Do not "just try
it" with a compiler.

## The rules

- **Both compilers keep working.** `gcc16` (GCC 16.2, libstdc++) and `p2996` (clang-p2996,
  libc++), both in C++26 mode. The preset matrix is in `cmake/presets/cpp-core.json`. A change
  that works on one and not the other is not done.
- **The module interface stays free of the C++ standard library.** A module's global module
  fragment is copied into every importing translation unit, and two copies of a standard header
  collide. (That is the observed failure mode, not the standard's rule - see `DEF-3`.)
- **`modules/logging/format.hpp` is private.** It is the module's own formatter; it is not in the
  public interface and it does not enter the module's purview.
- **The vcpkg manifest and the overlay ports are the dependency contract.** The manifest is
  `vcpkg.json`; the overlays are in `ports/`; the triplet is in `triplets/`.
- **The catalog IDs are wire identifiers.** They are the `ID` attributes a MIPI Sys-T consumer
  decodes against, so an ID that moves between releases is a wire format that changed. `DEF-6` is
  the defect; `BUILD-7` is the decision that fixes it.
- **Custom formatters are written for `fmt` only** - quill bundles its own copy of fmt
  (`fmtquill`), and the two copies are structural, not an accident.
- **The test framework's module variant is not used.** `import ut;` makes the `std` module
  reachable in the test translation unit and GCC 16 then collides with the standard headers the
  test file needs.

## Privacy

- **A machine name, host name, LAN address, tailnet name, account name, organisation name, real
  name or private project name is never written into a tracked file, a commit message, a pull
  request, an issue or a comment.** A file that needs one becomes a template that reads the value
  at apply time, and the public text names only the role.
- **This is forward-only.** Old branches, worktrees, commits, closed pull requests and old job
  logs are **not** scrubbed or backfilled. Nothing in the history is rewritten.
- **No key value is ever printed.** Report key-file paths only.
- Values are injected with `mise run secret:set NAME` - the value is piped in, never passed as an
  argument - and **never** with `fnox set`.
- On this machine, `fnox get`, `exec`, `export`, `edit`, `tui`, `mcp`, `push` and `list --values`
  may not be run. Use `fnox --non-interactive proxy run -- <command>`.

## The audit's conventions

The audit is a numbered set of parts, and the parts are indexed in two places that must agree:
`docs/cxx26-features-audit/README.md` and `PARKED.md`.

- Every item carries an ID - `DEF-n`, `FMT-n`, `QUIL-n`, `TOOL-n`, `MOD-n`, `REFL-n`, `MAC-n`,
  `COV-n`, `BUILD-n`, `VCPKG-n`, `ENV-n` - and **an ID is never renumbered**. A retired item keeps
  its ID and moves to `open-items.md` section 13.
- Every item says what settles it. The wording in the Markdown is prose; the machine-readable
  classification is in `docs/cxx26-features-audit/audit-index.json`.
- **That JSON is derived, never authored.** `scripts/audit_index.py` parses `open-items.md` into
  it. Edit the Markdown and run `mise run audit:index`; never edit the JSON by hand.
- `scripts/audit_summary.py` answers a question about the audit without reading the Markdown:
  `mise run audit:summary -- --prefix MOD`, `--owner`, `--category compile`, `--state answered`,
  `--id MOD-11`, `--counts`.
- New research is a new part: a number, a file, a row in both parts tables, and a section in
  `PARKED.md` saying what it changed.

## The scripts

All of them are stdlib-only Python, and none of them invokes a compiler.

| script | what it does |
|---|---|
| `scripts/audit_index.py` | parses `open-items.md` into the registry (`--write`, `--check`) |
| `scripts/verify_audit.py` | every check that does not need a compiler |
| `scripts/test_verify_audit.py` | breaks the tree 13 ways and asserts that the checker catches each one |
| `scripts/audit_summary.py` | the registry, sliced - the answer without the reading |
| `scripts/audit_metrics.py` | what the automation is worth, measured rather than asserted |
| `scripts/measure.py` | measures the project: its shape, its discipline, its API, its audit coverage, its dependency closure (`--write`, `--check`) |
| `scripts/verify_upstream.py` | the vendored upstream copies against `upstream/manifest.json` |
| `scripts/check_overlay_drift.py` | the overlay ports' pins against their upstreams' tips (`--network`) |

**Run `mise run audit:test` before you trust the checker.** A check that never fails is not a
check; the test breaks the tree thirteen ways and asserts that each one is caught. If you add a
check, add a mutation for it.

**The measurement harness has a committed baseline.** `docs/cxx26-features-audit/measurements.json`
is derived from the tree by `scripts/measure.py`, never hand-edited; `mise run audit:measure`
regenerates it with `--write` and the checker fails when it is stale. It is a ruler, not a verdict -
it counts, and it does not judge.

**And there is a bar the ruler is held to.** `docs/cxx26-features-audit/acceptance.json` is the
acceptance bar: the constraints the project must not lose, the targets it is heading towards, and
the metrics that cannot be measured yet. It is **authored, not derived** - a standard, not a
snapshot - and the harness reads it and never edits it. Only the owner moves a threshold.
`mise run audit:acceptance` checks the tree against it, and the checker fails when it is
violated.

## Agent skills

- `implement` - build one ticket from an existing plan, staged, not committed.
- `implement-spec` - build every open ticket of a spec, one worker per ticket.
- `work` - set the repository up, then name the next ready ticket.
- `visual-plan` - publish a plan as a commentable page.
- `ticket-retro` - the retrospective when a ticket or spec is finished.
