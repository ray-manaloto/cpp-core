---
okf_version: "0.2"
title: lychee vs lychee-extended — Builtin Comparison
description: Comparison of hk builtins for link checking - lychee (basic) vs lychee-extended (Flint-enhanced)
version: 2.12.0
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - hk
  - builtin
  - lychee
  - lychee-extended
  - link-checker
  - comparison
  - flint
  - offline-docs
sources:
  - id: hk-builtins-source
    resource: https://hk.jdx.dev/builtins.html#lychee
    title: hk Builtins Catalogue - lychee
    author: jdx
    last_modified: 2026-11-09T14:26:00Z
  - id: hk-builtins-extended-source
    resource: https://hk.jdx.dev/builtins.html#lychee-extended
    title: hk Builtins Catalogue - lychee-extended
    author: jdx
    last_modified: 2026-11-09T14:26:00Z
  - id: flint-lychee-docs
    resource: https://github.com/grafana/flint/blob/main/docs/linters/lychee.md
    title: Flint lychee linter documentation
    author: grafana
  - id: lychee-source
    resource: https://github.com/lycheeverse/lychee
    title: lychee GitHub Repository
    author: lycheeverse
  - id: flint-source
    resource: https://github.com/grafana/flint
    title: Grafana Flint Repository
    author: grafana
---

## lychee vs lychee-extended — Builtin Comparison

Comparison of the two hk builtins for link checking to help decide which to use in cpp-core.

### Quick Comparison

| Aspect | lychee | lychee-extended |
|--------|--------|-----------------|
| **Pkl Property** | `Builtins.lychee` | `Builtins.lychee_extended` |
| **Core Tool** | lychee (standalone) | flint + lychee |
| **Repository Awareness** | ❌ No | ✅ Yes (via Flint) |
| **Internal Link Checking** | Basic (file existence) | Enhanced (repo context) |
| **External Link Checking** | ✅ Yes | ✅ Yes |
| **Installation** | `mise use lychee` | `mise use packslip:grafana/flint lychee` |
| **Check Command** | `lychee --no-progress {{files}}` | `flint checker lychee --files-from -` |
| **Input Method** | File arguments | Stdin (`--files-from -`) |
| **Maintenance** | Active (lycheeverse/lychee) | Active (grafana/flint) |
| **hk Integration** | Native builtin | Native builtin |

### Feature Breakdown

#### lychee (Builtins.lychee)

**What it provides:**

- Fast, async, stream-based link checking
- Checks both external (HTTP/HTTPS) and internal (relative file) links
- Supports markdown, HTML, and text files
- Configurable via CLI flags and config file
- Can exclude patterns, set timeouts, limit concurrency
- Outputs: summary, verbose, JSON, GitHub Actions annotations

**Key features:**

- `--no-progress` - Clean CI output (used by hk builtin)
- `--max-concurrency N` - Control parallelism
- `--timeout SECONDS` - Request timeout
- `--exclude PATTERN` - Skip URLs matching pattern
- `--include PATTERN` - Only check URLs matching pattern
- `--base URL` - Base URL for relative links
- `--accept CODES` - Accept additional HTTP codes (e.g., 429, 999)
- `--config FILE` - Config file support (TOML/YAML/JSON)
- `--fail` - Exit with non-zero on failures

**Config file example** (`lychee.toml`):

```toml
# Global settings
max_concurrency = 10
timeout = "30s"
verbose = false

# URL exclusions
exclude = [
  ".*localhost.*",
  ".*127\\.0\\.0\\.1.*",
  ".*example\\.com.*"
]

# Accept additional codes (rate limits, etc.)
accept = [429, 999]

# Per-file settings
[[files]]
path = "README.md"
base = "https://github.com/ray-manaloto/cpp-core"
```

#### lychee-extended (Builtins.lychee_extended)

**What it provides (via Flint):**

- All lychee features PLUS:
- **Repository awareness**: Knows which files exist in your repo
- **Smart internal link resolution**: Validates relative links against actual repo structure
- **Context-aware checking**: Understands repo root, handles symlinks, submodules
- **Enhanced error reporting**: Shows repo-relative paths, suggests fixes
- **Flint integration**: Part of Grafana's linter ecosystem

**How it works:**

1. Flint receives file list via stdin (`--files-from -`)
2. Flint builds repository context (file tree, symlinks, git submodules)
3. Flint invokes lychee with enhanced context
4. Results include repo-aware diagnostics

**Flint lychee docs**: <https://github.com/grafana/flint/blob/main/docs/linters/lychee.md>

### Pros/Cons Analysis

#### lychee

| Pros | Cons |
|------|------|
| ✅ Simpler - single tool dependency | ❌ No repository context |
| ✅ Faster startup (no Flint overhead) | ❌ Basic internal link checking (file existence only) |
| ✅ Mature, widely used | ❌ Doesn't understand git submodules |
| ✅ Direct lychee config file support | ❌ Can't resolve `../docs/file.md` from subdirs intelligently |
| ✅ Works offline for local file checks | ❌ No repo-relative path reporting |
| ✅ Actively maintained (lycheeverse) | ❌ No integration with other Flint linters |
| ✅ Zero-config works out of box | |

#### lychee-extended

