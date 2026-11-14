---
okf_version: "0.2"
title: lychee-extended — Flint's Repository-Aware Link Check
description: hk builtin for lychee-extended - repository-aware link checking using Grafana Flint and lychee
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
  - lychee-extended
  - flint
  - link-checker
  - grafana
  - offline-docs
sources:
  - id: hk-builtins-source
    resource: https://hk.jdx.dev/builtins.html#lychee-extended
    title: hk Builtins Catalogue - lychee-extended
    author: jdx
    last_modified: 2026-11-09T14:26:00Z
  - id: flint-lychee-docs
    resource: https://github.com/grafana/flint/blob/main/docs/linters/lychee.md
    title: Flint lychee linter documentation
    author: grafana
  - id: flint-source
    resource: https://github.com/grafana/flint
    title: Grafana Flint Repository
    author: grafana
---

## lychee-extended — Flint's Repository-Aware Link Check

**Pkl Property**: `Builtins.lychee_extended`

**Category**: Special Purpose

### Description

Flint's repository-aware link check that uses lychee under the hood. Provides enhanced link checking with repository context awareness (e.g., checking links to files that exist in the repo vs external links).

See [Flint lychee linter documentation](https://github.com/grafana/flint/blob/main/docs/linters/lychee.md) for details.

### Installation

```sh
mise use packslip:grafana/flint lychee
```

This installs both:

- `flint` - Grafana's repository-aware linter runner
- `lychee` - The underlying link checker

Alternative installation:

```sh
# Install flint
mise use packslip:grafana/flint

# Install lychee separately
mise use lychee
```

### Configuration

#### Files Matched

- `text files` (all text files)

#### Check Command

```sh
flint checker lychee --files-from -
```

#### Fix Command

None (lychee-extended is a checker only)

### Usage

#### Basic Usage

```pkl
# In hk.pkl
["lychee-extended"] = Builtins.lychee_extended
```

```sh
# Run on all files
hk check --step lychee-extended --all

# Run on specific files
hk check --step lychee-extended -- README.md docs/**/*.md
```

#### Customization

```pkl
# Customize file patterns
["lychee-extended"] = (Builtins.lychee_extended) {
  glob = List("**/*.md", "**/*.markdown", "**/*.txt")
  exclude = List("**/node_modules/**", "**/.git/**")
}

# Add dependencies for ordering
["lychee-extended"] = (Builtins.lychee_extended) {
  depends = "lychee"
}

# Use with mise environment (HK_MISE=1)
```

### How It Works

Unlike basic `lychee` which checks all links independently, `lychee-extended` via Flint:

1. **Repository awareness**: Knows which files exist in your repository
2. **Internal link validation**: Validates relative links to other files in the repo
3. **Context-aware checking**: Understands repo structure for better error reporting
4. **Piped input**: Uses `--files-from -` to receive file list from stdin

### Differences from lychee

| Feature | lychee | lychee-extended |
|---------|--------|-----------------|
| External link checking | ✅ | ✅ |
| Internal link checking | Basic | Repository-aware |
| Repository context | ❌ | ✅ (via Flint) |
| Requires Flint | ❌ | ✅ |
| Input method | File arguments | Stdin (files-from -) |

### CI Integration

```yaml
# GitHub Actions
- name: Check links (extended)
  run: hk check --step lychee-extended --all
  env:
    HK_MISE: "1"
```

### Related

- [lychee](./lychee.md) - Basic fast link checker
- [Flint lychee documentation](https://github.com/grafana/flint/blob/main/docs/linters/lychee.md)
- [Grafana Flint repository](https://github.com/grafana/flint)
- [hk builtins catalogue](https://hk.jdx.dev/builtins.html#lychee-extended)
