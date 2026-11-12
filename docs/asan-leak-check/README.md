# The ASan leak check hangs at exit - review

**Status:** decision taken (option E). The leak check is now enabled for `p2996-asan` with
`cmake/lsan.supp`; `gcc16-asan` keeps `detect_leaks=0` with the reason recorded in the preset and
in the README. The `clang23-asan` preset (option C) is a planned follow-up - see
[Follow-up](#7-follow-up).
**Scope:** item 1 of the two flagged items. Item 2 (the module path reports no source location) is
untouched.

**Question:** the `gcc16-asan` and `p2996-asan` test presets set
`ASAN_OPTIONS=detect_leaks=0:abort_on_error=1`. Why, and what should we do instead?

**Short answer:** the leak check is disabled because it is broken in two different ways, neither of
which is our code:

1. **GCC 16.2.0 deadlocks** at exit inside its own `libasan` (10 runs out of 10, even for a
   hello-world).
2. **clang-p2996 (clang 21) does not deadlock**, but it reports leaks that macOS itself causes
   (libobjc, dyld thread-local variables, Apple's `snprintf` float formatting) - 316 bytes in 7
   allocations for our test binary, none of them ours.

Homebrew **clang 23.1.5** has a working leak check with no false positives, but it cannot build this
project today (no `<meta>` in any installed macOS SDK). The options are in
[What we can do](#5-what-we-can-do).

Everything below is reproducible from this directory; see [Reproducing](#8-reproducing).

---

## 1. The reproduction matrix

All runs use `ASAN_OPTIONS=detect_leaks=1:abort_on_error=1` and a 15 s timeout, so exit code 124
means "hung" and exit code 1 means "LeakSanitizer reported leaks".

| binary | compiler / runtime | `detect_leaks=1` | `detect_leaks=0` |
| --- | --- | --- | --- |
| `hello` (1 line, `int main(){}`) | GCC 16.2.0, `libasan.8.dylib` | **hangs, 10/10** | exit 0 |
| `hello` | clang-p2996 (clang 21) | exit 1: 120 B in 3 allocations (all libobjc) | exit 0 |
| `hello` | Homebrew clang 23.1.5 | exit 0, no leaks | exit 0 |
| `cpp-core-tests` (this repo, `gcc16-asan`) | GCC 16.2.0 | **hangs** (after `asserts: 11 (11 passed)`) | exit 0, `PASSED` |
| `cpp-core-tests` (this repo, `p2996-asan`) | clang-p2996 | exit 1: 316 B in 7 allocations (all platform) | exit 0, `PASSED` |

A deliberate 1234 B leak is still reported when the leak check is enabled
(`evidence/p2996-real-leak-with-suppressions.log`).

The GCC hang is therefore **not** caused by this project: a program that does nothing but
`return 0;` hangs the same way, 10 times out of 10.

---

## 2. Problem 1 - GCC 16's `libasan` deadlocks in `StopTheWorld`

### 2.1 What the stack shows

`sample` of the hung hello-world (`evidence/gcc16-hello-deadlock-callgraph.txt`):

```
main thread                                     helper thread (created by StopTheWorld)
  exit                                             thread_start
    __lsan::DoLeakCheck()                            __sanitizer::get_dyld_hdr()
      __sanitizer::StopTheWorld(...)                   dyld_shared_cache_iterate_text_swift
        _pthread_join   <-- waits forever               dyld4::RuntimeState::notifyLoad(...)
          __ulock_wait                                     _xpc_dyld_image_callback
                                                         class_createInstance
                                                        _malloc_type_calloc_outlined
                                                          __sanitizer::Semaphore::Wait()  <-- blocks
                                                            SizeClassAllocator64<...>::GetFromAllocator(...)
                                                              __sanitizer::Semaphore::Wait()
```

Two facts fall out of this:

* The main thread is blocked in `pthread_join` waiting for the helper thread that
  `StopTheWorld` spawns to suspend the other threads.
* The helper thread is blocked in **ASan's own allocator semaphore**
  (`SizeClassAllocator64::GetFromAllocator` -> `Semaphore::Wait`), on its *first* allocation.

So: the thread that has to make progress is waiting for an allocator lock, and the thread that
holds the allocator lock (or the one that would release it) is either suspended by
`StopTheWorld` or is the main thread that is itself waiting for the helper. Classic
stop-the-world / allocator-lock deadlock, entirely inside `libasan.8.dylib`.

The allocation that triggers it is not ours: it is `class_createInstance` (libobjc), called from
dyld's image-load notification while `get_dyld_hdr()` walks the shared cache.

### 2.2 It cannot be worked around from the program side

| attempt | result |
| --- | --- |
| `LSAN_OPTIONS=use_stacks=0` | still hangs |
| `LSAN_OPTIONS=use_stacks=0:use_tls=0:use_registers=0` | still hangs |
| `LSAN_OPTIONS=max_leaks=1`, `report_objects=0` | still hangs |
| `ASAN_OPTIONS=atexit=1` | still hangs |
| pre-warming `dyld_shared_cache_iterate_text()` in `main` (`repro/prewarm_dyld.cpp`) | still hangs, same stack (`evidence/gcc16-prewarmed-deadlock-callgraph.txt`) |
| calling `__lsan_do_recoverable_leak_check()` early, from `main` (`repro/early_lsan.cpp`) | still hangs |
| running the leak check in a forked child, parent kills it after 5 s (`repro/fork_lsan.cpp`) | the *child* still hangs; only the hang is bounded |

The pre-warm does not help because the blocking allocation comes from dyld's *notification* path
(`notifyLoad` -> xpc callback -> libobjc class creation), not from the cache iteration itself.

### 2.3 The fork workaround does not work either

Running the leak check in a forked child is the usual "keep the hang out of the test result" trick.
Measured (`repro/fork_lsan2.cpp`):

* the child's report is polluted by the fork itself (512 B + 256 B blocks from
  `libSystem_atfork_child` / `os_map_64_init`, 17 allocations in total);
* a **deliberate 4321 B leak in the parent is not reported by the child**, because the child's copy
  of the stack still holds the pointer, so the allocation is reachable and not a leak.

So the child neither reproduces the parent's leaks nor gives a clean report. Option D below is
refuted by measurement.

### 2.4 Upstream status: no pending fix in the relevant file

The Darwin stop-the-world implementation is byte-identical in all three trees
(`upstream/`):

```
$ diff gcc16-sanitizer_stoptheworld_mac.cpp gcc-master-sanitizer_stoptheworld_mac.cpp   # identical
$ diff gcc16-sanitizer_stoptheworld_mac.cpp llvm-main-sanitizer_stoptheworld_mac.cpp   # identical
```

The same is true for `lsan_common_mac.cpp`, `lsan_mac.cpp`, `sanitizer_common.cpp`, the allocator
headers and `sanitizer_mutex.h` (which defines `Semaphore`). GCC 16.2.0 ships a libsanitizer that
matches LLVM main in every file we compared.

Consequences:

* There is **no upstream source change to wait for** in the file that deadlocks; GCC's libsanitizer
  is simply a snapshot of LLVM compiler-rt.
* We could not explain, from the sources, why clang 23's runtime does not deadlock while GCC's
  does - the relevant code is identical. What we know empirically: clang 23.1.5 runs the same
  `StopTheWorld` path 10/10 without hanging, and it reports a real leak correctly.

---

## 3. Problem 2 - the p2996 "leaks" are macOS artifacts

The full report for our test binary is `evidence/p2996-leak-report.log`
(`SUMMARY: AddressSanitizer: 316 byte(s) leaked in 7 allocation(s)`). Every allocation is
attributable to the platform:

| bytes | allocation site | verdict |
| --- | --- | --- |
| 72 | `libobjc.A.dylib` -> `_fetchInitializingClassList` | Objective-C runtime init; present in a hello-world too |
| 48 | `libdyld.dylib` -> `ThreadLocalVariables::instantiateVariable` (via `_tlv_get_addr`) | dyld's thread-local storage, allocated on first use of *any* `thread_local` |
| 80 | Apple libc -> our `format_double` (`src/logging/quill_logger.cpp:131`, `snprintf("%g")`) | Apple's float formatting buffer |
| 36 + 32 | indirect children of the 80 B block | same |
| 32 + 16 | indirect children of the 48 B block | same |

The isolated micro-tests in `repro/` confirm each attribution:

* `tlv_trivial.cpp` - a single `thread_local int` produces the same 48 B dyld TLV leak.
* `tlv_nontrivial.cpp` - same with a `thread_local std::shared_ptr`.
* `snprintf_test.cpp` (`%f`, `%.*f`) leaks 148 B more than `snprintf_int.cpp` (`%d`): the float
  path allocates inside Apple's libc.
* `quill_b.cpp` - logging one message produces exactly the dyld TLV allocation; quill's own
  `ThreadContext` is not leaked - it lives in a `thread_local ScopedThreadContext`
  (`upstream/quill/ThreadContextManager.h:423`), and it is the `thread_local` itself that makes dyld
  allocate the 48 B TLV block.

**None of our code leaks.** The 80 B block is reached from our `format_double`
(`src/logging/quill_logger.cpp:131`), but the allocation is Apple's, inside `snprintf`.

---

## 4. Problem 3 - clang 23 works, but cannot build this project (yet)

Homebrew clang 23.1.5 has a clean leak check:

| test | `detect_leaks=1`, no suppressions |
| --- | --- |
| hello-world | exit 0, no leaks |
| deliberate 1234 B leak | exit 1, `1234 byte(s) leaked in 1 allocation(s)` |
| `snprintf("%f")` test | exit 0, no leaks |
| quill hello | exit 0, no leaks |

So a clang 23 ASan build would give us leak checking for free, with no suppression file.

The obstacle is the build, not the runtime:

* `src/reflection_demo.cpp` includes `<meta>` (C++26 static reflection). **No installed macOS SDK
  has a `<meta>` header** - checked MacOSX.sdk, MacOSX26/26.5/27/27.2.sdk and the CommandLineTools
  SDK. p2996 ships its own libc++ that has it; GCC 16's libstdc++ has it; the SDK's libc++ does
  not.
* `cmake/toolchains/cpp-core.cmake` therefore sets **no** reflection flags for `clang23` (the
  `clang23` branch has an empty `_cpp_core_reflection`), and `cmake/cpp-core-check.cmake` only
  checks the compiler identity. A `clang23` build would fail on `src/reflection_demo.cpp`.
* Everything else would build: clang 23 compiles C++26 modules without extra flags (verified with
  a minimal `export module` / `import` pair), and none of the vcpkg headers we use
  (`log/log.hpp`, `stdx/ct_string.hpp`, quill) include `<meta>` (grepped the installed tree).
* There is no `arm64-osx-clang23*` triplet and no `clang23-*` preset yet.

So a clang 23 ASan preset is feasible, but it needs: a triplet, a preset, and a way to keep
`src/reflection_demo.cpp` out of that build (a CMake option), plus a fresh vcpkg build of quill,
cib, stdx and ut against the SDK's libc++.

---

## 5. What we can do

### Option A - keep `detect_leaks=0` on both compilers (today's behaviour)

* **Pros:** zero risk, zero work; the ASan presets still catch memory errors, use-after-free,
  buffer overflows and UBSan violations; the test suites are green on both compilers today.
* **Cons:** no leak detection at all; the README's claim "Leak checking is off on both compilers,
  where an ASan binary with leak checking hangs at exit on this Mac" is only true for GCC - for
  p2996 the leak check *works* and reports only platform noise. A real leak introduced later would
  not be caught by any preset.

### Option B - enable leak checking on p2996 with an LSAN suppression file

Add `cmake/lsan.supp`:

```
leak:libobjc
leak:libdyld
leak:_dyld_shared_cache_iterate_text
leak:snprintf
leak:_vfprintf
```

and set `LSAN_OPTIONS=suppressions=${sourceDir}/cmake/lsan.supp` in the `p2996-asan` test preset.
(`${sourceDir}` is expanded in test preset environment values - verified with CMake 4.4.5.)

Measured result: `cpp-core-tests` exits 0 with `asserts: 11 (11 passed)`, no leaks reported; a
deliberate 1234 B leak is still reported (`evidence/p2996-real-leak-with-suppressions.log`).

* **Pros:** real leak detection on the compiler we develop with; one small, reviewable file; the
  suppressions are narrow (each matches only leaks whose stack passes through that platform
  frame), and we have verified that they do not hide our own leaks; the file is self-documenting
  about *why* each entry exists.
* **Cons:** only covers p2996 - GCC 16 stays without leak detection; a suppression file is a
  maintenance liability (a new platform allocation pattern needs a new entry, and a wrong entry
  could hide a real leak); the suppressions are macOS-specific, so a CI runner on Linux would need
  a different set (on Linux the same code leaks nothing - the artifacts are macOS's).

### Option C - add a `clang23-asan` preset with leak detection on

* **Pros:** the only option that gives *clean* leak detection (no suppressions) with a modern
  compiler; Homebrew clang 23.1.5 is already installed and the toolchain already knows the
  `clang23` compiler id; the leak check catches real leaks with no false positives, so it needs no
  suppression file to maintain.
* **Cons:** the most work of the three: a new vcpkg triplet (`arm64-osx-clang23-asan`), a new
  preset set, a CMake option to exclude `src/reflection_demo.cpp` (the SDK has no `<meta>`), and a
  full vcpkg rebuild of quill/cib/stdx/ut against the SDK's libc++; the third compiler in the
  matrix increases CI time; it still leaves GCC 16 without leak detection; and the reflection demo
  would be missing from that build, so the preset would not cover all the code.

### Option D - run the leak check in a separate process

Refuted by measurement in section 2.3: the forked child hangs under GCC, its report is polluted by
fork-time allocations, and it does not report the parent's real leaks (the child's stack still
holds the pointers, so they are reachable). Listed here only because it is the obvious "keep the
hang out of the test" idea.

### Option E - combination

The pragmatic shape of B + C: enable leak detection wherever the runtime supports it
(p2996 with suppressions today, clang 23 without suppressions once its preset exists), and keep
GCC 16's ASan preset at `detect_leaks=0` with a README note that explains exactly why, so the
next person does not have to rediscover the deadlock.

---

## 6. Recommendation

**Option E: B now, C as a follow-up, GCC 16 stays at `detect_leaks=0` with an explicit note.**

Reasoning, in order of weight:

1. B is cheap, proven by measurement on our own binary, and restores leak detection where it is
   possible today. The suppression file is five lines and every entry is justified by an
   attributed leak.
2. C is the better long-term answer, but it needs SDK support that does not exist yet (`<meta>`);
   doing it as a separate, larger change keeps this one small and reviewable.
3. GCC 16 cannot have leak detection on macOS at all - the deadlock is in its runtime, not in our
   code, and no option avoids it. The honest thing is to document that, rather than pretend
   `detect_leaks=0` is a project decision.

If we prefer to keep the change surface at zero, Option A is defensible, but it should then be
documented accurately: the leak check is off because it is broken on GCC and noisy on p2996, not
because it is off "everywhere by choice".

### What was implemented

| file | change |
| --- | --- |
| `cmake/lsan.supp` | new: the five suppression entries, each with the reason it exists |
| `cmake/presets/cpp-core.json` | `p2996-asan` test preset: `detect_leaks=1` + `LSAN_OPTIONS=suppressions=${sourceDir}/cmake/lsan.supp`; `gcc16-asan`: unchanged, with a `$comment` recording why `detect_leaks=0` is forced |
| `README.md` | a "Leak checking" section with the suppressions, what each one is, and the GCC deadlock |
| `docs/asan-leak-check/` | this review, its evidence and the upstream sources it quotes |

Verified after the change:

```
$ cmake --workflow --preset p2996-asan      # 1/1 Test #1: cpp-core-tests ... Passed
$ ASAN_OPTIONS=detect_leaks=1 <binary>      # without the suppressions: 316 byte(s) leaked in 7 allocation(s)
$ ASAN_OPTIONS=detect_leaks=1 LSAN_OPTIONS=suppressions=cmake/lsan.supp <binary>
                                           # PASSED, asserts: 11 (11 passed), exit 0
$ cmake --workflow --preset gcc16-asan      # 1/1 Test #1: cpp-core-tests ... Passed
```

The first line of that block is the important one: the preset passes *with the leak check on*,
and the same binary without the suppressions fails with the 316 B report, so the leak check is
really running.

One consequence of putting the options in the test presets: they apply only when the tests are run
through a preset. Verified by injecting a deliberate 4096 B leak into `tests/logging_test.cpp` and
running the same binary three ways:

| invocation | result with the leak present |
| --- | --- |
| `ctest --preset p2996-asan` | Failed: `SUMMARY: AddressSanitizer: 4096 byte(s) leaked in 1 allocation(s)` |
| `cd build/p2996-asan && ctest` | Passed - the leak check never ran |
| `./build/p2996-asan/tests/cpp-core-tests` | exit 0 - the leak check never ran |

So the tests have to be run through `ctest --preset <name>` (from the repository root, because CMake
reads `CMakePresets.json` from the current directory) or `cmake --workflow --preset <name>`. The
README says so.

## 7. Follow-up

Option C (a `clang23-asan` preset) is the planned next step, because Homebrew clang 23.1.5 has a
leak check that is clean without any suppressions. It needs:

1. a vcpkg triplet `arm64-osx-clang23-asan.cmake` (same shape as `arm64-osx-p2996-asan.cmake`,
   with `CPP_CORE_COMPILER=clang23`), so quill, cib, stdx and ut are built with clang 23 and the
   sanitizers;
2. a way to keep `src/reflection_demo.cpp` out of that build: it includes `<meta>`, and no
   installed macOS SDK has that header (the SDK's libc++ has no static reflection support yet),
   so a CMake option (for example `cpp_core_REFLECTION_DEMO`) is needed;
3. configure, build, test and workflow presets for `clang23-asan`, plus the leak check enabled
   there without a suppression file;
4. a README update of the preset matrix.

Until then, `clang23` remains usable for the include-what-you-use checks (which already use
Homebrew clang 23).

---

## 8. Reproducing

```sh
# 1. the GCC deadlock (a 2-line program)
g++-16 -std=c++26 -g -O0 -fsanitize=address repro/hello.cpp -o /tmp/hello.gcc16
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 timeout 15 /tmp/hello.gcc16   # hangs (exit 124)

# 2. the stack of the hang (macOS `sample`)
repro/sample_hang.sh /tmp/hello.gcc16 /tmp/gcc_hello

# 3. the p2996 false positives
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 build/p2996-asan/tests/cpp-core-tests
#   -> 316 byte(s) leaked in 7 allocation(s), all platform (see evidence/)

# 4. the same binary with the suppressions
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 \
  LSAN_OPTIONS=suppressions=docs/asan-leak-check/evidence/lsan.supp \
  build/p2996-asan/tests/cpp-core-tests
#   -> PASSED, asserts: 11 (11 passed), no leaks

# 5. clang 23 is clean without any suppressions
/opt/homebrew/opt/llvm/bin/clang++ -std=c++26 -g -O0 -fsanitize=address repro/hello.cpp -o /tmp/hello.clang23
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 /tmp/hello.clang23                # exit 0
```

---

## 9. What is in this directory

The files under `upstream/` are verbatim copies, with their license headers intact:

| source | origin | license |
| --- | --- | --- |
| `gcc16-sanitizer_stoptheworld_mac.cpp`, `gcc16-lsan_*.cpp` | `gcc-mirror/gcc`, branch `releases/gcc-16`, `libsanitizer/sanitizer_common` and `libsanitizer/lsan` | GPL-3.0-or-later with GCC Runtime Library Exception |
| `gcc-master-sanitizer_stoptheworld_mac.cpp` | `gcc-mirror/gcc`, branch `master`, same path | as above |
| `llvm-main-sanitizer_stoptheworld_mac.cpp`, `llvm-main-lsan_*.cpp` | `llvm/llvm-project`, branch `main`, `compiler-rt/lib/sanitizer_common` and `compiler-rt/lib/lsan` | Apache-2.0 WITH LLVM-exception |
| `quill/` | quill 13.1.0 (`odygrd/quill`), `include/quill/` | MIT |

They are here so that the review can be done offline, without a network connection.

```
README.md                                   this document
evidence/
  gcc16-hello-deadlock-callgraph.txt       sample output: the two deadlocked threads
  gcc16-prewarmed-deadlock-callgraph.txt   same, after pre-warming dyld's cache walk
  p2996-leak-report.log                     the 316 B / 7 allocations report, attributed
  p2996-leak-report-with-suppressions.log  the same binary with lsan.supp: clean, 11/11 asserts
  p2996-real-leak-with-suppressions.log    a deliberate leak is still caught
  lsan.supp                                 a copy of cmake/lsan.supp, the file the presets use
repro/
  hello.cpp alloc.cpp real_leak.cpp         the minimal cases (leak / no leak)
  snprintf_test.cpp snprintf_int.cpp        Apple's float formatting allocates, %d does not
  tlv_trivial.cpp tlv_nontrivial.cpp        any thread_local allocates a dyld TLV block
  quill_b.cpp quill_c.cpp                   quill alone: only the dyld TLV block
  prewarm_dyld.cpp early_lsan.cpp           the workarounds that do not work
  fork_lsan.cpp fork_lsan2.cpp               the separate-process idea, and why it fails
  sample_hang.sh                            captures the stack of a hung process
upstream/
  gcc16-sanitizer_stoptheworld_mac.cpp      GCC 16, LLVM's Darwin StopTheWorld
  gcc-master-sanitizer_stoptheworld_mac.cpp GCC master: identical to GCC 16
  llvm-main-sanitizer_stoptheworld_mac.cpp  LLVM main: identical to GCC 16
  gcc16-lsan_common_mac.cpp llvm-main-lsan_common_mac.cpp   identical
  gcc16-lsan_mac.cpp llvm-main-lsan_mac.cpp                 identical
  quill/                                    quill 13.1.0 headers that the analysis quotes
    ThreadContextManager.h Logger.h BackendWorker.h
```
