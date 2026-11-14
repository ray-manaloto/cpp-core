---
okf_version: "0.2"
title: ASAN Leak Check Analysis
description: Analysis of ASAN leak check hangs on macOS with GCC 16 and clang-p2996, with suppression strategy
version: 1.0.0
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - asan
  - leak-check
  - macos
  - gcc
  - clang
  - sanitizer
  - cpp-core
sources:
  - id: source-document
    resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/asan-leak-check/README.md
    title: Original ASAN Leak Check Documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
  - id: upstream-sources
    resource: ./upstream/
    title: Vendored upstream sanitizer sources (GCC 16, LLVM main, quill 13.1.0)
---

## ASAN Leak Check Analysis

Analysis of why ASAN leak checking hangs on macOS with GCC 16 and reports false positives with clang-p2996, and the implemented suppression strategy.

### Quick Summary

| Compiler | Leak Check Status | Solution |
|----------|-------------------|----------|
| **GCC 16.2.0** | **Hangs at exit** (deadlock in libasan's `StopTheWorld`) | Keep `detect_leaks=0`, document reason |
| **clang-p2996 (clang 21)** | **Works but reports 316 B platform leaks** | Enable with `cmake/lsan.supp` suppressions |
| **Homebrew clang 23.1.5** | **Clean, no false positives** | Planned `clang23-asan` preset (needs `<meta>` in SDK) |

### Key Findings

#### Problem 1: GCC 16 Deadlock

- GCC 16's `libasan.8.dylib` deadlocks in `StopTheWorld` at exit
- Main thread waits on `pthread_join` for helper thread
- Helper thread blocks on ASan's own allocator semaphore (`Semaphore::Wait`)
- Triggered by dyld notification path (`class_createInstance` from libobjc)
- **No workaround works** - tested 7 approaches including fork, pre-warm, early check
- **Upstream code is identical** in GCC 16, GCC master, and LLVM main - no fix pending

#### Problem 2: clang-p2996 Platform Leaks

316 bytes in 7 allocations, all macOS artifacts:

- 72 B: `libobjc` - `_fetchInitializingClassList` (ObjC runtime init)
- 48 B: `libdyld` - `ThreadLocalVariables::instantiateVariable` (dyld TLS)
- 80 B + children: Apple libc `snprintf("%g")` float formatting buffer
- **None are from our code** - verified with micro-tests

#### Problem 3: clang 23 Works But Can't Build Project

- Clean leak check, no suppressions needed
- **Blocker**: No macOS SDK has `<meta>` header for C++26 static reflection
- Requires: new vcpkg triplet, preset, CMake option to exclude `reflection_demo.cpp`

### Implemented Solution (Option E)

**Current**: B now, C as follow-up

| File | Change |
|------|--------|
| `cmake/lsan.supp` | New: 5 suppression entries with reasons |
| `cmake/presets/cpp-core.json` | `p2996-asan`: `detect_leaks=1` + `LSAN_OPTIONS=suppressions=...`; `gcc16-asan`: `detect_leaks=0` with comment |
| `README.md` | "Leak checking" section documenting suppressions and GCC deadlock |

### Verification

```sh
# p2996-asan preset passes with leak check ON
cmake --workflow --preset p2996-asan
# 1/1 Test #1: cpp-core-tests ... Passed

# Same binary WITHOUT suppressions: 316 B leaked in 7 allocations
ASAN_OPTIONS=detect_leaks=1 build/p2996-asan/tests/cpp-core-tests

# gcc16-asan preset passes (leak check OFF by necessity)
cmake --workflow --preset gcc16-asan
# 1/1 Test #1: cpp-core-tests ... Passed
```

### Reproduction

```sh
# GCC deadlock (2-line program)
g++-16 -std=c++26 -g -O0 -fsanitize=address repro/hello.cpp -o /tmp/hello.gcc16
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 timeout 15 /tmp/hello.gcc16  # hangs

# clang-p2996 false positives
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 build/p2996-asan/tests/cpp-core-tests
# -> 316 byte(s) leaked in 7 allocation(s)

# With suppressions
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 \
  LSAN_OPTIONS=suppressions=docs/asan-leak-check/evidence/lsan.supp \
  build/p2996-asan/tests/cpp-core-tests
# -> PASSED, asserts: 11 (11 passed), no leaks
```

### Directory Structure

```text
docs/asan-leak-check/
├── README.md                      # This document (full analysis)
├── evidence/                      # Measured outputs
│   ├── gcc16-hello-deadlock-callgraph.txt
│   ├── p2996-leak-report.log
│   ├── p2996-leak-report-with-suppressions.log
│   ├── p2996-real-leak-with-suppressions.log
│   └── lsan.supp                  # Copy of cmake/lsan.supp
├── repro/                         # Minimal reproduction cases
│   ├── hello.cpp, alloc.cpp, real_leak.cpp
│   ├── snprintf_test.cpp, snprintf_int.cpp
│   ├── tlv_trivial.cpp, tlv_nontrivial.cpp
│   ├── quill_b.cpp, quill_c.cpp
│   ├── prewarm_dyld.cpp, early_lsan.cpp
│   ├── fork_lsan.cpp, fork_lsan2.cpp
│   └── sample_hang.sh
└── upstream/                      # Vendored upstream sources
    ├── gcc16-sanitizer_stoptheworld_mac.cpp
    ├── llvm-main-sanitizer_stoptheworld_mac.cpp
    ├── gcc16-lsan_*.cpp, llvm-main-lsan_*.cpp
    └── quill/                     # quill 13.1.0 headers
```

### Related

- [Architecture Bundle → Dependency Graph](../architecture/04-dependency-graph.md)
- [Project Root PARKED.md](../../PARKED.md) - Build lane status
- [CMake Presets](../../cmake/presets/cpp-core.json)
