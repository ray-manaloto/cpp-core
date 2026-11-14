---
okf_version: "0.2"
title: lychee — Fast, Async, Stream-Based Link Checker
description: hk builtin for lychee link checker - validates URLs in markdown and text files
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
  - link-checker
  - offline-docs
sources:
  - id: hk-builtins-source
    resource: https://hk.jdx.dev/builtins.html#lychee
    title: hk Builtins Catalogue - lychee
    author: jdx
    last_modified: 2026-11-09T14:26:00Z
  - id: lychee-source
    resource: https://github.com/lycheeverse/lychee
    title: lychee GitHub Repository
    author: lycheeverse
---

## lychee — Fast, Async, Stream-Based Link Checker

**Pkl Property**: `Builtins.lychee`

**Category**: Special Purpose

### Description

Fast, async, stream-based link checker for validating URLs in markdown and text files.

### Installation

```sh
mise use lychee
```

Or install via your preferred package manager:

- Homebrew: `brew install lychee`
- Cargo: `cargo install lychee`
- Download binary from [GitHub releases](https://github.com/lycheeverse/lychee/releases)

### Configuration

#### Files Matched

- `text files` (all text files)

#### Check Command

```sh
lychee --no-progress {{files}}
```

#### Fix Command

None (lychee is a checker only)

### Usage

#### Basic Usage

```pkl
# In hk.pkl
["lychee"] = Builtins.lychee
```

```sh
# Run on all files
hk check --step lychee --all

# Run on specific files
hk check --step lychee -- README.md docs/**/*.md
```

#### Customization

```pkl
# Customize file patterns
["lychee"] = (Builtins.lychee) {
  glob = List("**/*.md", "**/*.markdown", "**/*.txt")
  exclude = List("**/node_modules/**", "**/.git/**")
}

# Add dependencies for ordering
["lychee"] = (Builtins.lychee) {
  depends = "markdown-lint"
}

# Use with mise environment (HK_MISE=1)
# Tools from mise.toml are automatically available
```

### Common Options

| Option | Description |
|--------|-------------|
| `--no-progress` | Disable progress bar (used by default in hk) |
| `--max-concurrency N` | Limit concurrent requests |
| `--timeout SECONDS` | Request timeout |
| `--exclude PATTERN` | Exclude URLs matching pattern |
| `--include PATTERN` | Only check URLs matching pattern |
| `--base URL` | Base URL for relative links |
| `--accept CODES` | Accept additional HTTP status codes (e.g., 429,999) |

### Example: Checking Only Markdown Files

```pkl
["lychee"] = (Builtins.lychee) {
  glob = List("**/*.md", "**/*.markdown")
}
```

### Example: Excluding External Links

```pkl
["lychee"] = (Builtins.lychee) {
  # Note: lychee's --exclude works on URL patterns, not file patterns
  # File exclusion is handled by hk's glob/exclude
}
```

### CI Integration

```yaml
# GitHub Actions
- name: Check links
  run: hk check --step lychee --all
  env:
    HK_MISE: "1"
```

### Related

- [lychee-extended](./lychee-extended.md) - Repository-aware link checking with Flint
- [hk builtins catalogue](https://hk.jdx.dev/builtins.html#lychee)
- [lychee documentation](https://github.com/lycheeverse/lychee)
