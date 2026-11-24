---
okf_version: "0.2"
title: Project Metadata and Configuration
description: cpp-core project metadata, tool versions, and configuration reference
version: 1.0.0
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - cpp-core
  - metadata
  - configuration
  - tools
  - versions
sources:
  - id: mise-config
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/.mise.toml
    title: mise task configuration
  - id: hk-config
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/hk.pkl
    title: hk git hooks configuration
  - id: clang-format
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/.clang-format
    title: clang-format configuration
  - id: rumdl-config
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/.rumdl.toml
    title: rumdl markdown linter configuration
  - id: cpplint-config
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/.cpplint
    title: cpplint configuration
  - id: vcpkg-manifest
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/vcpkg.json
    title: vcpkg manifest
---

## Project Metadata and Configuration

Reference for cpp-core project metadata, tool versions, and configuration files.

### Tooling Scope (`dotfiles-v2`, `uv.lock`, `.github/ci/mise.toml`)

Per the **2026-11-24 owner ruling** (overturning 2026-11-15), `.mise.toml` declares zero `[tools]` and commits no root `mise.lock`:

- **Developer workstation tools (`dotfiles-v2`):** `hk` (`2.14.0`), `betterleaks`, `jactionlint`, `lychee`, `node`, `pkl`, `ruff`, `rumdl`, `shellcheck`, `shfmt`, `tombi`, `ty`, `typos`, `uv`, `zizmor` come from global `~/.config/mise/config.toml`.
- **Python-packaged C++/CMake tools (`pyproject.toml` + `uv.lock`):** `clang-format==23.1.5`, `cpplint==2.0.2`, and `gersemi==0.29.2` install via `mise deps uv` (`uv sync --locked`) into `.venv/` and run via `uv run --locked`.
- **Advisory CI tools (`.github/ci/mise.toml` + `.github/ci/mise.lock`):** `.github/workflows/ci.yml` sets `MISE_GLOBAL_CONFIG_FILE=${{ github.workspace }}/.github/ci/mise.toml` and installs locked CI pins including `kingfisher`, `osv-scanner`, `prettier`, and `npm:renovate`.

### Configuration Files

| File | Purpose |
|------|---------|
| `.mise.toml` | Tool-free task runner config, `[deps.uv]`, doctor checks, and task includes |
| `pyproject.toml` | Pinned `clang-format`, `cpplint`, and `gersemi` dev dependency group |
| `uv.lock` | Locked Python wheels for `.venv/` lint tools |
| `.github/ci/mise.toml` | Advisory CI tool pins (`MISE_GLOBAL_CONFIG_FILE`) |
| `.github/ci/mise.lock` | Locked advisory CI tool checksums (`linux-arm64`, `linux-x64`, `macos-arm64`) |
| `mise/audit/tasks.toml` | Audit verification tasks (13) |
| `mise/hk/tasks.toml` | hk-based checks and utilities (14) |
| `mise/ci/tasks.toml` | CI pipeline (parallelized, 4) |
| `mise/lint/tasks.toml` | Language-specific linting via hk (6) |
| `mise/format/tasks.toml` | Language-specific formatting via hk (9) |
| `mise/doctor/tasks.toml` | mise/hk doctor diagnostics (6) |
| `mise/setup/tasks.toml` | Tool installation, hooks, validation (6) |
| `mise/render/tasks.toml` | Render tasks (placeholder) |
| `hk.pkl` | hk git hooks config (`hk@2.14.0`, check, fix, pre-commit, pre-push, commit-msg) |
| `.clang-format` | clang-format config (LLVM style, 120 cols) |
| `.rumdl.toml` | rumdl config (MD013, MD041, MD052, MD033 disabled) |
| `.cpplint` | cpplint config (line length 120, specific disables) |
| `vcpkg.json` | vcpkg manifest (dependencies, overlays) |
| `cmake/presets/cpp-core.json` | CMake presets (GCC 16, clang-p2996) |
| `.editorconfig` | Editor config (matches clang-format) |
| `lychee.toml` | lychee link checker config (exclusions, timeouts) |

