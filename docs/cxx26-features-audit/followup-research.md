# The follow-up research: eight items

**Date:** 2026-11-12
**Status:** research. **Nothing here is applied to the build.** The build lane is parked: no
builds, no compiler or toolchain installs or configuration, no CMake or preset build runs, no test
or ASan runs. Every finding below was reached by reading - the project's own files, the installed
headers, or upstream - and anything that would need a compile is written down as a question
instead.

This is **part 18** of the audit. Parts 1-17 answered the owner's three questions. This part
answers a different question: **what did the audit leave unasked?**

---

## The state this starts from

The audit has **83 open items**, and they decompose exactly (verified by parsing the "settled by"
column of every row, plus the six defect headings):

| Kind | Count | What resolves it |
|---|---|---|
| Owner decisions | **13** | the owner's answer. Four of them gate the plan: `FMT-14`, `TOOL-13`, `TOOL-14`, `BUILD-7` |
| Compile / run / preprocessor | **70** | the build lane reopening - mechanical, not research |
| Registry read | **0** | `VCPKG-1` and `VCPKG-2` were answered by section 2 below - the registry at the pinned baseline turned out to be readable after all |

(It was 83 when this part opened; section 2 answered the two registry items and moved them to
`open-items.md` section 12, section 4 answered `QUIL-8` the same way, and sections 5 and 6 added
`FMT-15`, `MOD-10` and `MOD-11` of their own.)

**The audit's own research is complete.** Seventeen parts, the upstream sources all vendored
(`upstream/`), the root README checked line by line (part 16), the owner decisions collected into
one sheet (part 17). Nothing is pending on the research lane except two items that wait on other
people: the registry checkout, and the commit identity (which waits on dotfiles-lead's fnox
profile).

So the 81 are **not** the backlog this part addresses. They are the existing plan's backlog.

## What the audit never asked

Reading the plan against the build files surfaced one defect and seven gaps. None of them is in
the 81, because the 81 are the audit's *questions about the code it was written to understand* -
and these are questions about the **code, the build and the claims** the audit did not examine.

Three of them touch the project's central claims:

- The README says the overlay ports are "pinned to the latest upstream commit"
  (`README.md:366`). That is a point-in-time truth that silently decays, and nothing detects it.
- The README says "both compilers build and pass the tests". `clang-p2996` is validated by
  `MATCHES "p2996"` - **no version bound at all**, let alone a commit - and the compiler on `PATH`
  is a moving symlink between git snapshots.
- The module's interface is the whole API (`README.md:120`), and its **preconditions are
  undefined**: nothing in the project says whether `log()` before `setup()` is valid, whether
  `setup()` is idempotent, or whether `log()` can throw.

And one of them is a **defect in the plan itself**, found by reading rather than by compiling -
which is exactly what a research lane is for.

## The checklist

