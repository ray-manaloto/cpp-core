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

The audit has **81 open items**, and they decompose exactly (verified by parsing the "settled by"
column of every row, plus the six defect headings):

| Kind | Count | What resolves it |
|---|---|---|
| Owner decisions | **13** | the owner's answer. Four of them gate the plan: `FMT-14`, `TOOL-13`, `TOOL-14`, `BUILD-7` |
| Compile / run / preprocessor | **68** | the build lane reopening - mechanical, not research |
| Registry read | **0** | `VCPKG-1` and `VCPKG-2` were answered by section 2 below - the registry at the pinned baseline turned out to be readable after all |

(It was 83 when this part opened; section 2 answered the two registry items and moved them to
`open-items.md` section 12.)

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
| 3 | The public API has no contract | ☐ **not started** | — |
| 4 | A benchmark harness | ☐ **not started** | — |
| 5 | A differential test between the two logging paths | ☐ **not started** | — |
| 6 | Costing the `import std;` option | ☐ **not started** | — |
| 7 | Four smaller questions | ☐ **not started** | — |
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

---

## 4. A benchmark harness

**The question.** `QUIL-8` asks whether the module path should flush on every message, and the
audit's own answer is *"a measurement, not a guess"*. There is nothing to measure with.

**The evidence, before the research.**

- The repository contains **no benchmark files at all** - no `bench*`, no harness, no baseline.
- The module path formats on the calling thread and copies the result into a `std::string`
  (documented in parts 13 and 14), so **every module-path message costs one heap allocation on
  the calling thread**.
- The catalog path queues the arguments and formats on the backend thread. The two paths have
  different performance profiles, and neither has been measured.

**What is needed.** A specification of what to measure, how, and against what baseline.

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

- The **state table** (81 items, 13 / 0 / 68): parsed from the "settled by" column of every row of
  [open-items.md](open-items.md) plus its six defect headings. The 13 owner decisions match the
  thirteen headings in [decisions.md](decisions.md) exactly - none missing, none extra. The two
  registry items were removed from the open list when section 2 answered them.
- The **evidence quoted in each section** was read from the files it names.
- **Nothing was built, configured, run or regenerated.** Every claim is a restatement of a
  finding recorded in an earlier part, or a reading recorded here.
