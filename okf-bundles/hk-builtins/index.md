---
okf_version: "0.2"
title: hk Builtins Offline Documentation
description: Offline documentation for hk built-in linters and utilities, focusing on lychee and lychee-extended link checkers
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
  - builtins
  - lychee
  - link-checker
  - offline-docs
sources:
  - id: hk-builtins-source
    resource: https://hk.jdx.dev/builtins.html
    title: hk Builtins Catalogue (v2.12.0)
    author: jdx
    last_modified: 2026-11-09T14:26:00Z
---

## hk Builtins Offline Documentation

Offline mirror of the [hk builtins catalogue](https://hk.jdx.dev/builtins.html) for the hk v2.12.0 release.

### Contents

- [lychee](./lychee.md) - Fast, async, stream-based link checker
- [lychee-extended](./lychee-extended.md) - Flint's repository-aware link check (requires flint and lychee)

### Overview

Builtins are reusable Pkl step definitions for linters, formatters, and hk's own utilities. They supply file patterns, check and fix commands, and optimizations such as diff output.

**Important**: Builtins configure how hk invokes a tool; they do not install that tool. The executable used by the builtin must be on PATH, or the step must use a prefix that resolves it.

With `HK_MISE=1`, hk resolves the mise environment for the step's directory, so tools declared in a subproject's `mise.toml` are available without a prefix.

### Quick Reference

| Builtin | Pkl Property | Install Command | Description |
|---------|--------------|-----------------|-------------|
| lychee | `Builtins.lychee` | `mise use lychee` | Fast, async, stream-based link checker |
| lychee-extended | `Builtins.lychee_extended` | `mise use packslip:grafana/flint lychee` | Flint's repository-aware link check |

### Usage

```pkl
amends "package://github.com/jdx/hk/releases/download/v2.12.0/hk@2.12.0#/Config.pkl"
import "package://github.com/jdx/hk/releases/download/v2.12.0/hk@2.12.0#/Builtins.pkl"

hooks {
  ["check"] {
    steps {
      ["lychee"] = Builtins.lychee
      ["lychee-extended"] = Builtins.lychee_extended
    }
  }
}
```

Then run:

```sh
hk check --step lychee --all
hk check --step lychee-extended --all
```
