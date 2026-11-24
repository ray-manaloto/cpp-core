---
type: Project Document
title: AGENTS.md — cpp-core Agent Rules
description: Repository rules for agents working on cpp-core
resource: https://github.com/ray-manaloto/cpp-core
tags:
  - cpp-core
  - agent-rules
  - contributing
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - cpp-core
  - agent-rules
  - contributing
sources:
  - id: architecture-bundle
    resource: ./okf-bundles/architecture/index.md
    title: Architecture documentation bundle
  - id: audit-bundle
    resource: ./okf-bundles/audit/index.md
    title: C++26 features audit bundle
  - id: asan-leak-check
    resource: ./docs/asan-leak-check/README.md
    title: ASAN leak-check documentation
  - id: module-source-location
    resource: ./docs/module-source-location/README.md
    title: Module source location research
---

## AGENTS.md — cpp-core Agent Rules

> **This is a pointer document.** The full agent rules have been migrated to OKF bundles.
> See the linked bundles below for complete documentation.

### Repository: cpp-core

A small C++26 library: a logging module (`com.rsm.logging`), a string-catalog path, and C++26
static reflection. It builds with two compilers, GCC 16 (libstdc++) and clang-p2996 (libc++),
and it is deliberately conservative about what enters the module interface.

### Workflow Facts

- **Check:** `mise run audit:verify` runs every check that does not need a compiler: the audit's
  item counts, duplicate and dangling IDs, the decisions sheet against the open list, the counts
  the prose claims, Markdown table shape, fence balance, relative links, the parts tables, the
  privacy scan, the vendored upstream copies, and the citation anchor. It is fast, needs only Python, and must pass before each commit. The hk `audit-verify` step runs it in check, fix, pre-commit and pre-push, so `git commit` enforces it. No CI check gates a merge: the owner ruled on 2026-11-15 that cpp-core uses no paid services. `.github/workflows/ci.yml` runs on GitHub Actions, which is free on this public repository, as an advisory check; `ci` is not a required check, so a red run reports a problem but blocks nothing. The gate is local: `hk check --all` in the worktree and the Codex reviewer's approval.

- **Tools:** Per the **2026-11-24 owner ruling** (overturning the 2026-11-15 project-lockfile
  ruling), cpp-core declares zero `[tools]` in `.mise.toml` and commits no root `mise.lock`:
  developer tools live at user/global scope (`dotfiles-v2`), Python-packaged C++/CMake lint and
  format tools (`clang-format`, `cpplint`, `gersemi`) are pinned in `pyproject.toml` + `uv.lock`
  (`[tool.uv] package = false`, synced via `mise deps uv` / `uv sync --locked` on Python 3.14 for
  prebuilt `gersemi` wheels and run via `uv run --locked`), and advisory CI pins live in
  `.github/ci/mise.toml` + `.github/ci/mise.lock` (loaded in CI via `MISE_GLOBAL_CONFIG_FILE`).
  Renovate (`renovate.json`) opens update PRs against `.github/ci/mise.toml`, `pyproject.toml`,
  and `uv.lock`. No update merges itself: `renovate.json` turns automerge off because CI is
  advisory, so an agent checks the PR out in a worktree, runs `hk check --all` and has the Codex
  reviewer approve it before merging. To update advisory CI pins by hand: `mise run tools:outdated`,
  edit `.github/ci/mise.toml`, re-lock `.github/ci/mise.lock` with
  `MISE_GLOBAL_CONFIG_FILE="$PWD/.github/ci/mise.toml" mise lock --global`, run
  `mise run tools:lock-check`, then `mise run tools:lock-verify` (slow; installs from
  `.github/ci/mise.lock` into an empty directory). Never run `mise upgrade`. Keep
  `lockfile_mode = "merge"` in `.github/ci/mise.toml`. Find the active binary path via
  `mise which <tool>` (or `.venv/bin/<tool>` for uv-managed tools).