| Pros | Cons |
|------|------|
| ✅ Repository-aware internal link validation | ❌ More complex - requires Flint + lychee |
| ✅ Understands repo structure, submodules, symlinks | ❌ Slower startup (Flint initialization) |
| ✅ Better error messages with repo context | ❌ Additional dependency (Flint) |
| ✅ Part of Grafana Flint ecosystem | ❌ Config via Flint, not direct lychee config |
| ✅ Can integrate with other Flint checkers | ❌ Less documentation than standalone lychee |
| ✅ Smart resolution of relative paths | ❌ Flint is newer, smaller community |
| ✅ Actively maintained by Grafana | |

### What Each Provides That the Other Doesn't

#### lychee provides (lychee-extended lacks)

- Direct lychee config file (`lychee.toml`, `.lychee.toml`, `lychee.yml`)
- Simpler installation (single binary)
- Direct access to all lychee CLI flags
- Faster execution for simple use cases
- Offline local file checking without repo context

#### lychee-extended provides (lychee lacks)

- Repository-aware internal link checking
- Git submodule awareness
- Symlink resolution in link targets
- Repo-relative path reporting in errors
- Integration with Flint's multi-linter pipeline
- Context-aware base URL resolution

### Modern Best Practices Assessment

#### Active Maintenance (as of 2026-11)

| Project | Stars | Last Release | Commit Frequency | Status |
|---------|-------|--------------|------------------|--------|
| **lychee** (lycheeverse/lychee) | ~5k+ | Active | High | ✅ Mature |
| **Flint** (grafana/flint) | ~1k+ | Active | High | ✅ Active |

Both are actively maintained. lychee is more mature; Flint is newer but backed by Grafana.

#### hk Integration Quality

Both are **native hk builtins** with equal integration quality:

- Defined in hk's `Builtins.pkl`
- Same configuration pattern (`["name"] = Builtins.name`)
- Same hook support (check, pre-commit, etc.)
- Both support `depends`, `profiles`, `glob`, `exclude`

#### mise Integration

| Tool | mise Package | Notes |
|------|--------------|-------|
| lychee | `mise use lychee` | Simple, direct |
| Flint | `mise use packslip:grafana/flint` | Via packslip (Flint not in mise directly) |
| lychee (for extended) | `mise use lychee` | Still needed as dependency |

**mise integration is slightly simpler for lychee** (single package vs packslip + lychee).

### Recommendation for cpp-core

#### Use **lychee** (Builtins.lychee)

**Rationale:**

1. **Simpler is better** - cpp-core has a flat documentation structure (README.md, PARKED.md, AGENTS.md, OKF bundles). No complex submodule/symlink scenarios.

2. **No repository awareness needed** - Our internal links are simple relative paths (`./okf-bundles/architecture/index.md`, `../docs/...`). Basic file existence check is sufficient.

3. **Faster CI** - lychee starts faster, no Flint overhead. Important for pre-commit hooks.

4. **Direct config** - Can use `lychee.toml` for fine-tuning (exclude localhost, accept 429, etc.) without Flint indirection.

5. **Mature tool** - lychee is battle-tested, larger community, more examples/docs.

6. **Sufficient for our use case** - We need:
   - ✅ External link validation (GitHub, docs, crates.io, etc.)
   - ✅ Internal link validation (OKF bundle cross-refs)
   - ✅ CI integration (pre-commit, CI pipeline)
   - ❌ Don't need: submodule awareness, symlink resolution, multi-repo context

#### When to Consider lychee-extended Later

Switch to lychee-extended if:

- Project adds git submodules with cross-references
- Documentation moves to a complex multi-directory structure with many relative links
- Team adopts Flint for other linters (actionlint, hadolint, etc.) and wants unified pipeline
- Internal link false positives become a maintenance burden

### Configuration for cpp-core

#### Recommended: lychee with config file

**hk.pkl:**

```pkl
["lychee"] = (Builtins.lychee) {
  glob = List("**/*.md", "**/*.markdown")
  exclude = List("**/node_modules/**", "**/.git/**", "**/build/**", "**/upstream/**")
}
```

**lychee.toml** (project root):

```toml
# lychee config for cpp-core
max_concurrency = 10
timeout = "30s"
verbose = false

# Exclude known problematic patterns
exclude = [
  ".*localhost.*",
  ".*127\\.0\\.0\\.1.*",
  ".*example\\.com.*",
  # Allow rate limits and network errors in CI
]
accept = [429, 999]

# Base URL for relative links in README
[[files]]
path = "README.md"
base = "https://github.com/ray-manaloto/cpp-core"

[[files]]
path = "PARKED.md"
base = "https://github.com/ray-manaloto/cpp-core"

[[files]]
path = "AGENTS.md"
base = "https://github.com/ray-manaloto/cpp-core"
```

**CI Integration:**

```yaml
# .github/workflows/links.yml
- name: Check links
  run: hk check --step lychee --all
  env:
    HK_MISE: "1"
```

### Related Documents

- [lychee](./lychee.md) - Full lychee documentation
- [lychee-extended](./lychee-extended.md) - Full lychee-extended documentation
- [Bundle Index](./index.md) - hk-builtins bundle overview
- [Master Registry](../registry/index.md) - All OKF bundles
- [Project Meta](../project-meta/index.md) - Tool versions and config reference