| # | Item | Status | Finding |
|---|---|---|---|
| 1 | The `static_assert` formatter tests cannot reach the code they test | ☑ **done** | **Route B** - a private `format_tests.hpp` included by the module, so the asserts test the module's own copy. The plan's `tests/format_static_asserts.cpp` would compile a second copy and inflate the coverage union |
| 2 | Build reproducibility and upstream drift | ☑ **done** | The pin inventory, what each compiler bump breaks, and a three-layer drift mechanism. **And a correction:** the two "registry read" items were never blocked - the registry at the pinned baseline is readable over HTTP, and it answers both |
| 3 | The public API has no contract | ☑ **done** | The contract, derived from the implementation: threading, start-up, flushing, levels, message handling and the error model - written out as prose for the module's header comment and the README. **The headline:** the level threshold is not consulted on the module path (DEF-1), so the contract cannot promise the filtering until the fix lands |
| 4 | A benchmark harness | ☑ **done** | Six metrics (M1-M6), a five-step baseline ladder (B0-B5), the variables, and three traps the harness has to avoid - `high_resolution_clock` is the wall clock on libstdc++, the per-message allocation is 0 or 1 depending on the small-string threshold, and the clock reads are as expensive as the measurement. **And a correction:** `QUIL-8`'s premise is wrong - `<true>` means "honour the flush threshold", the threshold is 0 by default, and quill's own default is the same value |
| 5 | A differential test between the two logging paths | ☑ **done** | The case list, classified: **11 of the 15 divergences are testable** as a runtime differential comparison; the other four are asymmetric compile-time rejections and need a "must not compile" mechanism the project does not have. The oracle is three columns - the standard, the catalog path, the module path - with the rule that the expectations come from the standard, not from the implementation. Two modes, switched by `FMT-14`. And the test would **trigger DEF-6**, so it needs its own catalog |
| 6 | Costing the `import std;` option | ☑ **done** | The row-by-row flip analysis of the twenty-row table: **five rows flip cleanly, one partly, three lossily, one only in combination, nine not at all.** Two results the audit did not have: **rows 19 and 7-9 are a package** (validating with the standard's grammar while formatting with the module's own is *worse* than not validating), and **the GCC 16 blocker is unverified in the project's configuration** - the project compiles with `-fmodules-ts`, the matrix was measured with `-fmodules`, and the project's own GCC 16 build does the shape the matrix says fails |
| 7 | Four smaller questions | ☑ **done** | **7.1** consuming the module from another project: CMake's `install(EXPORT ... CXX_MODULES_DIRECTORY ...)` is the load-bearing piece, and the project's own obstacles are named - `format.hpp` is a `PRIVATE` source but a **public build-time dependency** of the installed module, `internal.hpp` is in the global module fragment, and the export publishes quill's and cib's whole closure. **7.2 MemorySanitizer: no** - two independent blockers (GCC 16 has no `memory` sanitizer; clang's MSan supports only Linux/NetBSD/FreeBSD) and the installed libc++ has no MSan support at all. **7.3 `ut`'s supply chain:** good and unchanged - an immutable released tag, a SHA512, a byte-identical installed tree, 419 lines, two contributors, and **no vcpkg registry port**, so the baseline gives it no protection. **7.4 quill:** keep it - current (13.1.0, 2026-10-17), MIT, and `quill::Codec<Arg>` is the *supported* extension point `QUIL-1` depends on |
| 8 | Re-validating the audit's time-sensitive claims | ☐ **not started** | — |

---

## 1. The `static_assert` formatter tests cannot reach the code they test

**The question.** The plan's step 4 puts the formatter's `static_assert` tests in a new
`tests/format_static_asserts.cpp`. Can such a file exist, and would it prove anything?

**The evidence, before the research.**

`modules/logging/CMakeLists.txt` says:

```cmake
target_sources(
    cpp-core-logging
    PUBLIC
        FILE_SET CXX_MODULES FILES logging.cppm
    PRIVATE
        ${PROJECT_SOURCE_DIR}/src/logging/quill_logger.cpp
        format.hpp
)

target_include_directories(cpp-core-logging PUBLIC "${PROJECT_SOURCE_DIR}/include")
```

`format.hpp` is a **PRIVATE** source (`:19`), and the only published include directory is
`include/` (`:22`). The module's own directory is not on any include path for a consumer.

And the module includes it in its **private implementation section** - after `export module`
(`modules/logging/logging.cppm:33`), so it is not reachable by `import` either.

**Three routes, and what each one actually proves.**

### Route A - a new test translation unit (what the plan says)

`tests/format_static_asserts.cpp` would have to reach `modules/logging/format.hpp`. It cannot
`import` it - it is not exported. It is not on any include path - the module publishes only
`include/`. So it needs a **relative path across the source tree**:

```cpp
#include "../../modules/logging/format.hpp"
```

That compiles, because `format.hpp` is standard-library-free by design and `#pragma once` makes
the double include harmless. But it compiles a **second copy** of the formatter, in the test TU's
global module, and that copy is not the one the module uses.

What does a second copy prove? **The rules, but not the module.** The source text is identical, so
a `static_assert` over the second copy does verify the formatting rules. But:

- it says nothing about whether the **module's** copy is `constexpr`. If the `constexpr` sweep
  (plan step 3) were applied to the test's copy and not the module's - or forgotten in the module -
  the test would still pass, while the thing the sweep is *for* (the module constant-evaluating its
  own formatter) would not hold;
- it creates a **source-layout dependency** from `tests/` to `modules/logging/`, which breaks if
  the module moves;
- and it interacts badly with the coverage gate. The formatter's templates are emitted into the
  **importing** translation units (the project's own comment says so: `format.hpp:5-6` - *"the
  compiler emits them into the translation units that instantiate the module's templates"*), so
  `format.hpp`'s lines are already reported from several TUs. The gate merges per file by union
  (`TOOL-11`: *"any count > 0 means covered"*). A second copy in `tests/` joins that union, and a
  line executed **only** in the test's copy would count as covered for the module's.

### Route B - a private test header, included by the module

```cpp
// modules/logging/logging.cppm, private implementation section

#include "format.hpp"
#include "format_tests.hpp"
```

`format_tests.hpp` holds the `static_assert`s and the `constexpr` helper. They are compiled as part
of the module interface unit, **against the module's own copy of the formatter**, on both
compilers, in every build that compiles the module - which is every build.

This is the only route that tests the actual code. It also needs **no CMake change** (the header
is a private source of the same target), **no include-path change** (nothing outside `modules/`
sees it), and creates no second copy, so the coverage union is untouched.

The cost is one thing: the `static_assert`s are compile-time-only, so `format_equals` is never
instantiated at runtime and its lines would show as **zero-count** in the coverage report. That is
the same category the audit already identified - `scan_format` and `format_matches` are `consteval`
and *"produce no runtime arcs"* (`coverage-gaps.md` §1.2) - so it needs one entry in the reviewed
exclusion list, with the justification *"compile-time only; verified by the compiler"*.

### Route C - export a test entry point from the module

`import com.rsm.logging;` and call an exported `constexpr` function. This works, but it
**exports the formatter's internals through the module's public interface** - and the module's
interface *is* the whole API (`README.md:120`). It would widen the public surface to make a test
possible, which is backwards. **Rejected.**

### The recommendation

**Route B.** The shape:

```cpp
// modules/logging/format_tests.hpp
#pragma once

#include "format.hpp"

namespace com::rsm::logging::detail {

// Formats a message into a fixed buffer and compares it with the expected text.
// The arguments must be constexpr objects of static storage duration: format_message takes
// their addresses, so a temporary cannot be constant-evaluated (part 9, caveat 2).
template <unsigned long N, typename... Args>
[[nodiscard]] constexpr auto format_equals(char const (&expected)[N], char const *text,
                                           unsigned long length, Args &&...args) -> bool {
  message_buffer buffer;
  format_message(buffer, text, length, forward<Args>(args)...);
  if (buffer.size() != N - 1U) {
    return false;
  }
  for (unsigned long i = 0U; i < N - 1U; ++i) {
    if (buffer.data()[i] != expected[i]) {
      return false;
    }
  }
  return true;
}

}  // namespace com::rsm::logging::detail

namespace com::rsm::logging::detail::tests {

// Namespace-scope constexpr variables have static storage duration, which is what
// format_message's address-taking requires.
constexpr int answer = 42;

static_assert(format_equals("the answer is 42", "the answer is {}", 16, answer));

}  // namespace com::rsm::logging::detail::tests
```

Three details make it work, and each was checked:

- `message_buffer` is **default-constructible in a constant expression**: it has no user-provided
  constructor, `char chars[capacity]{}` and `unsigned long used = 0U` are constant initialisers
  (`format.hpp:204-205`), so the implicit default constructor is `constexpr`.
- `forward` is the header's **own** `forward` (`format.hpp:126-136`), not `std::forward` - the
  module may not use the standard library.
- The test arguments are **namespace-scope `constexpr` variables**, which have static storage
  duration, which is exactly what part 9's caveat 2 requires (`format_message` takes the
  addresses of its arguments, so a temporary cannot be constant-evaluated).

### What it changes in the plan

Plan step 4 becomes *"add `modules/logging/format_tests.hpp`, included by the module's private
implementation section"* instead of *"add `tests/format_static_asserts.cpp`"*. The coverage gate
gains one exclusion entry.

**This does not remove a compile question.** `FMT-5` already asks whether the `static_assert`
pattern constant-evaluates on both toolchains, and that is still open - the build lane has to
settle it. What this section settles is **where the asserts live and what they prove**, which no
compile would have told us.

---

## 2. Build reproducibility and upstream drift

**The question.** The project claims two things that decay: that both compilers build, and that
the ports track upstream. What is the minimum set of pins that makes the build reproducible, and
what would detect a drift?

**The evidence, before the research.**

- `cmake/cpp-core-check.cmake:29` validates `p2996` with `_path MATCHES "p2996"` - **no version
  bound**. The `gcc16` and `clang23` branches do check a version range; `p2996` does not.
- The compiler on `PATH` is `~/.local/share/p2996/current`, a **symlink between git snapshots**.
  The machine has at least two (`562409c...`, `f17c8d6...`); the symlink is repointed by
  whatever installs a new one.
- The four Intel overlay ports use `version-date`, which is vcpkg's form for a port with **no
  semantic version** - so vcpkg never learns that a newer upstream exists. `ports/README.md`
  says so itself.
- `README.md:366-367` states the ports "are pinned to the latest upstream commit". True on
  2026-11-12; false after the next upstream push; and nothing reports the change.
- There is no CI (BUILD-5), no git remote, and no upstream watch.

**What is needed.** A pin inventory, an assessment of what a compiler bump breaks, and a drift
detection mechanism. To be worked through in this section.

### The pin inventory

Every input the build depends on, and whether it is pinned:

| What | Pinned to | Where | Pinned how well |
|---|---|---|---|
| the `gcc16` compiler | GCC 16.x | `cpp-core-check.cmake:17-19` | **a version range** (16 ≤ v < 17), not a build |
| the `clang23` compiler | Clang 23.x | `:22-25` | **a version range** (23 ≤ v < 24), and explicitly *not* a p2996 path |
| the `p2996` compiler | **nothing** | `:27-30` | **not pinned at all** - the path only has to contain the string `p2996` |
| the p2996 *snapshot* | a commit | the install tool | **not in the repo** - the repo never names a commit |
| the vcpkg registry | `245d37306671ea67d8f313081a81aae8079f8916` | `vcpkg.json:7` | **exactly** - a registry commit, which is the strongest form vcpkg offers |
| the vcpkg *tool* | a build | the install tool | **not in the repo** - no file records the tool version |
| the five overlay ports | a `REF` + a `SHA512` | `ports/*/portfile.cmake` | **exactly** - the archive hash is checked on download |
| the overlay ports' *upstream* | `HEAD_REF main` | the same | **not pinned** - `HEAD_REF` is what `--head` would use, not what a normal build uses |
| the four Intel ports' version | `version-date` | `ports/*/vcpkg.json` | **a date, not a version** |
| `ut`'s version | `1.2.1` | `ports/ut/vcpkg.json` | exactly, and its `REF` **is** the `v1.2.1` tag |
| CMake | `cmake_minimum_required(VERSION 3.31)` | `CMakeLists.txt:1` | a floor, not a version |
| the `import std` gate | `f35a9ac6-8463-4d38-8eec-5d6008153e7d` | not in the project | **not set at all** - the project never uses `import std;` |
| the standard libraries | the compiler's own | - | follow the compiler |
| the tooling | the machine's installs | not in the repo | **not pinned** - clang-format 23.1.5, cmakelang 0.6.13, gcov-16 16.2.0 are all machine state |

**The pattern.** Everything vcpkg touches is pinned by hash; everything the *toolchain* touches is
pinned by a version range or not at all. The reproducibility of this build rests on the vcpkg
graph, which is strong, and on the machine's toolchain state, which is not recorded anywhere in
the repository.

### What a compiler bump actually breaks

The three compilers are not interchangeable, and a bump to each breaks something different.

**A GCC bump (17.x) breaks the reflection flag.** The toolchain sets `-freflection` for `gcc16`
(`cpp-core.cmake:39`) and `-freflection -fexpansion-statements -fannotation-attributes` for
`p2996` (`:48`). GCC 16 refuses `-freflection` below `-std=c++26`, which is why the flags live in
`CPP_CORE_REFLECTION_FLAGS` and are applied only to this project's C++ compiles
(`cpp-core-check.cmake:40-42`). A GCC 17 that renames or gates that flag differently would fail
the *first* compile of the module, not a configure.

**A p2996 bump breaks three things at once, and the check will not catch any of them.** The
`p2996` branch of `bloomberg/clang-p2996` is what the project builds with; upstream's default
branch is `purpose`, which is a different line of development (its tip is from June 2025, while
the `p2996` branch's tip is from November 2026). A new snapshot on the `p2996` branch can change:

1. **the reflection dialect.** `-fexpansion-statements` and `-fannotation-attributes` are
   Bloomberg's own flags, defined in the fork's `Options.td` (`:3609`, `:3614`), not upstream
   clang's. They can be renamed or removed without notice, and the toolchain hard-codes them.
2. **the module binary format.** llvm#63939: a BMI is locked to the clang that built it. A new
   snapshot invalidates every cached BMI, so a stale build tree fails in a way that reads like a
   project bug rather than a toolchain change. This is also why the project's clang-tidy is
   Homebrew's clang 23.1.5 and not the p2996 compiler - the two cannot read each other's BMIs
   (`tooling-design.md`, blocker (b)).
3. **the standard library's shape.** The p2996 snapshot ships its own libc++ - and the installed
   one has `<meta>` with `std::meta::nonstatic_data_members_of` (`<meta>:74`), which Homebrew's
   libc++ does not have at all. `src/reflection_demo.cpp` depends on it.

**A CMake bump breaks the `import std` gate UUID - but only if the project ever uses it.** The
UUID is version-specific (`f35a9ac6-...` for CMake 4.4+, `451f2fe2-...` for 4.3.x) and became
non-gated in 4.5. The project sets **no** gate today - `grep` for
`CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` finds it only in the vendored `upstream/ut/CMakeLists.txt`.
So this is a constraint on option (c) in part 4, not on the build as it stands.

**A libc++ bump breaks the hardening default.** The toolchain sets `_LIBCPP_HARDENING_MODE`
explicitly (`cpp-core.cmake:117-129`), so the mode names matter, not the default. The installed
libc++ 21 defines all four (`__config:123-126`): `NONE` (1 << 1), `FAST` (1 << 2),
`EXTENSIVE` (1 << 4) and `DEBUG` (1 << 3) - and `__config_site:43` sets
`_LIBCPP_HARDENING_MODE_DEFAULT 16`, which is `EXTENSIVE`. A future libc++ that renames or
reorders a mode breaks the configure with a hard `#error` (`__config:139-147`), which is at least
an honest failure.

### The correction: the two "registry read" items were never blocked

The audit recorded `VCPKG-1` and `VCPKG-2` as settled by "reading the registry at the pinned
baseline", and said that read could not be done because `$VCPKG_ROOT` is the vcpkg *tool* with no
`ports` tree and no `.git`.

**That is true of the local install and false of the registry.** The registry is a git
repository, and the pinned baseline is a commit in it. Reading a file *at that commit* does not
require a checkout - the GitHub raw endpoint serves it. The read was done, and it answers both
items.

**`VCPKG-2` - do the five overlay ports shadow builtin vcpkg ports? No.** The baseline's tree
was enumerated in full (17,869 paths, `truncated: false`) and searched:

| Overlay port | in `ports/` at the baseline | in `versions/` at the baseline |
|---|---|---|
| `ut` | **no** | **no** |
| `intel-cib` | **no** | **no** |
| `intel-cpp-std-extensions` | **no** | **no** |
| `intel-baremetal-concurrency` | **no** | **no** |
| `intel-baremetal-senders-and-receivers` | **no** | **no** |

The nearest names the registry *does* ship are `utf8-range`, `utf8h`, `utf8proc` (not `ut`) and
`intel-ipsec`, `intel-mkl`, `intelrdfpmathlib` (not the four Intel ports). So `ports/README.md`'s
warning does not apply today: **none of the five shadows a builtin port, and all five therefore
track the upstream rather than the pinned baseline** - which is the *opposite* of the failure
`ports/README.md` warns about, and is worth knowing before someone adds a builtin port with one
of these names.

**`VCPKG-1` - does the upstream vcpkg `quill` port have an opt-in feature for an external fmt?
No.** The upstream `quill` port at the baseline has **no `features` key at all** and depends only
on `vcpkg-cmake` and `vcpkg-cmake-config`; its portfile passes no fmt-related option. And quill
13.1.0's own CMakeLists has no fmt switch either - there is no `QUILL_*FMT*` option among its 26
`option()` calls, and it installs `include/quill/bundled/fmt/*` unconditionally, exposing it as
the `fmtquill` interface target. So **the two copies of fmt are structural**, exactly as part 12
recorded, and the answer to VCPKG-1's question is that no such feature exists to be opted into.

**What this changes about the drift.** The two registry ports that *are* in the graph - `quill`
13.1.0 and `fmt` 12.2.1 - are **registry** ports, so they are pinned by the manifest's
`builtin-baseline` and a baseline bump is what moves them. The five **overlay** ports are not in
the registry's version database at all, so `vcpkg upgrade` cannot see them and the baseline
cannot move them. The two mechanisms are disjoint, and the project's README describes only the
overlay half.

### The drift detection mechanism

Three layers, cheapest first. **None of this is applied** - the build lane is parked - but the
shapes are known and each is a small script or a one-line change.

**Layer 1 - a version bound for `p2996`.** The check at `cpp-core-check.cmake:27-30` accepts any
Clang whose path contains `p2996`. A bound is easy and catches gross changes:

```cmake
elseif(CPP_CORE_COMPILER STREQUAL "p2996")
  if(_id STREQUAL "Clang" AND _path MATCHES "p2996" AND _ver VERSION_GREATER_EQUAL 21)
    set(_ok TRUE)
  endif()
```

That is a floor, not a pin - it catches a p2996 that becomes clang 24, and nothing else. A true
pin would compare the snapshot's commit against a recorded one, which means the project would have
to name a commit in a tracked file. **That is a new tracked artefact and therefore an owner
decision**, in the same family as `BUILD-7` (the committed stable-catalog file). The
recommendation is to record it, because the alternative - an unpinned compiler whose BMI format
and reflection flags can change under the project - is the weakest link in the whole chain.

**Layer 2 - a drift check for the overlay ports.** The `REF` in each portfile is a commit, and
`git ls-remote` can report the upstream's current tip without cloning. The check is one command
per port and it works today:

```
git ls-remote https://github.com/intel/compile-time-init-build.git HEAD
```

Run on 2026-11-12, all five overlay ports' `REF`s **still match** their upstream's `HEAD`:

| Port | pinned `REF` | upstream `HEAD` | state |
|---|---|---|---|
| `intel-baremetal-concurrency` | `77be79110fd8...` | `77be79110fd8...` | current |
| `intel-baremetal-senders-and-receivers` | `5629659b781b...` | `5629659b781b...` | current |
| `intel-cib` | `b5c68e65801f...` | `b5c68e65801f...` | current |
| `intel-cpp-std-extensions` | `94546c5a9122...` | `94546c5a9122...` | current |
| `ut` | `dc65567be78f...` | `dc65567be78f...` | current |

So the README's claim "are pinned to the latest upstream commit" is **true today**. The defect is
not that it is false; it is that **nothing checks it**, so it becomes false silently. The
mechanism is a script that does the five `git ls-remote` calls and fails when a tip differs from
the pinned `REF`. It has no build dependency, runs in under a second, and can be run by hand or
by CI (which does not exist - `BUILD-5`).

**Layer 3 - `version-date` is the wrong field for a port that pins a commit.** `version-date` is
vcpkg's documented scheme for *"[live at HEAD](https://learn.microsoft.com/en-us/vcpkg/users/versioning)"
libraries* - a library with no release versioning. Three of the four Intel ports have **no tags
at all** upstream, so `version-date` is the *correct* scheme for them. But `intel-cib` **does**
have tags (`v1.7.0`, `v1.0.0`, `v0.2.2`, ...), and its port pins a `main` commit from 2026-11-09
that is **not** any tag - it is a dependabot merge commit. A port that tracks `main` should say
so; a port that could track a release should.

The one concrete improvement available: **`ut`'s port is already correct** - `version: 1.2.1`
with `REF dc65567be78febd265ca36c324e1c504512d4d74`, and that `REF` **is** upstream's `v1.2.1`
tag exactly. It is the model the other four could follow if they gained tags.

### What a compiler bump would have broken here, specifically

A concrete walk through of the "what breaks" list, with this project as the subject:

| A bump to | breaks | where it would show | how loudly |
|---|---|---|---|
| GCC 16 → 17 | the reflection flag's spelling or gating | the first module compile | loud - a compiler error naming the flag |
| p2996 → a new snapshot | the BMI cache | any stale build tree | **confusing** - reads like a project bug |
| p2996 → a new snapshot | `-fexpansion-statements`, `-fannotation-attributes` | the first module compile | loud - "unknown argument" |
| p2996 → a new snapshot | `<meta>` in libc++ | `src/reflection_demo.cpp` | loud |
| CMake 4.4 → 4.5 | the `import std` gate | nothing today | **silent** - the project does not use it |
| libc++ 21 → 22 | a hardening mode's name | the configure | loud - libc++'s own `#error` |
| a registry baseline bump | `quill`, `fmt` | the vcpkg install | loud |
| an overlay `REF` bump | the library's behaviour | anywhere | **silent** - that is the whole point |

The last row is why the drift check matters more than the version bound. A compiler bump breaks
the build; a library bump breaks the *program*, and the program is the thing the project exists
to provide.

---

## 3. The public API has no contract

**The question.** The module's interface is the whole API. What are its preconditions - and what
does it promise on failure?

**The evidence, before the research.**

`grep` for `thread-safe`, `noexcept`, `can throw` or `error model` in
`modules/logging/logging.cppm` returns **nothing**. The exported surface is:

```cpp
auto setup() -> void;
auto flush() -> void;
auto set_level(level l) -> void;
[[nodiscard]] auto current_level() -> level;
auto log_raw(level l, char const *message, unsigned long length, ...) -> void;
auto log(level l, format_string<...> fmt, Args &&...args) -> void;
auto trace/debug/info/warning/error/critical(...) -> void;
```

(`logging.cppm:86-151`.)

Nothing states whether `setup()` is idempotent, whether `log()` before `setup()` is valid,
whether `set_level()` may race with `log()`, or whether any of them can throw. Part 14
established that the *logger* is created once thread-safely and that the *level threshold* is
atomic - but that is two facts about the implementation, not a contract for the caller.

**Why this matters now.** The coverage work is about to write tests. Tests written against an
undefined contract either test the implementation by accident or encode a behaviour nobody chose.

### The contract, derived from the implementation

Every claim below is read from the source, not assumed. Where the implementation and the comment
disagree, both are given.

#### `setup()` - starts the backend, and is idempotent

`logging.cppm:86` is `auto setup() -> void { detail::start_logger(); }`, and the comment says
*"Idempotent: the first log call starts it too."* Both halves are true:

- **Idempotent**, because `quill_logger()` (`quill_logger.cpp:83-91`) holds the logger in a
  function-local static with an initializer. C++ guarantees that initializer runs exactly once
  ([stmt.dcl]/8-9), and concurrent callers block until it completes. So `setup()` twice is one
  start.
- **Optional**, because `emit()` (`quill_logger.cpp:105-119`) calls `quill_logger()` too, so the
  first log call starts the backend whether or not `setup()` was called. **`log()` before
  `setup()` is valid** and is not an error.
- **It starts quill's backend, which registers a `std::atexit` handler** (`quill/Backend.h:70-74`).
  That handler stops the backend and drains the queues, so messages queued before `main` returns
  are not lost. The project's own `main()` does not need to stop anything.

**The one thing `setup()` does not do:** it does not make the *first* log call cheaper or
different. It only moves the backend's start earlier. The contract should say that, because
"setup() prepares the logger" invites a reader to expect more.

#### `flush()` - blocks until the queue is written, and has a real precondition

`logging.cppm:89` is `auto flush() -> void { detail::flush_logger(); }`, which calls
`quill::Logger::flush_log()` (`quill_logger.cpp:95-99`).

- **It blocks the calling thread** until the messages queued so far have been written
  (`quill/Logger.h:604`).
- **It must not be called from the destructor of a static object.** Quill says so explicitly
  (`quill/Logger.h:613`): *"Do not call this function from the destructor of a static object. This
  may lead to application crashes if the thread-local ThreadContext is destroyed before the static
  object invoking `flush_log`."* The project's public API says nothing about it. **This is
  `QUIL-9`, and it is a documentation defect, not a bug** - the project's own `main()` calls
  `flush()` from `main` (`src/main.cpp:15`), not from a destructor.
- **It throws if called from quill's backend thread** (`quill/Logger.h:623-629`:
  `QuillError{"logger->flush_log() cannot be called from the backend worker thread"}`). A consumer
  cannot normally reach the backend thread, so this is a formality - but it means `flush()` is
  **not** `noexcept`.
- **`flush_logger()` null-checks the logger** (`quill_logger.cpp:96`) - but `quill_logger()` never
  returns null, so the check is dead code today. It is defensive, not a behaviour.

#### `set_level()` / `current_level()` - atomic, and **the level does not filter**

`set_level()` writes the **logger's** threshold (`quill_logger.cpp:101`); `current_level()` reads
it back (`quill_logger.cpp:103`).

- **The read and the write are atomic.** Quill's `_log_level` is a `std::atomic<LogLevel>`
  (`quill/core/LoggerBase.h:135`, `:149`), read and written with `memory_order_relaxed`. So
  `set_level()` racing with `log()` is **not a data race** - it is a benign race with an
  unspecified winner, like `std::cout` from two threads. The contract can say *"the level may be
  changed concurrently with logging; a message may or may not be filtered according to the order
  the two operations happen in."*
- **`current_level()` round-trips exactly.** The module's six levels map onto quill's six
  distinct ones (`quill_logger.cpp:37-55`), and back (`quill_logger.cpp:57-79`). The audit
  confirmed this in part 14.
- **But setting the level does not filter anything on the module path.** This is **DEF-1**: the
  project's `emit()` calls `log_statement_runtime_metadata` directly (`quill_logger.cpp:117`), and
  that function **never calls `should_log_statement`** - it goes straight to the queue
  (`quill/Logger.h:427-476`). The filtering happens later, in the backend, against each **sink's**
  threshold (`quill/backend/BackendWorker.h:1500`), and the sink's default is `TraceL3`
  (`quill/sinks/Sink.h:279`) - the least severe level, so everything passes.

**So the contract cannot say "messages below the level are not logged" - that is false today.**
It has to say what is true: *"`set_level()` sets the logger's threshold. Until DEF-1 is fixed, that
threshold is not consulted on the module path, so every message is emitted."* A contract that
promised the filtering would be a contract the implementation does not keep.

#### The log functions - what they do with the arguments

- **`log()` formats on the calling thread**, into a **fixed 2,048-byte stack buffer**
  (`logging.cppm:112-114`, `format.hpp:154-156`), then copies the result into a `std::string`
  (`quill_logger.cpp:118`). So **each module-path message costs one copy of its bytes on the
  calling thread**, plus a heap allocation for any message longer than the small-string threshold
  (22 characters on libc++ 21, 15 on libstdc++ 16 - see section 4), and a message longer than
  2,047 bytes is **silently truncated** at the buffer's
  capacity (`format.hpp:163-165`).
- **`log_raw()` takes an already-formatted message** and a length, and passes them through
  unchanged (`logging.cppm:101-105`). It does **not** copy into the 2,048-byte buffer - it goes
  straight to `emit()`.
- **The format string is checked at compile time, but only for the *number* of arguments.**
  `format_string`'s constructor is `consteval` and calls `format_matches<sizeof...(Wrapped)>`
  (`logging.cppm:71`), which counts the replacement fields. It does **not** check each argument's
  *type* against the format specification - so `info("{:s}", 42)` compiles and the specification is
  ignored. **This is DEF-5.**
- **The source location is the call site's**, captured by the `format_string` constructor's
  defaulted parameters (`logging.cppm:67-69`). A default argument is evaluated at the call site, so
  `__builtin_FILE()` names the caller, not the module.

#### The error model - there isn't one, and that is the finding

**None of the public functions is `noexcept`, and none documents what it does on failure.**

| Function | Can it throw? | What would throw |
|---|---|---|
| `setup()` | yes | quill's `Backend::start()` validates its options and starts a thread; `create_or_get_sink`/`create_or_get_logger` can throw `QuillError`; a thread-creation failure throws `std::system_error` |
| `log()`, `log_raw()`, the shortcuts | yes | `std::bad_alloc` from the `std::string` copy (`quill_logger.cpp:118`) or from the queue's growth; `QuillError` from quill's internals |
| `flush()` | yes | `QuillError` if called from the backend thread (`quill/Logger.h:627`) |
| `set_level()` | yes | `std::bad_alloc` - the logger's first use allocates the sink and the backend's structures |
| `current_level()` | effectively no | it reads an atomic; but its *first* call creates the logger, which can throw |

**The honest contract is therefore a "may throw, and the caller is expected to handle it" one** -
which is the C++ default and needs no `noexcept` on the API. But it should be **stated**, because
a logging call that can throw is a real design decision: a caller logging from a destructor, or
from a `noexcept` function, has to know.

There is also a **latent** issue worth naming: the queue is `UnboundedBlocking` by default
(`quill/core/FrontendOptions.h:53`), so a slow backend makes the *producer* block rather than drop.
That is a deliberate choice, but it is invisible from the API.

#### The contract, written out

This is the shape the documentation should take - as prose in the module's header comment and in
the README, not as a new file (the module's interface **is** the API, so the contract belongs
there):

> **Threading.** Every function is safe to call from any thread. The logger is created once,
> lazily, and shared. `set_level()` may be called concurrently with logging; the threshold is
> atomic, so a message logged at the same moment as a level change may or may not be filtered.
>
> **Start-up.** `setup()` is optional - the first log call starts the backend too - and
> idempotent. It exists to start the backend before any work happens, so that a log call from a
> static initialiser cannot race the backend's own start-up.
>
> **Flushing.** `flush()` blocks until the messages queued so far have been written. It must not
> be called from the destructor of a static object. Messages queued before the process exits are
> drained by quill's own exit handler, so `flush()` is only needed when the output must be on the
> console before `main` returns.
>
> **Levels.** `set_level()` sets the logger's threshold; `current_level()` reads it back
> exactly. *Until the level-filtering defect (DEF-1) is fixed, the threshold is not consulted on
> the module path, so every message is emitted.*
>
> **Messages.** The module path formats on the calling thread into a fixed 2,048-byte buffer, so
> a longer message is silently truncated. Each message costs one copy of its bytes on the calling
> thread, plus a heap allocation for any message longer than the small-string threshold. The format
> string is checked at compile time for the *number* of arguments only, not for the type of each
> argument against the format specification.
>
> **Errors.** No function is `noexcept`. Logging can fail to allocate, and `flush()` throws if it
> is called from the logger's backend thread. A caller in a `noexcept` context must catch.

#### What this changes

Two of the audit's items become **documentation work rather than research**:

- **`QUIL-9`** - the public `flush()` needs quill's static-destructor caveat. It is already an
  owner decision followed by an edit; the *content* of the caveat is now written, so the decision
  is only about where the text goes (the module's header comment, the README, or both).
- **DEF-1** - the contract must either promise the filtering (and the fix must land first) or
  state that the threshold is not consulted. **The recommendation is to fix DEF-1 and write the
  promise**, because a public API whose level setting does nothing is worse than one that says so
  plainly - and DEF-1 is already plan step 1.

And one **new** item falls out of it:

- **A test for the contract itself.** `tests/logging_test.cpp` today asserts that the level round-trips
  (`:74-81`) and that logging does not throw (`:92-98`). It does **not** assert that a message
  below the threshold is suppressed - because that is DEF-1's test and DEF-1 is unfixed. So the
  suite currently *passes* while the API's most important promise is false.

---

## 4. A benchmark harness

**The question.** `QUIL-8` asks whether the module path should flush on every message, and the
audit's own answer is *"a measurement, not a guess"*. There is nothing to measure with.

**The evidence, before the research.**

- The repository contains **no benchmark files at all** - no `bench*`, no harness, no baseline.
- The module path formats on the calling thread and copies the result into a `std::string`
  (documented in parts 13 and 14), so **every module-path message costs a copy of its bytes on the
  calling thread** - and, as the research below shows, a heap allocation only for messages longer
  than the small-string threshold, which is 22 characters on libc++ and 15 on libstdc++, so the
  earlier "one heap allocation per message" claim was wrong for short messages.
- The catalog path queues the arguments and formats on the backend thread. The two paths have
  different performance profiles, and neither has been measured.

**What is needed.** A specification of what to measure, how, and against what baseline.

### First: the question behind `QUIL-8` is wrong

`QUIL-8` reads: *"`emit()` hard-codes `<true>` for the immediate-flush template parameter
(`quill_logger.cpp:117`). Should the module path flush on every message, or match quill's macro-free
default?"*

**It does not flush on every message, and it already matches quill's default.** Reading quill
13.1.0's headers settles it without a measurement:

- **`<true>` does not mean "flush every message".** It means *"honour the per-logger immediate-flush
  threshold"* (`quill/Logger.h:945-952`). `_flush_after_log_statement_if_needed` loads the
  threshold and **returns immediately if it is 0** (`Logger.h:995-999`).
- **The threshold is 0 by default** - `std::atomic<uint32_t> _message_flush_threshold{0}`
  (`quill/core/LoggerBase.h:221`) - and it is only set by `set_immediate_flush()`
  (`LoggerBase.h:168-171`), which the project **never calls** (no `set_immediate_flush`,
  `flush_every_n_messages` or `set_flush_interval` anywhere in `src/`, `include/` or `modules/`).
- **Quill's own default is the same value.** `LogMacros.h:129-132` defines
  `QUILL_ENABLE_IMMEDIATE_FLUSH 1`, and the macro path passes exactly that
  (`LogMacros.h:407`, `:1040`).

So the module path's `<true>` is **one relaxed atomic load and a predictable branch** - the same
branch quill's own macros take. **There is no decision to make here.** `QUIL-8` should be reworded
from *"a measurement, not a guess"* to *"already settled by reading the headers"*, and the benchmark
below is not for it.

**But the same reading turns up something the audit missed, and it is a performance defect.**
Quill's macro path calls `should_log_statement<log_level>()` **before** queueing
(`LogMacros.h:404`). The project's runtime-metadata path does **not** - `emit()` calls
`log_statement_runtime_metadata` directly (`quill_logger.cpp:117`), and that function never
consults the level (`Logger.h:427-476`). So the module path **queues every message, including the
ones the level would filter out.** That is DEF-1 again, but seen as a cost: **the module path's
producer cost is independent of the configured level**, while quill's own path gets cheaper as the
level rises. A benchmark that measures both at two levels would put a number on that.

### The metrics

Six metrics, each with a definition. A benchmark that does not state what it measures produces
numbers nobody can compare.

| # | Metric | Definition | Why it is here |
|---|---|---|---|
| M1 | **producer ns/message** | wall-clock time the *calling thread* spends inside the log call, divided by the message count | what the application's thread pays - the number the module path actually changes |
| M2 | **producer p50 / p99** | the per-message distribution of that time, not the mean | a mean hides the tail, and the tail is what a user notices |
| M3 | **allocations/message** | heap-allocation calls attributable to the producer thread, per message | the module path's `std::string` copy is the project's only per-message allocation |
| M4 | **end-to-end p50 / p99** | enqueue → written to the sink | the user-visible latency of a log line |
| M5 | **drain time** | after the producer stops, the time until the last message is in the sink | the backlog the producer built |
| M6 | **throughput** | messages/second, producer-limited | the ceiling |

**M1-M3 are the producer's; M4-M5 are the logger's.** They have to be reported separately, because
they move in opposite directions when the work moves between the threads - and that is exactly
what the module path does.

### The baseline ladder

Five baselines, each isolating one layer. **Without the ladder a single number says nothing about
where the time goes.**

| # | Baseline | What it isolates |
|---|---|---|
| **B0** | the empty loop, with the same clock reads | **the harness's own overhead** - the noise floor every other number sits on |
| **B1** | `format_message` into the 2,048-byte buffer, **no** `emit()` | the module's formatter cost, with nothing queued |
| **B2** | the module path's `log()`, end to end | the module path's producer cost |
| **B3** | `log_raw()` with a pre-formatted string | the queueing cost **without** formatting |
| **B4** | the catalog path's `CIB_INFO(...)` | the catalog path's producer cost |
| **B5** | quill's own `LOG_INFO(...)` macro | the reference implementation - the number to beat |

The differences are the findings:

- **B2 − B1** = what the queueing costs.
- **B2 − B3** = what the formatting costs (B3 also skips the `std::string` copy, so this is the
  formatter **plus** the copy).
- **B4 − B1** = what the module path adds over the catalog path, which is the decision `FMT-14`
  turns on.
- **B5 − B4** = what the catalog path costs over a plain quill user - the price of the catalog's
  compile-time identification.
- **B5 − B2** = the module path's total premium over quill's own path.

**B0 is not optional.** Without it, a "42 ns/message" number is uninterpretable.

### The variables

| Variable | Values | Why |
|---|---|---|
| compiler | `gcc16-release`, `p2996-release` | the two supported toolchains, and they differ (see the clock trap below) |
| level | `info` (primary), `trace` (secondary) | at `trace`, quill's macro path filters nothing either, so B5's cost rises; at `info` the difference appears |
| message length | 8 bytes, 64 bytes, 2,048 bytes | **8 bytes is below the small-string threshold on both libraries** (see below), 64 is above both, 2,048 is the formatter's truncation boundary |
| message count | 100,000 per repetition | enough to amortise the warm-up and to make the p99 meaningful |
| repetitions | 20 | enough for a stable tail; the harness reports the distribution across repetitions, not just one run |
| warm-up | 1,000 messages before measuring | lets the SPSC queue reach its steady-state size (128 KiB initially, `FrontendOptions.h:58`) and the thread-local context settle |
| sink | console redirected to `/dev/null` (default); `NullSink` if the seam is added | see "the sink" below |
| build | `CMAKE_BUILD_TYPE=Release`, `CPP_CORE_HARDENING=none`, **no sanitizer** | a sanitizer changes the cost by an order of magnitude and the numbers stop describing the shipped binary |

### The harness has three traps, and all three are real

**Trap 1 - `high_resolution_clock` is not the same clock on the two compilers.** This is the one
that would silently corrupt half the results.

| Library | `high_resolution_clock` | monotonic? |
|---|---|---|
| libc++ 21 | `typedef steady_clock high_resolution_clock` (`<chrono>:435`) | **yes** |
| libstdc++ 16 | `using high_resolution_clock = system_clock` (`bits/chrono.h:1294`) | **no** - it is the wall clock |

A harness written against `high_resolution_clock` would produce monotonic numbers on `p2996` and
wall-clock numbers on `gcc16`, and the wall-clock ones would show occasional negative or absurd
durations whenever the system clock is adjusted. **The harness must use `std::chrono::steady_clock`
on both.** (`steady_clock::is_steady` is `true` in libc++, `:430`.)

**Trap 2 - the per-message allocation is not one, and the threshold differs between the
libraries.** The audit says the module path "costs one heap allocation on the calling thread"
(`README.md:277`), and that is only true for messages **longer than the small-string threshold**:

| Library | small-string capacity | a message of *n* characters |
|---|---|---|
| libc++ 21 | **22** (`__min_cap = (sizeof(__long) - 1)`, `string:834`, `:896`) | ≤ 22 → the `std::string` lives on the stack → **0** heap allocations |
| libstdc++ 16 | **15** (`_S_local_capacity`, `bits/basic_string.h:217`) | ≤ 15 → **0** heap allocations |

`emit()` constructs `std::string{message, length}` (`quill_logger.cpp:118`), so a short message
never touches the heap - the bytes still get copied, into the small-string buffer, and then again
into the queue. So:

- **the allocation count is 0 or 1 per message depending on the message length**, and the crossover
  is at a *different* length on each compiler;
- the audit's README claim is **wrong for short messages**, and the benchmark is what would have
  found it.

**This means the benchmark's message length is not a cosmetic variable - it is the variable that
flips the allocation count**, and a single-length benchmark would report either "0 allocations" or
"1 allocation" and be true only for that length.

**Trap 3 - the producer's clock reads are not free.** Two `steady_clock::now()` calls per message
cost a `mach_absolute_time` each on macOS - tens of nanoseconds, which is the same order as the
thing being measured. So:

- the per-message timing must be **batched** (time a block of *N* messages, divide) and the
  per-message distribution must come from **many small batches**, not from one call per message;
- **B0 measures exactly this cost** and is subtracted from the reported numbers.

### The allocation counter

M3 needs a count of heap allocations on the producer thread. Three ways, and only one is
trustworthy:

| Way | Verdict |
|---|---|
| **`operator new` replacement, scoped to the producer thread** | **the recommendation.** Replacing the global `operator new`/`operator delete` in the benchmark TU is legal, needs no dependency, and the counter can check `std::this_thread::get_id()` so it only counts the *producer's* allocations - quill's backend thread allocates too, and those must not be counted |
| `malloc_zone_statistics` (macOS) | counts the whole process, not a thread, and is not portable to the other platform the project might use |
| ASan's `__sanitizer_get_allocated_bytes()` | exact, but only under ASan - and ASan changes the timings, so it would have to be a **second, separate run** |

The counter must be **enabled only during the measured region**, and the harness must subtract the
count taken over the equivalent idle region, because quill's own setup allocates outside the
producer's control.

### The sink: the one structural blocker

**The project's sink is hard-wired.** `quill_logger()` creates a `quill::ConsoleSink` and a logger
named `"cpp-core"` (`quill_logger.cpp:83-91`), once, in a function-local static. `create_or_get_logger`
**returns the existing logger** for a duplicate name, so a benchmark cannot create a second logger
with a different sink - and `setup()` takes no arguments, so the module path cannot be pointed
elsewhere.

A benchmark that logs to the console measures **the terminal**, not the logger: the write to a tty
costs microseconds and varies with whether stdout is a tty at all. Two ways out:

| Shape | What it needs | What it measures |
|---|---|---|
| **S1 - redirect stdout** | **nothing.** `dup2` fd 1 onto `/dev/null` before the first log call - the pattern `tests/logging_test.cpp:26-43` already uses | producer cost **plus** the backend's real work (formatting the pattern, the `fwrite`) minus the terminal's cost |
| **S2 - a `NullSink`** | **a source change**: a seam so the benchmark's logger gets a `quill::NullSink` (`quill/sinks/NullSink.h`, header-only, its `write_log` is an inline no-op) | the producer cost **alone** |

**The recommendation is S1 for the first benchmark**, because it needs no source change and the
backend's work is part of what the user asked about. S2 is the better instrument for isolating the
producer, and it is a small change - but it is a source change, so it waits for the build lane.

Note that S1 has a subtlety: quill's `StreamSink` writes with `fwrite` to the `stdout` `FILE*`
(`quill/sinks/StreamSink.h:131`), so redirecting the *file descriptor* works, and the existing test
proves it does.

### Two more things the harness needs, and one it must not do

- **The catalog path needs the catalog.** `CIB_INFO(...)` goes through `catalog<Message>()`
  (`cib_quill.hpp:139`), so the benchmark target must link `cpp-core-catalog`, exactly as
  `cpp-core-tests` does (`tests/CMakeLists.txt:12`).
- **The module path must be imported, not included.** `import com.rsm.logging;` at the top of the
  benchmark TU, and the target links `cpp-core::logging` - the same shape as
  `tests/logging_test.cpp:9`. `log()` is a template, so it is instantiated in the benchmark TU and
  measured as the consumer sees it.
- **The harness must not use `ut`.** `ut` is a test framework; it has no timing, no repetition and
  no percentile support. It would be a harness written from scratch on top of a test framework.
- **The harness must not be part of the test suite.** It is a separate target, excluded from
  `ctest`, and run through its own preset.

### The framework choice

Both candidates are **already in the vcpkg registry at the pinned baseline**, so neither needs an
overlay port:

| Candidate | Version at the baseline | What it gives | What it costs |
|---|---|---|---|
| **`benchmark`** (google) | **1.9.5** | `->Percentile(0.99)` out of the box; `benchmark::MemoryManager` for allocations-per-iteration; ns/op and items/s; a documented warm-up and repetition model | a real dependency in `vcpkg.json`; a heavier build |
| **`nanobench`** | **4.6.0** | single header; fast; ns/op with a median | its library API has no first-class percentile reporting and no allocation counter |

**The recommendation is `benchmark`.** The two things the specification demands that a hand-rolled
harness gets wrong are the **percentiles** and the **warm-up/repetition model** - and
re-implementing those correctly is exactly the kind of work that produces numbers that look
plausible and are not comparable. Adding a dependency to `vcpkg.json` is a small decision for the
owner; the recommendation is to make it.

### What the numbers would decide

| The number | settles |
|---|---|
| B2 − B4 | the module path's premium over the catalog path - the strongest input to **`FMT-14`** |
| M3 at 8 / 64 / 2,048 bytes | how often the module path touches the heap, and **that the README's "one heap allocation per message" is wrong for short messages** |
| B2 at `trace` vs `info` | the cost that **DEF-1** leaves on the table, since the module path queues messages that quill's own path would filter |
| B5 − B2 | the module path's total premium over a plain quill user - the number a consumer would compare against |
| M4 / M5 | whether the producer and the backend are balanced, and whether the `UnboundedBlocking` queue is hiding a backlog |
| B2 − B1 vs B2 − B3 | whether the cost is in the formatter or in the queueing - which decides whether `FMT-14`'s answer (c) is worth the Codec experiment |

### And the one thing the benchmark cannot settle

**The end-to-end latency (M4) needs the sink's write to be observable**, which means the sink has
to timestamp each message - and the project's pattern has no timestamp field
(`quill_logger.cpp:33-35` has `%(time)`, but that is the *logger's* timestamp, taken when the
backend processes the message, not when the producer called `log()`). So M4 is only measurable with
a **custom sink** that records the enqueue time alongside the write - a third source change, and a
bigger one than S2. **The recommendation is to defer M4 and M5** until the producer cost (M1-M3) is
measured; they are the second-order question, and the first-order one does not need them.

---

## 5. A differential test between the two logging paths

**The question.** Part 13 found fifteen differences (D1-D15) between the module path's format
dialect and the catalog path's, by **reading** two implementations. Nothing keeps them in sync.

**The evidence, before the research.**

The two dialects are structurally different: fmt cannot enter the module interface, so the module
has its own scanner and parser (`modules/logging/format.hpp`), while the catalog path uses quill's
bundled fmt. Two of the differences change output today:

| call | module path | catalog path | the standard |
|---|---|---|---|
| `info("{:>06}", 42)` | `000042` | `    42` | `    42` |
| `info("{}", 1234567.0)` | `1.23457e+06` | `1234567` | `1234567` |

and one is not a formatting difference at all: the module **never validates the format
specification**, so `info("{:s}", 42)` compiles and is silently ignored (DEF-5).

**What is needed.** A test design that formats the same input through both paths and compares -
which would make the finding permanent instead of historical, and is the test that would fail if
`FMT-14` is answered (c).

### The first question: what would the test actually observe?

**Not the formatter.** Both paths end at the same sink, and the sink is between the formatter and
anything the test can see. The project's sink is a `quill::ConsoleSink` on stdout, and its pattern
is fixed (`quill_logger.cpp:33-35`):

```
%(time) [%(thread_id)] %(short_source_location:<28) LOG_%(log_level:<9) %(logger:<12) [%(tags)] %(message)
```

So the test observes **formatter + sink**, and three things sit between the formatter and the
observation:

| Confound | What it does | How the design handles it |
|---|---|---|
| the **multi-line split** | quill formats **each line of a multi-line message separately, with the full prefix** (`quill/backend/PatternFormatter.h:128-160`). A message containing a real newline becomes several prefixed lines | the case list avoids real newlines in the *expected* output, and D15's case is handled explicitly (below) |
| the **2,048-byte buffer** | the module path truncates silently at the buffer's capacity (`format.hpp:163-165`); the catalog path does not | every case's payload stays well under 2,048 bytes, so the buffer is not part of any comparison |
| the **pattern's field widths** | `%(short_source_location:<28)` and `%(logger:<12)` are padded | the test extracts only the payload, so the widths do not matter - but the *extraction rule* does depend on the pattern's shape, and the test must assert that shape |

**The honest consequence: this is a test of the two paths as the user sees them, not a test of the
two formatters.** That is the right level for a *differential* test - the user sees the sink - but
it means the expectations are "what the sink prints", and any change to the pattern changes them.
**The test must therefore assert the pattern's shape as well as the payloads**, so a pattern change
fails loudly instead of silently mis-extracting.

### The case list: four of the fifteen cannot be tested this way

This is the first hard result, and it is not obvious until the compile-time behaviour is taken
into account.

| # | The format string | the argument | the standard / fmt | the module path | testable? |
|---|---|---|---|---|---|
| **D1** | `"{:s}"` | `42` (an `int`) | **a compile-time error** | compiles, and prints `42` | **no** - the catalog path does not compile |
| **D2** | `"{:>06}"` | `42` | `"    42"` | `"000042"` | **yes** |
| **D3** | `"{}"` | `1234567.0` | `"1234567"` | `"1.23457e+06"` | **yes** |
| **D4** | `"{:f}"` | `3.5` | `"3.500000"` | `"3.5"` | **yes** |
| **D5** | `"{:+}"` | `3.5` | `"+3.5"` | `"3.5"` | **yes** |
| **D6** | `"{:#g}"` | `3.0` | `"3.00000"` | `"3"` | **yes** |
| **D7** | `"{:L}"` | `1234` | `"1,234"` (fmt's locale form) | `"1234"` | **yes**, but it needs fmt's locale feature enabled - otherwise fmt's answer is `"1234"` too and the case says nothing |
| **D8** | `"{:{}}"` | - | valid | **a compile-time error** | **no** - the module path does not compile |
| **D9** | `"{0} {0}"` | `"first"` | valid | **a compile-time error** | **no** - the module path does not compile |
| **D10** | `"{:B}"` | `42` | `"101010"` | `"42"` | **yes** |
| **D11** | `"{:c}"` | `65` | `"A"` | `"65"` | **yes** |
| **D12** | `"{:d}"` | `'x'` | `"120"` | `"x"` | **yes** |
| **D13** | `"{:#o}"` | `0` | `"0"` | `"00"` | **yes** |
| **D14** | `"{:d.3}"` | `42` | **a compile-time error** | `"42"` | **no** - the catalog path does not compile |
| **D15** | `"{:?}"` | `"a\n"` | `"a\\n"` | `"a"` + a real newline | **yes**, with a caveat (below) |

**Eleven of the fifteen are testable as a runtime differential comparison.** The other four are
**asymmetric compile-time rejections**, and a runtime test cannot compare two programs when one of
them does not compile.

**The four need a different mechanism entirely: a "must not compile" test.** The project has none.
CMake's `try_compile` returns a boolean, but it cannot `import com.rsm.logging;` - the module has
to be built first, and the import path is CMake-internal. The workable route is a ctest fixture
that reads the compile command out of `compile_commands.json` (the project already generates it,
`cmake/presets/cpp-core.json`), substitutes the source file, runs the compiler and asserts that it
**fails**. That is a build-system change, so it waits for the build lane - but **the four cases are
the most important ones** (D1 is the difference between a checked and an unchecked format string),
and a design that quietly drops them would be a design that drops the point.

**D15's caveat.** The module path's output is `"a"` followed by a **real** newline, and quill's
multi-line handling turns that into a second prefixed line - and then **drops the empty tail**,
because the loop ends when `start == log_msg.size()` (`PatternFormatter.h:133-159`). So the module
path's sink output for D15 is the single line `... a`, and the trailing newline never reaches the
sink at all. That is a *sink* behaviour, not a formatter behaviour, and the expectation must say
so - otherwise the test looks like it is testing the formatter when it is testing the sink.

### The oracle: three columns, and the rule that keeps it honest

Every case needs three answers, not two:

| Column | Where it comes from | What it is for |
|---|---|---|
| **the standard** | [format.string.std](https://eel.is/c++draft/format.string) and Table 104-110 | the **normative** answer - what the dialect is supposed to produce |
| **the catalog path** | fmt 12.2.1, running | the implementation under test, on the other path |
| **the module path** | the module's formatter, running | the implementation under test, on this path |

**The rule: the expected values are written from the standard, not copied from the
implementation.** If the module's expected value is copied from what the module prints today, the
test freezes the bug and calls it a specification. So for each case the table records what the
standard says, and the module's value is compared against it - which means **the module's column
starts out as a list of failures**, and the test has two possible shapes.

### The two modes, and what decides between them

| Mode | The assertion | When it applies |
|---|---|---|
| **A - divergence characterisation** | `module == <the module's current value>` **and** `catalog == <the standard's value>` | **today**, while `FMT-14` is undecided |
| **B - agreement** | `module == catalog` **and** `catalog == <the standard's value>` | after `FMT-14` is answered (b) or (c) |

**Mode A is the default, and it is not a compromise.** It says: *"the module path prints `000042`
here and the catalog path prints `    42`, and that is what both of them do today."* That makes the
divergence **permanent and visible** instead of historical - which is exactly what part 13 asked
for - and it turns any change to either formatter into a test failure that names the case.

**Mode B is what `FMT-14` (b) or (c) buys**, and it is the test that would fail if the fix is
incomplete. The switch is one line in the case table: a column that says *"agree"* or *"diverge"*.

**And the cases where the module is wrong (D3, D4, and the ones step 5 of the plan fixes) are
already labelled.** Step 5 replaces `snprintf` with fmt in `format_double`
(`quill_logger.cpp:121-167`), which changes the module path's float output - so D3 and D4 stop
being divergences at all, and the case table's expectation for them changes from *"diverge"* to
*"agree"*. **The table is the place where the plan's steps and the test meet**, and it should be
edited when each step lands.

### The harness

The shape is a macro, because each case has a different argument *type*, and the same arguments
have to go to both paths.

```cpp
// One case. The format string is a literal, because both paths require a compile-time one:
// the module's format_string constructor is consteval, and cib's is a ct_string.
#define DIFFERENTIAL_CASE(ID, FORMAT, MODULE_TEXT, CATALOG_TEXT, ...)                  \
  do {                                                                                 \
    stdout_capture capture;                                                            \
    expect(capture.ok()) << "could not capture stdout";                                \
    com::rsm::logging::info(FORMAT, __VA_ARGS__);                                      \
    CIB_INFO(FORMAT, __VA_ARGS__);                                                     \
    com::rsm::logging::flush();                                                        \
    auto const output = capture.contents();                                            \
    /* extract the two payloads and compare them with the two expectations */           \
  } while (false)
```

Three things about that sketch that the design has to get right.

**The arguments are expanded twice**, once per path. For the case list's literals that is
harmless, but it is a trap: **the arguments must be side-effect-free**, and the macro should say
so.

**The extraction needs a sentinel.** The pattern's last field is the message, but the prefix
contains two bracketed groups - `[%(thread_id)]` and `[%(tags)]` - and the *tags* differ between
the paths (the module path sends `""`, `quill_logger.cpp:117`; the catalog path sends
`"cpp_core id=N mod=M"`, `cib_quill.hpp:147-148`). So the payload is **everything after the second
`]`** on the line - which works, but couples the test to the pattern's shape.

The robust version is a **sentinel in the format string**: the case's format string is prefixed
with a token that contains no `]`, say `"#D02# {:>06}"`, and the test finds the sentinel and takes
what follows it. The sentinel is part of the format string, so it becomes part of the message
text and therefore part of the catalog ID - which is harmless, and the reason for the next section.

**The extraction must assert the pattern's shape.** The test should count the `]` before the
payload and require exactly two, and fail with a clear message if the pattern changes. Otherwise a
pattern change turns every case into a false pass or a false failure, silently.

### The catalog: the differential test triggers DEF-6

**This is the one part of the design with a consequence outside the test.**

The catalog path's message is identified by `catalog<Message>()`
(`cib_quill.hpp:139`), and the catalog is built from the **undefined symbols** of the object
libraries that log (`cmake/catalog.cmake:17-20`). The test's object library is already one of
them:

```cmake
set(cpp_core_catalog_inputs cpp-core-app)
if(TARGET cpp-core-test-code)
  list(APPEND cpp_core_catalog_inputs cpp-core-test-code)
endif()
```

So the differential test's `CIB_INFO` calls would go into **the application's catalog** - and the
catalog's IDs are the **rank in text order** (`gen_str_catalog.py:228-229`, `Message.__lt__`),
assigned fresh on every run because the build passes no `STABLE_JSON`
(`cmake/catalog.cmake:22-39`; the mechanism is in `string_catalog.cmake:16`, `:85` and
`gen_str_catalog.py:307-337`, `:492-506`). **Adding the test's messages would renumber the
application's messages.** That is **DEF-6**, triggered by a test.

Two ways out:

| Shape | What it does | Cost |
|---|---|---|
| **C1 - a separate catalog for the test** | a second `gen_str_catalog` call with its own `CLIENT_NAME`, its own output and its own object library; the test executable links the test catalog instead of the application one | a second catalog invocation in `cmake/catalog.cmake`, and the test's object library must be removed from the application catalog's inputs |
| **C2 - use the stable-ID mechanism** | pass the previous catalog as `STABLE_JSON`, so existing messages keep their IDs and new ones take the free ones | this is **BUILD-7 option (a)**, and it does not keep the test's messages *out* of the application's catalog - it only stops them from renumbering the application's messages |

**C1 is the right shape**, because the application's catalog is deployment collateral
(`catalog-ids.md`) and the test's messages are not part of the application. **C2 is worth doing
anyway** - it is the fix for DEF-6, it is one line plus a committed file, and it is `BUILD-7` - but
it does not replace C1.

**The generated file supports C1.** The catalog's entries are explicit template specialisations
keyed by the message's exact type (`cpp-core-catalog.cpp`: `template<> auto catalog<sc::message<...>>()`),
so two catalogs can coexist as long as their message types differ - and the test's and the
application's do.

### One thing nobody has compiled

**The differential test needs a translation unit that does both: `import com.rsm.logging;` *and*
`#include <cpp-core/logging/cib_quill.hpp>`.** No such translation unit exists today:

- `tests/logging_test.cpp` imports the module and includes `<cstdio>`, `<string>` and `<unistd.h>`
  - but **not** `cib_quill.hpp`;
- `src/app.cpp` includes `cib_quill.hpp` - but does **not** import the module;
- `src/main.cpp` imports the module - and includes nothing.

`cib_quill.hpp` pulls in `<string>`, `<string_view>`, `<type_traits>`, `<cstdint>`, `<utility>`,
quill's headers, cib's `<log/log.hpp>` and `<stdx/*>` (`cib_quill.hpp:24-40`).

**And the audit's own matrix says that on GCC 16 this may not compile**: the row *"the module
exports no std types, importer + `#include <cstdio>`"* is marked **fails** on GCC 16.2
(`import-std.md:206`). The project's test file appears to contradict that - it does exactly that
and builds - so either the matrix's row describes a different configuration or the two cases differ
in some way the audit did not isolate.

**Either way this is the differential test's first open question, and it must be settled by a
compile before any of the test is written.** The question is precise:

> Does a translation unit that imports `com.rsm.logging` and then includes
> `cpp-core/logging/cib_quill.hpp` compile on GCC 16 and on clang-p2996?

If it does not, the differential test needs a **different shape**: the two paths in **separate**
translation units, with the comparison done by the test process over the captured output. That is
strictly more work - the two paths cannot share a macro - but it is a fallback that works.

### What the test would protect

| The test protects | From |
|---|---|
| the two paths' dialects | a change to either formatter that is not a decision - the mode-A expectations fail and name the case |
| the plan's step 5 | when `format_double` moves to fmt, D3 and D4's expectations change from *"diverge"* to *"agree"*, and the table has to be edited - which is the point |
| `FMT-14` | the moment the owner answers (b) or (c), the table's mode flips and the test becomes the acceptance criterion |
| the **application's** catalog | C1 keeps the test's messages out of the deployment collateral, and C2 stops them renumbering it |
| a future third path | the case table is the specification of the dialect; a new path is checked against it |

**And it is not a coverage substitute.** The differential test exercises **one** format string per
case - eleven of them - while the formatter has **15 functions** and the audit's coverage inventory
(`constexpr-and-fmt.md`) lists the branches that need covering. The differential test is the
*oracle* for the formatter's behaviour; the coverage work still has to write the branch tests.
The two are complementary, and the differential test is the one that tells the branch tests **what
the right answer is**.

---

## 6. Costing the `import std;` option

**The question.** Part 4 compared the standard's text with both compilers' behaviour. It never
asked the decision-relevant question: **if `import std;` worked on GCC too, what would change?**

**The evidence, before the research.**

The audit's keep / replace / defer table has twenty rows, and row 18 is the whole
standard-library-free module rule - the audit calls it "the one real decision". Eight other rows
are marked "replace if the module may use the standard library" or "shrink". But nobody has
enumerated *which* rows flip, *what the work* is, or *what the payoff* is - and the payoff is what
makes the case.

**What is needed.** A row-by-row flip analysis, a work estimate, and a payoff statement.

### The first thing to fix: the table asks the wrong question

The table's rows are phrased conditionally - *"replace **if the module may use the standard
library**"* - which is the right condition, but it hides three different outcomes under one
verdict. **"The module may use the standard library" can mean three things**, and they have very
different prices:

| | What it means | What it costs |
|---|---|---|
| **B** | the module's *interface* names `std::` types - so `import std;` | the importer migration, the CMake gate, and the GCC question |
| **B'** | the module's *implementation* names `std::` types - so the formatting moves behind `internal.hpp` | the type-erasure problem (**QUIL-1**) - **no modules work at all** |
| **C** | the module names `fmt::` types - so fmt's own module is imported | a new overlay port, and fmt's global module fragment |

**B' is the one the audit already recommends** (`import-std.md:300-315`: "keep the module's
*interface* standard-library-free ... and put the standard-library-dependent work behind
`include/cpp-core/logging/internal.hpp`"), and it needs **no `import std;` at all** - because
`src/logging/quill_logger.cpp` is a plain translation unit and may use the standard library
freely today. **That is the single most important fact in this section**, and the table's phrasing
hides it.

### The row-by-row flip analysis

Twenty rows. Here is what each one does under the condition "the module may use the standard
library", with the evidence for each verdict.

| # | The hand-rolled thing | Flips? | The new verdict, and why |
|---|---|---|---|
| 1 | the type traits (`format.hpp:20-107`) | **yes, cleanly** | `std::remove_cvref_t` and the rest. 88 lines go. The blocker was never the traits - it was only the standard-library-free rule |
| 2 | `convertible_to` (`format.hpp:109-113`) | **yes, cleanly** | `std::convertible_to`. 5 lines go |
| 3 | `forward` (`format.hpp:126-136`) | **yes, cleanly** | `std::forward`. 11 lines go |
| 4 | `message_buffer` (the 2,048-byte stack buffer, `format.hpp:154-210`) | **no** | `std::inplace_vector<char, 2048>` is **not available on libc++ 21** - there is no `<inplace_vector>` in the include tree at all, not merely a missing macro. libstdc++ 16 has it. Two compilers must keep working, so **57 lines stay** |
| 5 | `scan_format` + `format_matches` (the consteval scanner, `format.hpp:220-298`) | **only with rows 7-9** | The scanner is the module's *dialect*. It stays unless the module stops doing its own formatting. But its **reason** changes: Intel's `stdx` is still ruled out (it pulls in the standard library), and `std::format_string` becomes available as the validation mechanism - which is row 19, and which is only correct **together with** rows 7-9 (below) |
| 6 | `format_integer` (`format.hpp:329-422`, plus `digit_char` at `:323-327`) | **yes, cleanly** | `std::to_chars` **is** `constexpr` in both implementations: libstdc++ 16 `<charconv>:126,166,212,235,288,324`, libc++ 21 `<charconv>:34` (P2291R3). 99 lines go |
| 7 | `format_value` (the per-type dispatch, `format.hpp:424-467`) | **yes, but lossily** | `std::formatter<T>` is the standard's extension point - but the renderer behind it, `std::format_to`, is **not `constexpr`** in either implementation on this machine (no `constexpr` on `format_to` or `format_to_n` in libstdc++ 16's `<format>` or libc++ 21's `<format>`). Taking this row **destroys the constexpr formatter** |
| 8 | `parse_spec` (the runtime spec parser, `format.hpp:477-515`) | **yes, but lossily** | same: `std::format_to` parses the spec, and it is not `constexpr` |
| 9 | `format_message` (the field loop, `format.hpp:532-602`) | **yes, but lossily** | same |
| 10 | `format_double` (`snprintf` with `%g`, `quill_logger.cpp:121-167`) | **no** | It is **already** in a plain translation unit that may use the standard library, so the replacement (fmt) is reachable **today**, with no modules work. The row was already "replace" |
| 11 | `to_quill_level` / `from_quill_level` | **no** | The two mappings cannot be merged: **MIPI Sys-T's 0 is the most severe level and the module's 0 is the least severe**, so they point in opposite directions. `import std;` gives no shared enum. The row's "shrink" verdict **does not flip** |
| 12 | `decay_enum_value` (`cib_quill.hpp:53-61`) | **no** | `std::to_underlying` is already available - that header is not standard-library-free. The row was already "replace" |
| 13 | the cib tag string (`cib_quill.hpp:143-149`) | **no** | same - and it needs `"fmt"` in `vcpkg.json`, which is plan step 2, not a modules change |
| 14 | `stdx::ct_conversions::type_as_string` | **no** | reflection still cannot do it (no constexpr allocation) |
| 15 | the `CIB_*` macros | **no** | unchanged |
| 16 | the `__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION` default arguments (`logging.cppm:67-69`, `:104-105`) | **partly** | The **module** half becomes `std::source_location::current()`. The **cib** half is already free to use it - that header is not standard-library-free. This is the only payoff that does not depend on the formatter's fate |
| 17 | the source-location capture itself | **no** | already macro-free; `std::source_location` is the same idiom |
| 18 | the standard-library-free module rule | **the decision** | see below |
| 19 | the `format_string` class's compile-time check (`logging.cppm:64-84`) | **yes, cleanly - but not on its own** | `std::basic_format_string<char, Types...>`'s constructor is `consteval` and validates the specification against the class's **type** parameters (libstdc++ 16 `<format>:168-186`, the definition at `:5430`). So DEF-5 goes away. **But see the package rule below** |
| 20 | `std::meta::nonstatic_data_members_of` | **no** | already the C++26 facility |

**The tally.**

| Outcome | Rows |
|---|---|
| flip cleanly | **1, 2, 3, 6, 19** (five) |
| flip partly | **16** (one) |
| flip lossily | **7, 8, 9** (three) |
| flip only in combination | **5** (one) |
| do not flip | **4, 10, 11, 12, 13, 14, 15, 17, 20** (nine) |
| the decision itself | **18** (one) |

**Five rows flip cleanly, and only one of the five (row 16) is worth anything on its own.**

### The package rule: rows 19 and 7-9 are not separable

This is the sharpest result, and it corrects the audit's table.

**Row 19 on its own is a defect.** `std::basic_format_string` validates the specification against
the **standard's** grammar and the argument's type. If the module keeps its own runtime formatter
(row 5 stays, rows 7-9 do not flip), the module would then **validate with one grammar and format
with another**. The example is D2:

```cpp
com::rsm::logging::info("{:>06}", 42);
```

`std::basic_format_string` accepts it - the syntax is valid, and `42` is formattable as an
integer. The standard's meaning is *right-align in a width of 6*, so `std::format` gives
`"    42"`. The module's renderer gives `"000042"` - it treats the `0` as zero-padding and ignores
the alignment. So the module would **accept a specification whose meaning it does not implement**,
and the compile-time check would certify it.

**That is a worse failure than DEF-5**, because the check would be *there* and *wrong* rather than
absent. DEF-5 is "the module never validates"; this would be "the module validates against a
grammar it does not implement".

**So the rule is: either the module uses the standard's validator *and* the standard's renderer,
or it uses neither.** Rows 19 and 7-9 are one decision, and the audit's table lists them as two.

**And the same rule applies to fmt.** fmt 12.2.1 implements the C++26 format-spec grammar, so a
fmt-based validator and a fmt-based renderer agree with each other - but fmt's `fmt::format` is
**not** `constexpr` either, unless the compile-time API is used (`FMT_COMPILE` /
`FMT_STATIC_FORMAT`, `fmt/compile.h`). So the fmt route has the same shape: the validator and the
renderer must come from the same library.

### Three outcomes, three prices

| | **A - the module keeps its own formatter** | **B - the module uses the standard's** | **C - the module uses fmt's** |
|---|---|---|---|
| **rows that flip** | 1, 2, 3, 6, 16 | 1, 2, 3, 6, 7, 8, 9, 16, 19 | 7, 8, 9, 16, 19 (to fmt) |
| **how** | `import std;` in the purview, **the module's scanner stays** | `import std;` + `std::format_to` | `import fmt;` |
| **`format.hpp`** | 603 -> **~400 lines** | 603 -> **~120-150 lines** | 603 -> **~120-150 lines** |
| **the dialect** | the module's own - **DEF-4 stays** | the standard's - DEF-4's structural cause goes | fmt's (the standard's grammar) - same |
| **DEF-5** | **goes** (row 19) - but see the package rule | **goes** | **goes** |
| **constexpr formatting** | **kept** | **LOST** - `std::format_to` is not `constexpr` in either implementation | **kept**, if the compile-time API is used |
| **the `static_assert` formatter tests** (item 1, Route B) | **kept** | **destroyed** | **kept** |
| **the GCC migration** | yes | yes | maybe (see the `FMT_IMPORT_STD` switch) |
| **the CMake gate** | yes | yes | no |

**Outcome A is the interesting one.** It is the only outcome where the module keeps its
`constexpr` formatter *and* its `static_assert` tests *and* gets the traits and `std::to_chars`
from the standard library. But it keeps the module's own dialect, so **DEF-4 stays** - and, worse,
row 19 turns the missing validation into a *wrong* validation unless the module also drops the
standard's validator. So **A is only coherent without row 19**: `import std;` for the traits and
`std::to_chars`, the module's own scanner, and the module's own dialect.

And then A buys 203 lines for the whole GCC migration and the experimental CMake gate. **That is a
bad trade, and it is the reason the recommendation below is not "adopt `import std;`".**

### The fmt module: the option the audit never considered

**fmt 12.2.1 ships a C++20 module.** Upstream's `src/fmt.cc` is:

```cpp
module;
#define FMT_MODULE
#ifndef FMT_IMPORT_STD
#  include <algorithm>
#  include <bitset>
...
#endif
export module fmt;
#ifdef FMT_IMPORT_STD
import std;
#endif
```

and upstream's `CMakeLists.txt` has `option(FMT_MODULE "Build a module library." ${FMT_USE_CMAKE_MODULES})`,
where `FMT_USE_CMAKE_MODULES` is TRUE only if CMake >= 3.28, `CMAKE_CXX_STANDARD >= 20`, Ninja
>= 1.11, and GCC >= 15 / Clang >= 16 / MSVC >= 1934 (`CMakeLists.txt:55-86`).

**The project's own environment clears every one of those gates**: CMake 4.4.5, Ninja 1.13.2, GCC
16.2.0, clang-p2996 21.0.0git, and `CMAKE_CXX_STANDARD 26` (`cmake/toolchains/cpp-core.cmake:70-72`).

**But the vcpkg port at the pinned baseline does not build it.** The baseline's `ports/fmt`
portfile passes only three options - `-DFMT_CMAKE_DIR`, `-DFMT_TEST=OFF`, `-DFMT_DOC=OFF` - and
does **not** set `CMAKE_CXX_STANDARD`, so `FMT_USE_CMAKE_MODULES` is FALSE and `FMT_MODULE`
defaults to FALSE. The installed tree confirms it: fmt 12.2.1 (`FMT_VERSION 120201`), **no module
interface, no BMI, no `.cppm`**.

**So Outcome C needs an overlay port for fmt** - and the project already has the mechanism and the
pattern: five overlay ports under `ports/`, each a `vcpkg.json` plus a `portfile.cmake`, with a
`REF` and a `HEAD_REF`. The port would pass `-DFMT_MODULE=ON` and `-DCMAKE_CXX_STANDARD=20`.

**And the `FMT_IMPORT_STD` switch is the same decision again, in miniature.** With it, fmt's
module does `import std;` - which works on clang-p2996 and is subject to the GCC question below.
Without it, fmt's module textually includes the standard headers into its **global module
fragment** - one copy - which is the same coupling the project's own module avoids, and the same
collision risk the `logging.cppm:9-19` comment describes. **There is no setting of
`FMT_IMPORT_STD` that is free of the question.**

One more cost for Outcome C: **the project would then have three copies of fmt in play** - quill's
bundled `fmtquill` (which VCPKG-1 answered is structural), the standalone fmt 12.2.1, and fmt's
module.

### The GCC question is not priced - and the matrix that priced it is not the project's configuration

This is the other sharp result, and it corrects the audit's cost model.

**The audit's GCC matrix says option (c) is blocked.** `import-std.md:295` - *"it is **blocked on
GCC 16 today** - any standard or system-header include in an importing translation unit fails"* -
and the matrix at `:201-206` shows three GCC 16 failures, including the last row: *"the module
exports no std types, importer + `#include <cstdio>`" -> **fails***.

**But the project's own GCC 16 build does exactly that row.** `tests/logging_test.cpp` imports the
module and includes `<cstdio>`, `<string>` and `<unistd.h>`; the module's interface exports no
standard-library types; and `build/gcc16-debug/tests/cpp-core-tests` exists. The project's GCC 16
build works.

**The two configurations differ in the dialect flag, and nobody noticed.**

| | The dialect | Where it comes from |
|---|---|---|
| the audit's matrix | `-fmodules` | `import-std.md:188` - *"`-fmodules` for GCC (not implied by `-std=c++26`)"* |
| **the project** | **`-fmodules-ts`** | `build/gcc16-debug/compile_commands.json`: `-std=c++26 -freflection -fmodules-ts -fmodule-mapper=...`. CMake 4.4.5's `Modules/Compiler/GNU-CXX.cmake` sets `CMAKE_CXX_MODULE_MAP_FLAG` to `-fmodules-ts` for GCC >= 14 |

The p2996 path has **no** modules flag at all on the command line - CMake's clang path uses the
response-file modmap - so clang is in the C++23 dialect either way.

**So the matrix does not price the project's configuration, and "blocked on GCC 16" is an
unverified claim for this project.** It is a question, not a finding. That is **MOD-11**, and it is
the one measurement that decides the price of option (c).

**What is *not* in doubt** is the finding that the matrix was right to reach for the standard
library-free rule in the first place, and that the rule is load-bearing in **some** dialect: the
audit's own `logging.cppm:9-19` comment quotes a **GCC** error -
`redefinition of 'constexpr bool std::__is_constant_evaluated()'` - and a **Clang** error with a
*different* shape (`type alias template redefinition with different types`). Two different
mechanisms, and `import-std.md:112-119` explains the clang one as a **merge deficiency** rather
than a textual copy. So the two compilers differ, and the project is currently in the
configuration where they happen to agree.

### The work estimate

Nothing here can be built or measured - the build lane is parked - so this is an estimate in
**files and shape**, with the measurement that decides each one named.

| # | The work | Files | Shape | Decided by |
|---|---|---|---|---|
| 1 | **settle the GCC dialect question** | 0 | one compile | the build lane (**MOD-11**) |
| 2 | the CMake `import std;` gate | `cmake/toolchains/cpp-core.cmake` | ~5 lines: the experimental UUID (or CMake >= 4.5) and `CMAKE_CXX_MODULE_STD ON` | nothing - but it is **version-specific** and the UUID has to be looked up per CMake |
| 3 | the module's purview | `modules/logging/logging.cppm` | ~3 lines: `import std;` after `export module` (it must sit there - [module.import]/1) | work 1 |
| 4 | **the importer migration** | `src/app.cpp`, `src/main.cpp`, `src/reflection_demo.cpp`, `tests/logging_test.cpp` | **every `#include` in four files reviewed.** They include quill's headers, cib's headers, `<unistd.h>` and the standard headers | work 1; and whether `<unistd.h>` survives the mix (**MOD-4**) |
| 5 | the formatter's replacement | `modules/logging/format.hpp` | 603 -> ~400 (Outcome A) or ~120-150 (Outcome B) | the outcome chosen |
| 6 | `format_string`'s replacement | `modules/logging/logging.cppm:64-84` | ~20 lines: hold a `std::basic_format_string<char, Types...>` instead of the hand-rolled check - **and only together with work 5** | the package rule |
| 7 | `std::source_location` | `modules/logging/logging.cppm:67-69`, `:104-105` | ~10 lines: the `__builtin_*` triple becomes one default argument | work 3 |
| 8 | the fmt overlay port (Outcome C only) | `ports/fmt/vcppkg.json`, `ports/fmt/portfile.cmake` | **two new files**, following the pattern of the five existing overlays; `-DFMT_MODULE=ON`, `-DCMAKE_CXX_STANDARD=20` | nothing |
| 9 | `"fmt"` in the manifest | `vcpkg.json` | 1 line | nothing - and it is **plan step 2** regardless, because rows 10 and 13 need it |

**The critical path is work 1.** Everything in column "Decided by" that says "work 1" is blocked
on it, and it is the cheapest of the nine - one compile.

**And the biggest single item is not a compile at all: work 4.** Four files, every include
reviewed, and the include set includes **third-party headers** (quill's, cib's, `ut`'s) that the
project does not control. The audit's open question 8 asks whether quill's, cib's and ut's headers
compile in a translation unit that imports `std` on clang-p2996 - and libc++'s own documentation
warns that *"Including headers after importing the `std` module **may fail**"*.

### The payoff

**What `import std;` uniquely buys.** This is the question the table's phrasing hides. Of the five
rows that flip cleanly, **four are reachable without `import std;` at all** - the traits, the
concept, `std::forward` and `std::to_chars` all live on the *implementation* side of the
`internal.hpp` boundary, and `src/logging/quill_logger.cpp` is a plain translation unit that may
use the standard library freely **today**.

So the *unique* payoff of `import std;` is:

| | what only `import std;` gives |
|---|---|
| **row 16** | `std::source_location::current()` in the module's default arguments - about **10 lines** and three `__builtin_*`s |
| **row 19** | the standard's own compile-time format-string validation, in the module's interface |

**And row 19 is only correct together with rows 7-9** (the package rule) - which the
implementation-side route (B') delivers *anyway*, because the implementation can use
`std::format_to` freely.

**So the honest payoff statement is:**

> `import std;` buys the module's interface the **standard's format-string grammar** - about 80
> lines of scanner and parser - and `std::source_location` - about 10 lines. Everything else it
> appears to buy is reachable behind `internal.hpp` with no modules work at all.

**And what it costs** is the four-file importer migration, the experimental CMake gate, the
loss of the `constexpr` formatter (Outcome B), the risk that the module's global module fragment
re-introduces the collision the standard-library-free rule exists to prevent, and a
**GCC-16 question that has not actually been asked in the project's configuration**.

**And what it does not buy at all**, even with everything working: `std::inplace_vector` (row 4 -
libc++ has none), the level-enum merge (row 11 - the two enums point in opposite directions), the
`format_double` fix (row 10 - already reachable), the cib tag string (row 13 - already reachable).

### The recommendation

**Do not adopt `import std;` now, and do not adopt it in the shape the audit's table implies.**

1. **Adopt B' - the implementation-side route - as the plan's step 7.** It gets the traits,
   `std::to_chars` and `std::format_to` **without any modules work**, and it is already the
   audit's recommendation (`import-std.md:300-315`). It depends on **QUIL-1** (the Codec
   experiment), which is the one open question that decides whether it is possible at all.
2. **Do not take row 19 without rows 7-9.** The package rule above is a **new** finding and it
   changes `FMT-14`'s option (b): validating with the standard's grammar while formatting with the
   module's own is *worse* than not validating at all.
3. **Do not adopt Outcome A.** `import std;` for 203 lines, with the module's dialect unchanged and
   DEF-4 still there, is the worst of the three.
4. **Keep the standard-library-free rule, but correct its reason.** The rule stays - it is what
   makes the two compilers work today - but `logging.cppm:9-19` and `internal.hpp:3-6` state the
   standard's rule wrongly (the global module fragment is **not** copied into every importer; it is
   *attached to the global module*, and the collisions are merge deficiencies - `import-std.md:112-119`
   has the full argument). That correction is worth making on its own: the comment currently
   teaches the wrong model.
5. **Measure MOD-11 before costing option (c) again.** The audit's blocker is unverified in the
   project's configuration, and it is one compile.

**And the fmt module (Outcome C) is the option worth keeping open.** It is the only route that
gives the standard's grammar **and** keeps the `constexpr` formatter **and** the `static_assert`
tests **and** does not require the importer migration. Its price is one overlay port - a shape the
project already has five of - plus the `FMT_IMPORT_STD` question, which is the same question one
level down.

---

## 7. Four smaller questions

**7.1 - Can another project consume a C++ module?** `BUILD-2` is an owner decision ("should
cpp-core be consumable outside this repository?"), and the technical shape - `install()`, an
export set, a module configuration file, and `find_package` support for `CXX_MODULES` - is
non-trivial and appears nowhere in the audit. Even if the answer is "not now", the shape should be
known before the API freezes.

**7.2 - What about MemorySanitizer?** The presets cover ASan (plus UBSan) and TSan. MSan is
absent. It needs an instrumented standard library, so the answer is probably "not on macOS" - but
that is a fact worth having rather than an assumption.

**7.3 - What is the supply-chain posture of `ut`?** It is a single-maintainer, header-only test
library, pinned to a commit through an overlay port, and `VCPKG-2` asks whether that overlay
shadows a builtin vcpkg port. No risk assessment exists.

**7.4 - Is quill 13.1.0 still the right backend?** The audit never asks. It examined quill's
headers to answer specific questions, not to ask whether the dependency should stay. Now that fmt
is the formatter and the module path does its own formatting, the hybrid is worth a look.

### 7.1 - Can another project consume a C++ module?

**The state, first.** There is **not one `install()` call and no `export()` set** in any of the
project's CMake files, so another project cannot `find_package(cpp-core)` and cannot import the
module. (A correction while checking: `BUILD-2` says *"any of the five `CMakeLists.txt` files"* -
there are **four**: `CMakeLists.txt`, `modules/CMakeLists.txt`, `modules/logging/CMakeLists.txt`,
`tests/CMakeLists.txt`. The number does not change the answer, but the file should be right.)

**What CMake requires.** Three things, and the middle one is the one that is easy to miss:

| # | What | Since |
|---|---|---|
| 1 | `install(TARGETS cpp-core-logging EXPORT ... FILE_SET CXX_MODULES DESTINATION ...)` - installs the module's **source**, not a binary | 3.23 (file sets), 3.28 (`CXX_MODULES`) |
| 2 | `install(EXPORT cpp-core-targets ... CXX_MODULES_DIRECTORY ...)` | **3.28** |
| 3 | the consumer calls `find_package(cpp-core CONFIG REQUIRED)` and links `cpp-core::logging` | 3.28 for the module import to work at all |

The middle one is not optional. CMake's own words: *"without this information, **none of the C++
modules which are part of the targets in the export set will support being imported in consuming
targets**"*. A `cpp-core-config.cmake` without a `CXX_MODULES_DIRECTORY` would install the static
library, the headers and the target - and the consumer's `import com.rsm.logging;` would fail.

**And the project-specific obstacles, which are the interesting part.**

| # | The obstacle | Why it matters |
|---|---|---|
| **A** | **`format.hpp` is a textual dependency of the module's interface unit, but it is a `PRIVATE` source** | `logging.cppm:33` does `#include "format.hpp"` **in the module's purview**, and `modules/logging/CMakeLists.txt:19` lists `format.hpp` under `PRIVATE`. A consumer that rebuilds the module from source **needs that file installed and on the include path**. So the module's *private* implementation is a **public build-time dependency** of the installed module - and `PRIVATE` says it is not |
| **B** | **`internal.hpp` is in the global module fragment** | `logging.cppm:28` does `#include <cpp-core/logging/internal.hpp>` before `export module`. It is also a textual dependency. It lives under `include/cpp-core/logging/` and is published by `target_include_directories(... PUBLIC ...)`, but it is **not in a file set**, so an install would have to add it as one |
| **C** | **the target's public link closure** | `modules/logging/CMakeLists.txt:23` links `PUBLIC intel::cib quill::quill`. The exported config must `find_dependency(intel-cib)` and `find_dependency(quill)` - so the **consumer** must have those ports, at the same triplet, with the same `intel-cib` **overlay** port. Publishing the module publishes the whole dependency closure |
| **D** | **the catalog is separable - good** | `cpp-core-catalog` is a separate target, and the test executable links it explicitly (`tests/CMakeLists.txt:12`), so the module's consumers would not be forced to carry the string catalog |
| **E** | **a BMI is compiler- and flag-specific** | `CXX_MODULES_BMI` would install a prebuilt module interface - but the BMI embeds the `-std=c++26 -freflection` flags and the module mapper, so the consumer's flags have to match. **CMake's default is source-based** (the consumer rebuilds the module), which is the right choice here, and it is what makes obstacles A and B load-bearing |

**The verdict.** It is **doable**, and the shape is about **six lines of CMake plus two file-set
decisions** - but it publishes the dependency closure and freezes the API. So `BUILD-2`'s
recommendation to defer stands, and now there is a reason for it that is more concrete than
"the API is still moving": **the install set has to include a file the project currently calls
private**, and that is a decision about the module's structure, not about its packaging.

### 7.2 - What about MemorySanitizer?

**The answer is no, and there are two independent blockers - so this is not an open question.**

| | The blocker | The evidence |
|---|---|---|
| **1** | **GCC 16 does not implement MSan at all** | GCC 16's `-fsanitize=` options are: address, thread, hwaddress, memtag, kernel, pointer, shadow, leak, undefined, shift, integer, unreachable, vla, null, return, signed, bounds, alignment, object, float, nonnull, returns, bool, enum, vptr, builtin, all. **There is no `memory`** |
| **2** | **clang's MSan does not support macOS** | Clang's own documentation: *"MemorySanitizer is supported on the following OS: **Linux, NetBSD, FreeBSD**"*. macOS is not among them |
| **3** | **and it would need an instrumented C++ standard library** | the installed libc++ 21 snapshot has **no MSan support at all** - no `__msan` directory in the include tree, and not one "MemorySanitizer" mention anywhere in it. Clang's doc notes that MSan "makes it possible to run MemorySanitizer-instrumented programs linked with **uninstrumented libc**" - the C library, not the C++ one |

**So the preset table is complete as it stands.** `cc-asan` and `cc-tsan` cover the two sanitizers
that can run here, and the missing one is missing for a structural reason, not an oversight. The
project's preset file already says the same thing about TSan on GCC ("GCC 16 has no TSan runtime on
macOS") - MSan is the same story one step further.

**And the loss is small.** MSan detects uninitialised reads; the project has no report of one, and
the leak question - the one the sanitizers *can* answer here - is already covered by
[docs/asan-leak-check/README.md](../../docs/asan-leak-check/README.md). **This question is
answered.**

### 7.3 - What is the supply-chain posture of `ut`?

**The facts, all checked against the upstream and the installed tree.**

| | |
|---|---|
| **licence** | MIT (1,065-byte LICENSE) |
| **the whole dependency** | **419 lines**, in one header |
| **contributors** | **two** - `stephenberry` (106 commits) and `DockedFerret800` (17) |
| **reach** | 12 stars, 4 forks, 4 watchers, 3 open issues |
| **history** | created 2024-05-15; **v1.2.1 released 2026-07-31**; last push 2026-09-01 |
| **the overlay's `REF`** | `dc65567be78febd265ca36c324e1c504512d4d74` - **upstream's `v1.2.1` tag, exactly** |
| **the overlay's download pin** | a **SHA512** (`e02212527bc75...`) in the `vcpkg_from_github` call |
| **the installed tree** | **byte-identical** to upstream at the pinned SHA: `ut.hpp` sha256 `a13d227884641d2b871076f576abcc27ce8bc90b8163f248916bb2fdfeb12604`, matching upstream's `include/ut/ut.hpp` at that SHA |
| **the vendored copy in the repo** | also byte-identical: `ut.ixx` `1e6f3d40...`, `CMakeLists.txt` `bd631a84...` |
| **the vcpkg registry** | **no `ut` port** - not at the pinned baseline **and not on `master` today**. The overlay shadows nothing, and `VCPKG-2`'s answer holds against the current registry, not just the pinned one |

**What that assessment says.**

- **The mitigations are already in place, and they are the right ones.** An immutable **released
  tag** rather than a branch tip; a **SHA512** on the download; a **hash-verified installed tree**
  (verified above, not assumed); and **419 lines** of code as the entire blast radius.
- **The bus factor is one.** One maintainer holds 86% of the commits, on a library that every
  build of this project links into its test binary.
- **The one dependency that does not follow the baseline.** Everything else in `vcpkg.json` is
  pinned by the `builtin-baseline` commit; `ut` is pinned by its overlay's `REF` instead, because
  the registry does not have it. So **the baseline gives no protection for `ut`**, and a future
  bump is a manual act on the portfile. That is deliberate - there is no alternative - but it
  should be named.
- **There is no vcpkg security-audit pipeline for it.** vcpkg's audit tooling works on the
  registry's ports; an overlay port that has no registry counterpart gets none of it. The
  substitute is the SHA512, and it is a good one: a compromised upstream cannot get in without
  also changing the portfile.
- **The one loose end** is `HEAD_REF main` in the portfile. `HEAD_REF` is what `vcpkg` follows
  when it wants the newest commit, and it is **not** what the build uses - the build uses `REF`.
  But it is a standing invitation to bump `REF` to a branch tip. The recommendation is to bump
  only to a **tag**, and to change the `REF` and the `SHA512` **together** - they are one change.

**The verdict: the posture is good for 419 lines of a test framework, and it should stay as it
is.** No change is needed. The upstream has moved about five weeks past the pinned tag (last push
2026-09-01 against v1.2.1 on 2026-07-31), so a bump is *available* - but there is no reason to take
it, and taking it would mean re-verifying the SHA512 for no gain.

**One thing worth noting.** `ut` **has** a module variant (`modules/ut.ixx`), and the overlay
port's own comment says why it is not used: *"The module variant needs `import std`, which CMake
only supports behind an experimental gate, so this port ships the header-only form."* So the
dependency the project already has has already answered the `import std;` question for itself -
and the answer it chose is the same one the audit reached.

### 7.4 - Is quill 13.1.0 still the right backend?

**Is it current? Yes.** quill 13.1.0 was released **2026-10-17**, it is the latest release, and
the vcpkg registry's `quill` port is **13.1.0 at both the pinned baseline and `master` today**. The
project is 3,084 stars, 275 forks, 10 open issues, MIT, last push 2026-10-30.

**What the project actually uses of it.** Eight distinct symbols and nine header includes across
three files:

| The symbol | Used |
|---|---|
| `quill::LogLevel` | 32 times |
| `quill::MacroMetadata`, `quill::Logger` | 4 times each |
| `quill::Frontend` | twice |
| `quill::quill`, `quill::PatternFormatterOptions`, `quill::ConsoleSink`, `quill::Backend` | once each |

So the project uses quill for exactly four things: **a lock-free queue, a backend thread, a
pattern formatter and a console sink**.

**What quill offers that the project does not use** - thirteen sinks (File, RotatingFile, Json,
RotatingJson, Syslog, Systemd, Android, Stream, Null, ...), the `RdtscClock` /
`BackendTscClock` / `UserClockSource` clock sources, `SignalHandler`, `BacktraceStorage`,
`CsvWriter`, the `DeferredFormatCodec` / `DirectFormatCodec` /
`BinaryDataDeferredFormatCodec` family, `filters/`, `std/`, `HelperMacros`, `SimpleSetup`,
`ManualBackendWorker`, `BackendManager`, `BackendMdcState` and `BackendOptions`.

**Two of the unused pieces are the ones that matter to the project's own open questions.**

- **`quill::Codec<Arg>` is an open specialisation point** - `template <typename Arg, typename = void>
  struct Codec` (`quill/core/Codec.h:164-165`), with a documented contract (`:150-161`: the size
  computation may throw, the encode must not, and the decoders must consume their payload without
  throwing). **That is exactly the extension point `QUIL-1` is about** - a custom codec for the
  module's own argument-pack type that pushes *N* arguments from one pack element. So the
  mechanism the plan's last step depends on is a *supported* extension point, not a hack into
  quill's internals. That is a point in quill's favour, and it is a fact the audit did not record.
- **`quill::NullSink` exists** (`quill/sinks/NullSink.h`, header-only, its `write_log` is an inline
  no-op) - which is the **S2** shape from item 4's benchmark design. The benchmark's "isolate the
  producer" option needs a source change only to add the *seam*, not to add the sink.

**And one thing that is quill's cost.** quill **bundles its own fmt** (`quill/bundled/fmt`, in the
namespace `fmtquill`), so the project carries **two copies of fmt**: the bundled one and the
standalone 12.2.1 that arrives through `intel-cpp-std-extensions`. `VCPKG-1` answered that the
upstream quill port has **no fmt feature** and that quill 13.1.0's `CMakeLists.txt` has no fmt
switch among its 26 `option()` calls, so this is **structural**, not a configuration mistake.

**The alternatives, and why they lose.** Writing the queue and the backend by hand would be a few
hundred lines - and then the project would own the correctness of a lock-free queue, the backend's
shutdown protocol, the clock and the pattern formatter. quill supplies all of it, MIT-licensed and
maintained, and the project uses eight symbols of it. `spdlog` formats on the calling thread by
default and has no equivalent of quill's runtime-metadata path. `Boost.Log` is a much larger
dependency with a different model.

**The verdict: keep quill.** It is current, MIT, actively maintained, and the surface the project
uses is eight symbols against a library of three thousand stars.

**One observation worth recording.** The project uses quill for a *narrow* slice of it, and **the
narrowing is why the module path grew a hand-rolled formatter.** quill's own mechanism for
"queue something the backend will deal with" is `log_statement_runtime_metadata`, which the module
path already uses - but it takes a **pre-formatted** message plus runtime metadata, so the module
still has to format. The mechanism that would let the backend do the formatting is the codec
extension point, and that is `QUIL-1`. So the narrowness is not a quill deficiency; it is the
**one open question the plan's last step is waiting on**.

**And a correction to a plausible misreading.** quill's `TransitEvent` looks like it might be the
mechanism for sending structured data to the backend - it is quill's internal record type between
the frontend queue and the backend. But its payload is `std::variant<std::monostate,
std::atomic<bool>*, double>` (`quill/backend/TransitEvent.h:333`) - a flush flag and a metric
value. **It is not a user-facing extension point**, and it cannot carry the module's arguments.
`quill::Codec` is the extension point.

---

## 8. Re-validating the audit's time-sensitive claims

**The question.** The audit is a point-in-time document (2026-11-11/12). Which of its claims
decay, and what is their state now?

**The categories that decay.**

| What | Where | Decays how |
|---|---|---|
| the five overlay ports' upstream `REF`s | `ports/*/portfile.cmake` | upstream moves; the `REF` still points at *a* commit, but "the latest" stops being true |
| the upstream watch | part 14 | LLVM and LWG issues move; a blocker can close or a standard can ship |
| the tool versions | part 12 | clang-format / clang-tidy / cmake-format / gcov all move |
| the standard-library sweep | part 11 | libstdc++ and libc++ add features every release |
| the feature-test macro values | `FMT-13` | **needs the preprocessor** - parked |

**What is needed.** A re-validation pass, with anything that needs a compile left as a question.

---

## What was checked

- The **state table** (83 items, 13 / 0 / 70): parsed from the "settled by" column of every row of
  [open-items.md](open-items.md) plus its six defect headings. The 13 owner decisions match the
  thirteen headings in [decisions.md](decisions.md) exactly - none missing, none extra. The two
  registry items were removed from the open list when section 2 answered them, `QUIL-8` when
  section 4 did, and sections 5 and 6 added `FMT-15`, `MOD-10` and `MOD-11`.
- The **evidence quoted in each section** was read from the files it names.
- **Nothing was built, configured, run or regenerated.** Every claim is a restatement of a
  finding recorded in an earlier part, or a reading recorded here.