- **Renovate warnings:** `mise run renovate:problems` lists the "Repository Problems" in each
  revision Renovate saved to the Dependency Dashboard (#12), with its time. It shows when a warning
  appeared and went away, not what raised it, and a run that left the dashboard unchanged saves no
  revision: before you name a cause or say a run was clean, quote that run's log on
  developer.mend.io, including the WARN line's `branch=`.

- **Changing hk.pkl:** `hk validate` and `hk check` never run a step's `fix` command. Run
  `mise run hk:fix-smoke`, which runs `hk fix --all` on a scratch worktree of HEAD.

- **Shipping:** The remote is `github.com/ray-manaloto/cpp-core`, a public repository. Every change
  is a pull request: a branch in its own worktree, one commit or more, opened with `repotools
  pr-create --title <title> --body-file <body file>`. Run `hk check --all` in the worktree on the head commit and report its result in the pull request. The agent that opened the pull request (for a Renovate update, the agent that checked it out) merges it itself, with no separate approval from the owner, once `hk check --all` passes on the head commit, the Codex reviewer has approved the pull request at that head, and the advisory CI run has been looked at. `mise run ship:merge N` checks the head, `hk check --all`, the reviewer's approval at the head and the noreply email, then merges and checks the merge commit's author; it does not look at the CI run, which stays a step you take yourself; `mise run ship:merge N --dry-run` checks only. By hand, merge with `gh pr merge N --merge --match-head-commit <head sha> --author-email "$(git config user.email)"`. This repository's local `user.email` is the merging account's `users.noreply.github.com` address; check it before the first commit or merge from a new clone. Without `--author-email`, GitHub credits the merge commit to the account's personal email, and this history is public: the merge commits of #1 to #4 carry it, and the owner chose to leave them as they are. Never push to `main`. The owner still decides deleting the repository, rewriting or force-pushing `main`, changing its visibility, and removing a protection.

- **Research:** The notes live in [Audit Bundle](./okf-bundles/audit/index.md). The open items are in
  [open-items.md](./okf-bundles/audit/open-items.md); the owner's decisions are in
  [decisions.md](./okf-bundles/audit/decisions.md); `PARKED.md` is the map of the whole effort.

- **Review approval:** One Codex review per pull request, of its whole diff and its title and body.
  The reviewer pane is opened in the worktree and pinned with `repotools pane-pin`, and it approves
  the output of `repotools pr-fingerprint`, which covers the title, the body and the head commit, so
  a new commit or an edited text needs a fresh approval. Commits carry no approval of their own. The owner's
  decision on each open item is still recorded in [decisions.md](./okf-bundles/audit/decisions.md)
  and [open-items.md](./okf-bundles/audit/open-items.md).

- **Content guard:** The privacy scan inside `mise run audit:verify` is the content guard. It
  checks the tracked files and the working tree for a machine name, a host name, a LAN or tailnet
  address, an account or organisation name, a real name and a private project name — and it
  **derives those values at run time**, from this machine's git identity, from this repository's
  own history and from the machine name. An untracked `.audit/privacy-patterns.txt` can add more.

### The Lane

**The build lane is parked.** As of 2026-11-12 the owner's decision is that this repository is
research-only:

- No builds, no compiler or toolchain installs or configuration, no CMake or preset runs, no test,
  sanitizer or coverage runs
- **Source files are out of scope** — the documentation is in scope
- Anything that would need a compile is written down as an open item instead of guessed at

`PARKED.md` records what is parked and what the plan is when the lane reopens. Do not "just try
it" with a compiler.

### The Rules

- **Both compilers keep working.** `gcc16` (GCC 16.2, libstdc++) and `p2996` (clang-p2996,
  libc++), both in C++26 mode. The preset matrix is in `cmake/presets/cpp-core.json`. A change
  that works on one and not the other is not done.

- **The module interface stays free of the C++ standard library.** A module's global module
  fragment is copied into every importing translation unit, and two copies of a standard header
  collide. (That is the observed failure mode, not the standard's rule — see `DEF-3` in
  [Audit Bundle → Open Items](./okf-bundles/audit/open-items.md#def-defects--8-items).)

- **`modules/logging/format.hpp` is private.** It is the module's own formatter; it is not in the
  public interface and it does not enter the module's purview.

- **The vcpkg manifest and the overlay ports are the dependency contract.** The manifest is
  `vcpkg.json`; the overlays are in `ports/`; the triplet is in `triplets/`.

- **The catalog IDs are wire identifiers.** They are the `ID` attributes a MIPI Sys-T consumer
  decodes against, so an ID that moves between releases is a wire format that changed. `DEF-6` is
  the defect; `BUILD-7` is the decision that fixes it.

- **Custom formatters are written for `fmt` only** — quill bundles its own copy of fmt
  (`fmtquill`), and the two copies are structural, not an accident.

- **The test framework's module variant is not used.** `import ut;` makes the `std` module
  reachable in the test translation unit and GCC 16 then collides with the standard headers the
  test file needs.

### Privacy

- **No private values in tracked files.** A machine name, host name, LAN address, tailnet name,
  account name, organisation name, real name or private project name is never written into a
  tracked file, a commit message, a pull request, an issue or a comment. A file that needs one
  becomes a template that reads the value at apply time, and the public text names only the role.

- **Forward-only.** Old branches, worktrees, commits, closed pull requests and old job logs are
  **not** scrubbed or backfilled. Nothing in the history is rewritten.

- **One rewrite, before the repository went public (2026-11-15).** The owner overrode the
  forward-only rule once: `git filter-repo` gave the early commits the noreply author identity and
  removed machine paths from old `.opencode/agents` files. Every commit hash changed, and the
  hashes the documents cite were remapped. The old history is kept only as a private bundle
  outside the repository. Forward-only holds again from here.

- **No key value is ever printed.** Report key-file paths only.

- **Values are injected with `mise run secret:set NAME`** — the value is piped in, never passed as
  an argument — and **never** with `fnox set`. `secret:set` is a task in the user's global mise
  config, not in this repository, which keeps secret handling out of the tracked files; a clone
  without that global config does not have it.

- **On this machine, `fnox get`, `exec`, `export`, `edit`, `tui`, `mcp`, `push` and `list --values`
  may not be run.** Use `fnox --non-interactive proxy run -- <command>`.

### Audit Conventions

The audit is a numbered set of parts, indexed in [Audit Bundle → README](./okf-bundles/audit/README.md) and `PARKED.md`.

- Every item carries an ID (`DEF-n`, `FMT-n`, `QUIL-n`, `TOOL-n`, `MOD-n`, `REFL-n`, `MAC-n`,
  `COV-n`, `BUILD-n`, `VCPKG-n`, `ENV-n`) and **an ID is never renumbered**. A retired item keeps
  its ID and moves to [open-items.md section 13](./okf-bundles/audit/open-items.md#items-that-carry-an-id-and-are-answered-or-contingent).

- Every item says what settles it. The wording in the Markdown is prose; the machine-readable
  classification is in `docs/cxx26-features-audit/audit-index.json`.

- **The JSON is derived, never authored.** `scripts/audit_index.py` parses `open-items.md` into
  it. Edit the Markdown and run `mise run audit:index`; never edit the JSON by hand.

- `scripts/audit_summary.py` answers a question about the audit without reading the Markdown:
  `mise run audit:summary -- --prefix MOD`, `--owner`, `--category compile`, `--state answered`,
  `--id MOD-11`, `--counts`.

- New research is a new part: a number, a file, a row in both parts tables, and a section in
  `PARKED.md` saying what it changed.

### The Scripts

All are stdlib-only Python, none invokes a compiler.

| Script | Purpose |
|--------|---------|
| `scripts/audit_index.py` | Parses `open-items.md` into registry (`--write`, `--check`) |
| `scripts/citations.py` | Finds citations the audit makes, and what file each names |
| `scripts/anchor_citations.py` | Hashes every source line the audit cites, checks it still says what it said (`--write`, `--check`) |
| `scripts/verify_audit.py` | Every check that does not need a compiler |
| `scripts/test_verify_audit.py` | Breaks the tree 14 ways, asserts checker catches each one |
| `scripts/audit_summary.py` | Registry sliced — answer without the reading |
| `scripts/audit_metrics.py` | What the automation is worth, measured rather than asserted |
| `scripts/measure.py` | Measures project: shape, discipline, API, audit coverage, dependency closure (`--write`, `--check`) |
| `scripts/verify_upstream.py` | Vendored upstream copies against `upstream/manifest.json` |
| `scripts/check_overlay_drift.py` | Overlay ports' pins against their upstreams' tips (`--network`) |
| `scripts/check_mise_lock.py` | `.github/ci/mise.lock` holds every pin in `.github/ci/mise.toml` (`--self-test`, `--install`) |
| `scripts/check_doc_commands.py` | Every `mise run <task>` in the docs and scripts names a real task (`--self-test`) |
| `scripts/ship_merge.py` | Merges a pull request only when the Shipping gates hold (`--dry-run`) |
| `scripts/renovate_problems.py` | Dependency Dashboard's Repository Problems, revision by revision (`--since`, `--issue`) |

**Run `mise run audit:test` before you trust the checker.** A check that never fails is not a
check; the test breaks the tree fourteen ways and asserts that each one is caught. If you add a
check, add a mutation for it.

**The measurement harness has a committed baseline.**
`docs/cxx26-features-audit/measurements.json` is derived from the tree by `scripts/measure.py`,
never hand-edited; `mise run audit:measure` regenerates it with `--write` and the checker fails
when it is stale. It is a ruler, not a verdict — it counts, and it does not judge.

**And there is a bar the ruler is held to.** `docs/cxx26-features-audit/acceptance.json` is the
acceptance bar: the constraints the project must not lose, the targets it is heading towards, and
the metrics that cannot be measured yet. It is **authored, not derived** — a standard, not a
snapshot — and the harness reads it and never edits it. Only the owner moves a threshold.
`mise run audit:acceptance` checks the tree against it, and the checker fails when it is
violated.

**A citation is a claim about a range of lines, and it is checked like one.**
`docs/cxx26-features-audit/citations.json` records every citation the audit makes and a hash of
every source line those citations name. It is derived, never hand-edited; `mise run audit:anchor`
regenerates it with `--write`, and the checker fails when a cited line no longer says what it
said, when a citation names a line the file no longer has, or when a citation has moved without
the baseline being regenerated.

**The audit has read every line of the library.** Part 20 closed the read gap: the harness's
`audit.read_coverage_share` is **1.0**, and the bar's floor was ratcheted to 1.0 to match. A new
file, or a new line in an existing one, drops the share — and the checker fails until the reading
catches up.

### Agent Skills

- `implement` — build one ticket from an existing plan, staged, not committed.
- `implement-spec` — build every open ticket of a spec, one worker per ticket.
- `work` — set the repository up, then name the next ready ticket.
- `visual-plan` — publish a plan as a commentable page.
- `ticket-retro` — the retrospective when a ticket or spec is finished.

### Full Documentation

All documentation has been migrated to OKF bundles. See the bundles for complete documentation:

| Bundle | Path | Description |
|--------|------|-------------|
| Architecture | `./okf-bundles/architecture/` | 7 visual documents (components, wire protocol, sequences, dependencies, open issues, decisions) |
| Audit | `./okf-bundles/audit/` | 21-part C++26 features audit (70 open items, 19 decisions, verification system) |
| ASAN Leak Check | `./docs/asan-leak-check/README.md` | ASAN leak-check analysis |
| Module Source Location | `./docs/module-source-location/README.md` | Module source location research |

### Quick Reference

| Task | Command |
|------|---------|
| Run all checks | `mise run hk:check` |
| Format all files | `mise run hk:fix` |
| Run audit verification | `mise run audit:verify` |
| Run all CI checks | `mise run ci` |
| Install hooks | `mise run hooks:install` |
| Validate hk config | `mise run hk:validate` |
| Run pre-commit | `mise run pre-commit` |
| Validate commit msg | `mise run commit-msg` |
| List stale tool pins | `mise run tools:outdated` |
| Check the lockfile | `mise run tools:lock-check` |
| Smoke-test hk fix commands | `mise run hk:fix-smoke` |

### Key Files

| File | Purpose |
|------|---------|
| `hk.pkl` | hk configuration: shared steps for check, fix, pre-commit and pre-push, plus commit-msg |
| `.mise.toml` | tool-free task runner config, `[deps.uv]`, doctor checks, and task includes |
| `pyproject.toml` | pinned Python-packaged C++/CMake lint/format tools (`clang-format`, `cpplint`, `gersemi`) |
| `uv.lock` | locked wheels for `pyproject.toml` `[dependency-groups].dev` |
| `.github/ci/mise.toml` | advisory CI tool pins loaded via `MISE_GLOBAL_CONFIG_FILE` |
| `.github/ci/mise.lock` | locked CI tool versions, URLs and checksums for `linux-arm64`, `linux-x64` and `macos-arm64` |
| `.clang-format` | clang-format configuration |
| `.rumdl.toml` | rumdl configuration (MD013, MD041, MD052, MD033 disabled) |
| `.cpplint` | cpplint configuration (line length 120, disable specific checks) |
| `vcpkg.json` | vcpkg manifest (dependencies, overlays) |
| `PARKED.md` | Work status map (pointer to bundles) |
| `AGENTS.md` | This file |
| `README.md` | Project overview (pointer to bundles) |