### HK Configuration Summary

**Hooks**: check, fix, pre-commit, pre-push, commit-msg

**Steps**:

- Formatters: `clang-format`, `gersemi`, `shfmt`, `ruff-format`, `tombi-format`, `rumdl-format`, `prettier`, `mise-fmt`, `pkl-format`
- Linters: `clang-format` (check), `cpp-lint`, `cpp-lint-modules`, `gersemi` (check), `ruff`, `rumdl`, `tombi`, `renovate-config`, `jactionlint`, `zizmor`, `hadolint`, `shellcheck`, `ty`, `typos`, `python-check-ast`, `python-debug-statements`, `betterleaks`, `kingfisher`, `osv-scanner`, **lychee** (`flaky` profile)
- Utilities & Audit: `check-merge-conflict`, `check-added-large-files`, `check-symlinks`, `trailing-whitespace`, `newlines`, `mixed-line-ending`, `fix-smart-quotes`, `byte-order-marker`, `check-case-conflict`, `check-executables-have-shebangs`, `check-shebang-scripts-are-executable`, `destroyed-symlinks`, `detect-private-key`, `forbid-submodules`, `hk-validate`, `audit-verify`, `docs-commands`, `mise-lock`, `check-clean-workspace`
- Commit: `check-conventional-commit` (`commit-msg` hook)

**Parallel Execution**: `mise run hk_check ::: verify ::: doctor` (142% CPU)

### CMake Presets

| Compiler | debug | release | asan | tsan | iwyu |
|----------|-------|---------|------|------|------|
| GCC 16.2 | `gcc16-debug` | `gcc16-release` | `gcc16-asan` | — | — |
| clang-p2996 | `p2996-debug` | `p2996-release` | `p2996-asan` | `p2996-tsan` | `p2996-iwyu` |

### vcpkg Dependencies

**Manifest**: `vcpkg.json`
**Overlay ports**: `ports/`
**Triplet**: `triplets/arm64-osx-p2996-asan.cmake` (and gcc16 variants)

Key dependencies:

- quill (logging backend)
- fmt (formatting)
- intel-cib (compile-time logging)
- ut (test framework)
- stdx (constexpr utilities)

### Repository Rules (from AGENTS.md)

- **Both compilers must work**: GCC 16 (libstdc++) + clang-p2996 (libc++)
- **Module interface free of stdlib**: Global module fragment collides with importer's std headers
- **`format.hpp` is private**: Not in public interface
- **vcpkg manifest + overlays = dependency contract**
- **Catalog IDs are wire identifiers**: ID movement = wire format change
- **Custom formatters for `fmt` only**: quill bundles `fmtquill` (structural)
- **Test framework module variant not used**: `import ut;` collides with std headers on GCC 16

### Privacy Rules

- No private values in tracked files (machine name, host, LAN/tailnet address, account, org, real name, private project)
- Forward-only: history not rewritten
- Keys injected via `mise run secret:set NAME` (piped, never args); `secret:set` is a global mise task, not one of this repository's
- `fnox get/exec/export/edit/tui/mcp/push/list --values` forbidden on this machine

### Audit Conventions

- Item IDs never renumbered (`DEF-n`, `FMT-n`, `QUIL-n`, `TOOL-n`, `MOD-n`, `REFL-n`, `MAC-n`, `COV-n`, `BUILD-n`, `VCPKG-n`, `ENV-n`)
- JSON derived from Markdown (`scripts/audit_index.py`)
- Citation anchoring (`scripts/anchor_citations.py`)
- Full read coverage: `audit.read_coverage_share = 1.0`

### Related

- [Architecture Bundle](../architecture/index.md)
- [Audit Bundle](../audit/index.md)
- [hk-builtins Bundle](../hk-builtins/index.md)
- [Project Root AGENTS.md](../../AGENTS.md)
- [Project Root PARKED.md](../../PARKED.md)
