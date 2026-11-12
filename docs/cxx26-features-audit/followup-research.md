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
| Compile / run / preprocessor | **68** | the build lane reopening - mechanical, not research |
| Registry read | **2** | `VCPKG-1` and `VCPKG-2`, blocked on a vcpkg registry checkout this machine does not have |

**The audit's own research is complete.** Seventeen parts, the upstream sources all vendored
(`upstream/`), the root README checked line by line (part 16), the owner decisions collected into
one sheet (part 17). Nothing is pending on the research lane except two items that wait on other
people: the registry checkout, and the commit identity (which waits on dotfiles-lead's fnox
profile).

So the 83 are **not** the backlog this part addresses. They are the existing plan's backlog.

## What the audit never asked

Reading the plan against the build files surfaced one defect and seven gaps. None of them is in
the 83, because the 83 are the audit's *questions about the code it was written to understand* -
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
| 1 | The `static_assert` formatter tests cannot reach the code they test | ☐ **not started** | — |
| 2 | Build reproducibility and upstream drift | ☐ **not started** | — |
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

**Three routes, and what each one actually proves.** To be worked through in this section.

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

- The **state table** (83 items, 13 / 2 / 68): parsed from the "settled by" column of every row of
  [open-items.md](open-items.md) plus its six defect headings. The 13 owner decisions match the
  thirteen headings in [decisions.md](decisions.md) exactly - none missing, none extra.
- The **evidence quoted in each section** was read from the files it names.
- **Nothing was built, configured, run or regenerated.** Every claim is a restatement of a
  finding recorded in an earlier part, or a reading recorded here.
