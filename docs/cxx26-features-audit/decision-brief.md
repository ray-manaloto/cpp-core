# The owner's decisions, on one page

**Date:** 2026-11-12 (**one added 2026-11-13**: `BUILD-9`, from part 21)
**Status:** a brief, not a change. Nothing here is applied to the build.

**Fourteen decisions are waiting.** Four gate the implementation; ten shape it. This is part 17's
sheet - [decisions.md](decisions.md) - compressed to what can be read in one sitting, with what
the measurements have added since it was written ([measurements.md](measurements.md)),
and the one part 21 added ([cmake-feature-checks.md](cmake-feature-checks.md)).

**How to answer.** Every row below has an answer slot. Reply in this shape, and the answers get
recorded in `decisions.md`, in `open-items.md` and, where they move a number, in the acceptance bar:

```text
FMT-14: (a)
TOOL-13: JSON
TOOL-14: accept the sweep
```

"Accept all fourteen" is a valid answer. So is "all except FMT-14, where I choose (c)".

**STRONG** means the evidence decides it - there is a fact, and the answer follows from it.
**A JUDGEMENT CALL** means the evidence informs it - the answer is a preference, and the audit's
recommendation is one defensible reading of the same facts.

---

## The summary

| # | Decision | Gates | Recommendation | Strength | Your answer |
|---|---|---|---|---|---|
| **FMT-14** | the module path's format dialect | plan step 7 | **(c)** move formatting out of module interface (one fmtlib for both paths) | judgement | **(c)** — use fmtlib; single formatter for both paths; depends on QUIL-1 |
| **TOOL-13** | `.cmake-format.yaml` or `.cmake-format.json` | plan step 8 | **YAML** (add PyYAML via mise) | judgement | **YAML** — add PyYAML via mise; keep .cmake-format.yaml |
| **TOOL-14** | accept a one-shot `cmake-format -i` sweep? | plan step 8 | **accept the canonical layout** | judgement | **accept the sweep** — 9 of 12 files change; review diff |
| **BUILD-7** | where the stable catalog lives | **DEF-6** | **a committed file** (use CIB's stable ID mechanism) | **STRONG** | **(a)** — use CIB's stable ID mechanism per logging.adoc / binary_stable_ids |
| **BUILD-1** | what warning flags? | - | **all at once**: `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` | judgement | **all at once** — `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` |
| **BUILD-2** | consumable outside this repository? | - | **add install/export now** for current shape | judgement | **add install/export now** — FILE_SET CXX_MODULES + install(EXPORT CXX_MODULES_DIRECTORY) |
| **BUILD-3** | what is the public header surface? | - | **all three PRIVATE** — only the module is public | judgement | **all three PRIVATE** — only `import com.rsm.logging;` is public |
| **BUILD-4** | is `clang23` kept? | - | keep acceptance branch; add preset/triplet when Homebrew libc++ has `<meta>` | **STRONG** | **conditional** — add clang23 preset + triplet when Homebrew libc++ has `<meta>` |
| **BUILD-5** | should there be CI? | - | **no CI yet**; keep the gates local | **STRONG** | **no CI yet** — local presets (mise run audit:verify/measure/acceptance) |
| **BUILD-8** | check the catalog against the call sites? | - | **yes**, as part of the coverage work | judgement, and cheap | **yes** — small script, part of coverage work |
| **BUILD-9** | should the build gain a feature-check gate? | - | **(c)** - a check only where the answer gates a code path | judgement | **(c)** — check only where answer gates code path (HAVE_REFLECTION, module dialect, import std) |
| **QUIL-9** | what should the public `flush()` say? | - | **document in module header + README** | **STRONG** | **document in both** — two-line caveat on static destructor hazard |
| **ENV-2** | the abandoned `build/coverage-clang/` | - | **keep it (document why)** | judgement | **keep + document** — add README explaining it's abandoned and why |
| **ENV-3** | `ZAI_API_KEY` for the `zai-coding-plan` provider | - | **not a cpp-core decision** — defer to owner's agent setup | **STRONG** | **deferred** — not a cpp-core decision; owner's agent setup |

---

## The four that gate

### FMT-14 - what should the module path's format strings do?

**The question in one line.** The module path and the catalog path do not share a format-string
dialect, and the difference is structural - fmt cannot enter the module interface.

| | What it means | Cost |
|---|---|---|
| **(a) document** | write down the fifteen differences (D1-D15) and stop | one document |
| **(b) validate** | validate the format specification against the argument **types** | the scanner needs the type set; a real behaviour change - **and the renderer has to change with it** |
| **(c) move** | move the formatting out of the module interface, so one formatter serves both paths | the plan's last step; needs **QUIL-1** to succeed |

**Your answer: (c) — use fmtlib; single formatter for both paths; depends on QUIL-1.**

**What this means.** The hand-rolled formatter (492 lines, 51% of the library) is replaced by fmtlib.
Both module path and catalog path use the same fmtlib-based formatter. This unblocks step 7 of the
plan but **depends on QUIL-1** (can a quill Codec push N fields from one pack element?). If QUIL-1
fails, this path is dead and we fall back to (a) or (b).

**What the measurements added.** The hand-rolled formatter is **492 of the library's 967 lines of
code - 51% of it**. The acceptance bar's target is that share going **down**. The question is not
"is fmt better than a 492-line formatter" in the abstract; it is "is fmt better than **half the
project**". And **the two paths already disagree today**: `{:>06}` renders `000042` on the module
path and `42` on the catalog path, and `info("{:s}", 42)` compiles and is silently ignored
where `std::format` and fmt reject it - that is **DEF-5**.

**Full argument:** [decisions.md](decisions.md#fmt-14---what-should-the-module-paths-format-strings-do).

### TOOL-13 - `.cmake-format.yaml` or `.cmake-format.json`?

**The question in one line.** cmake-format accepts either; the YAML config **crashes** on this
machine because the pipx cmakelang 0.6.13 venv has no PyYAML, and the tool is not pinned in any
config either.

| | What it means | Cost |
|---|---|---|
| **JSON** | commit `.cmake-format.json` | the config is less pleasant to hand-edit |
| **YAML** | keep `.cmake-format.yaml` | the install must gain PyYAML **and** the install has to be pinned somewhere, or the tool is found by path |

**Your answer: YAML — add PyYAML via mise; keep .cmake-format.yaml.**

**What this means.** Install PyYAML in the mise environment (mise.toml), pin the cmakelang version,
and keep the existing .cmake-format.yaml config. The config stays human-readable with comments.

**Full argument:** [decisions.md](decisions.md#tool-13---cmake-formatyaml-or-cmake-formatjson).

### TOOL-14 - is a one-shot `cmake-format -i` sweep acceptable?

**The question in one line.** Running cmake-format over the tree changes **9 of the 12** CMake
files; the alternative is to encode the current hand-wrapping in the config.

| | What it means | Cost |
|---|---|---|
| **accept the sweep** | cmake-format's canonical layout becomes the project's layout | a 9-file diff to review |
| **keep the hand layout** | encode the current wrapping in `.cmake-format.*` | the config grows and fights the tool on every future file |

**Recommendation: accept the sweep.** **A judgement call.** The reason is the one that settled the
clang-format question in `42d35bb`: the project's configuration should describe the project, not
reconstruct a past hand-layout. **Measure the diff in review** - nine files, no behaviour change.

**Full argument:** [decisions.md](decisions.md#tool-14---is-a-one-shot-cmake-format--i-sweep-acceptable).

### BUILD-7 - where does the stable catalog live?

**The question in one line.** The catalog IDs are **not stable across releases** - the ID is a
message's rank among the messages in text order, so adding a message that sorts first renumbers
every message after it. The XML is **MIPI Sys-T deployment collateral**, where the IDs are wire
identifiers. The tool has the mechanism that prevents this; `cmake/catalog.cmake` does not use it,
so **every regeneration renumbers from scratch**.

| | What it means | Verdict |
|---|---|---|
| **(a) a committed file** | for example `cmake/catalog-stable.json` | **recommended** |
| **(b) the build tree** | `${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.json` | **does not work** - a clean build renumbers everything |
| **(c) leave it alone** | the IDs are a property of the current message set | defensible **only** if the XML is not consumed as deployment collateral |

**Your answer: (a) — use CIB's stable ID mechanism per logging.adoc / binary_stable_ids.**

**What this means.** The CIB tool already has a STABLE_JSON mechanism (`cmake/catalog.cmake` doesn't
use it). Follow the CIB docs: `logging.adoc` and the `binary_stable_ids` example. The stable file
(e.g., `cmake/catalog-stable.json`) is committed; IDs survive clean builds, branch switches, and
new machines. An ID change shows in a diff.

**What it gates:** **DEF-6**, and the catalog's use as deployment collateral.

**Full argument:** [decisions.md](decisions.md#build-7---where-does-the-stable-catalog-live).

---

## The ten that shape but do not gate

The plan's first six steps - the level-filter fix, the fmt manifest entry, the `constexpr` sweep,
the `static_assert` tests, `format_double` and the cib tag string - **need none of these**.

### BUILD-1 - what warning flags should the project use?

**There are none today** - not `-Wall`, not `-Wextra`, not `-Wpedantic`, not `-Wconversion`, not
`-Wshadow`. Adding warnings is a behavioural change: new diagnostics on code that compiles today.

**Your answer: all at once — `-Wall -Wextra -Wpedantic -Wconversion -Wshadow`.**

**What this means.** One sweep, one cleanup. All five flags enabled on both compilers from the
first implementation build. The noise is handled in a single pass. `-Wpedantic` on C++26
feature-test macros is known problematic but will be addressed directly.

**What the measurements added.** The library is **967 lines across 10 files** - small enough that
the full sweep is cheap, and the acceptance bar's *zero standard-library includes in the module
interface* is a rule a warning can help protect.

### BUILD-2 - should cpp-core be consumable outside this repository?

**Not today**: there is not one `install()` call and no `export()` set in any of the four
`CMakeLists.txt` files, so another project cannot `find_package(cpp-core)` and cannot import the
module.

**Your answer: add install/export now for current shape — FILE_SET CXX_MODULES + install(EXPORT CXX_MODULES_DIRECTORY).**

**What this means.** Add `install(TARGETS ... FILE_SET CXX_MODULES ...)` and
`install(EXPORT ... CXX_MODULES_DIRECTORY ...)` now, for the current API shape. Three obstacles
noted in Part 18 §7.1:

- `format.hpp` is PRIVATE but a **public build-time dependency** of the installed module
- `internal.hpp` is in the global module fragment, not in a file set
- The export publishes quill's and cib's whole closure

These are solved as part of the implementation. No consumer today, but the install rules force API
stability discipline earlier.

**Full argument:** [decisions.md](decisions.md#build-2---should-cpp-core-be-consumable-outside-this-repository).

### BUILD-3 - what is the public header surface?

All three headers in `include/cpp-core/logging/` are published by
`target_include_directories(... PUBLIC ...)`, and `quill_logger.hpp` includes `<quill/Logger.h>` -
**even though its own comment says it is "the implementation's business, not part of the module's
public interface"**. With no install rules there is no install-time boundary either, so "public"
is currently an accident.

**Your answer: all three PRIVATE — only `import com.rsm.logging;` is public.**

**What this means.** The module BMI (`import com.rsm.logging;`) is the **only** public interface.
All three headers (`internal.hpp`, `cib_quill.hpp`, `quill_logger.hpp`) become PRIVATE:

- `internal.hpp` — global module fragment, needed by importers via BMI
- `cib_quill.hpp` — catalog path API, reachable only through the module's implementation
- `quill_logger.hpp` — implementation detail (5 lines, 21 unread lines)

The install/export (BUILD-2) installs the module BMI + its BMI dependencies. Headers are not
installed. Consumers use `import com.rsm.logging;` only.

**What the measurements added.** `quill_logger.hpp` is **5 lines of code**, and the read-gap list
shows **all 21 of its source lines unread** at line granularity. A header nobody has read, whose
own comment says it is not public, is the clearest case for making the boundary explicit.

**Full argument:** [decisions.md](decisions.md#build-3---what-is-the-public-header-surface).

### BUILD-4 - is `clang23` kept?

The toolchain and `cmake/cpp-core-check.cmake` both accept it, with a full validation branch, but
there is **no `clang23` triplet and no `clang23` preset** - so it cannot be reached through the
supported path.

**Your answer: conditional — add clang23 preset + triplet when Homebrew libc++ has `<meta>`.**

**What this means.** The validation branch in `cmake/cpp-core-check.cmake` stays. The preset and
triplet are added **only when** Homebrew's libc++ gains `<meta>` support (so `src/reflection_demo.cpp`
can parse). Until then, no clang23 preset/triplet exists — it's not a supported configuration.
If clang-tidy needs a BMI, TOOL-3 measures whether the building compiler (GCC 16 or p2996) can
provide it.

**Full argument:** [decisions.md](decisions.md#build-4---is-clang23-kept).

### BUILD-5 - should there be CI?

There is **no `.github/` directory and no git remote**. The coverage gate, the format check and
the clang-tidy check therefore have **no home** until CI exists.

**Your answer: no CI yet — local presets (mise run audit:verify/measure/acceptance).**

**What this means.** No `.github/` directory, no workflow file. The gates are local commands
anyone can run: `mise run audit:verify`, `mise run audit:measure`, `mise run audit:acceptance`.
A workflow with no remote rots. Revisit when a remote exists; the design doesn't change, only
where it runs.

**What the measurements added.** The recommendation's "local, not CI" is now the status quo
rather than a plan: the three audit commands already police the repository's bookkeeping, its
metrics and its acceptance bar.

**Full argument:** [decisions.md](decisions.md#build-5---should-there-be-ci).

### BUILD-8 - should the build check the catalog's message set against the call sites?

The catalog tooling's input regex **drops a line that does not match**, and the message set is
deduplicated by a 64-bit hash, so a message can go missing from the catalog silently. The **link**
catches it - but only a build that links.

**Your answer: yes — small script, part of coverage work.**

**What this means.** A script counts catalog entries vs. `CIB_` call sites. Runs as part of the
coverage gate (100% rule). Turns "undefined symbol at link" into "message X missing from catalog".
Cheap, diagnostic, fits the 100% coverage rule.

**Full argument:** [decisions.md](decisions.md#build-8---should-the-build-check-the-catalogs-message-set-against-the-call-sites).

### BUILD-9 - should the build gain a feature-check gate?

**The question in one line.** Twenty of the audit's 30 `compile` questions are a CMake feature
check's shape (`check_cxx_source_compiles`, `try_compile`), so should the build ask them at
configure time?

| | What it means | Cost |
|---|---|---|
| **(a) a gate** | one check per compile-bearing item, on every preset | a configure that can fail on a compiler the project does not support; one-shot answers that go stale |
| **(b) no - on demand** | a scratch translation unit per item, when the lane reopens | nothing is re-measured; the answer stays a note |
| **(c) only what gates** | a check where the answer **branches the build**; a test for the rest | two mechanisms, and the split has to be argued once |

**Your answer: (c) — check only where answer gates code path (HAVE_REFLECTION, module dialect, import std).**

**What this means.** `check_cxx_source_compiles` / `try_compile` for gating checks only:
`HAVE_REFLECTION`, the module dialect capability, `import std` capability. The rest (facts about
the world) go to the coverage gate (100%) or tests. Confines the stale-answer problem to gating
checks — a stale gating check shows up as a missing code path.

**What part 21 added.** Two decisive measurements get a home: `FMT-13`'s preprocessor pass (probe
fails on purpose, `static_assert` message carries macro value, captured via `OUTPUT_VARIABLE`)
and `MOD-11`'s throwaway module (`try_compile` with `SOURCES_TYPE CXX_MODULE`, reproduces matrix
shape under project's `-fmodules-ts`).

**Full argument:** [cmake-feature-checks.md](cmake-feature-checks.md).

### QUIL-9 - what should the public `flush()` say?

`flush_log()` "blocks the calling thread until all log messages up to the current timestamp are
flushed" and carries quill's warning: *"Do not call this function from the destructor of a static
object. This may lead to application crashes..."*. The project's `com::rsm::logging::flush()` says
nothing about it, and a consumer cannot see quill's warning.

**Your answer: document in both — module header + README.**

**What this means.** Two-line caveat on `com::rsm::logging::flush()` in `logging.cppm:89` and in
the module's public header comment. Quill's warning: "Do not call from destructor of a static
object — may crash if ThreadContext destroyed first." No bug today (main() calls from main), but
consumer must know. Safe implementation would change sync→async contract — bigger than hazard
warrants.

**Full argument:** [decisions.md](decisions.md#quil-9---what-should-the-public-flush-say).

### ENV-2 - the abandoned `build/coverage-clang/`

An abandoned experiment (clang source-based coverage). The raw-profile version mismatch makes it
unusable - clang v10 against `llvm-profdata` 23.1.5's v11.

**Your answer: keep + document — add README explaining it's abandoned and why.**

**What this means.** The directory stays in the build tree (not tracked). Add a README in
`build/coverage-clang/` explaining: raw-profile version mismatch (clang v10 vs llvm-profdata
23.1.5 v11), experiment abandoned, kept as corroborating data point. All 9 build trees agree on
106-header closure; this is one of them. The cross-check is 8 trees without it — still exceeds
acceptance bar floor of 2.

**What the measurements added.** The abandoned tree is **one of the nine build trees** the closure
measurement reads, and all nine independently agree on the same 106-header closure. Keeping it
preserves the 9-tree corroboration.

**Full argument:** [decisions.md](decisions.md#env-2---the-abandoned-buildcoverage-clang).

### ENV-3 - `ZAI_API_KEY` for the `zai-coding-plan` provider

The two saved `.Z.AI` accounts belong to the `zai` integration, not to `zai-coding-plan`, so they
do not satisfy it.

**Your answer: deferred — not a cpp-core decision; owner's agent setup.**

**What this means.** This is the agent environment, not a cpp-core project decision. The two
saved Z.AI accounts belong to `zai` integration, not `zai-coding-plan`. Options (`opencode service
set env ZAI_API_KEY <key>` or `opencode auth login zai-coding-plan`) are handled by the owner
outside this project. Listed here only because it appeared in the original 13.

**Full argument:** [decisions.md](decisions.md#env-3---zai_api_key-for-the-zai-coding-plan-provider).

---

## One decision already made since the sheet

**Code coverage is 100%, always**, measured on the **`ut`** suite - the same unit testing library
glaze uses, and the one this project already writes its tests in. The acceptance bar carries it as
a floor of **1.0**, not a ratchet, and the tooling design already has it as
`CPP_CORE_COVERAGE_THRESHOLD`'s default. It means: every instrumented, non-excluded line of this
repository's library, application and module code is executed at least once by the coverage test
run - no more, no less. Not branch coverage, not vcpkg or system code, not the tests themselves,
and not `consteval` bodies whose only definition is compile time.

---

## What happens after you answer

**All 14 decisions are answered.** Every one of the plan's ten steps is unblocked.
The full step table is in [decisions.md](decisions.md#the-cheapest-path); the short version:

| Step | Needs |
|---|---|
| 1. Fix the level-filtering defect (**DEF-1**) + its test | nothing |
| 2. Add `"fmt"` to `vcpkg.json` | nothing - fmt 12.2.1 is already installed |
| 3. Mark the fifteen `format.hpp` functions `constexpr` | nothing - the compiler is the test |
| 4. Add the `static_assert` formatter tests | step 3 |
| 5. Replace `snprintf` with fmt in `format_double` | nothing - fixes DEF-2 and DEF-4 in both paths |
| 6. `fmt::format` for the cib tag string | nothing |
| 7. Move the formatting out of the module interface | **FMT-14 (c)**, and **QUIL-1** must succeed |
| 8. Wire the formatting and the checks into CMake | **TOOL-13 (YAML+PyYAML)**, **TOOL-14 (sweep)** |
| 9. The coverage gate | nothing - a separate track |
| 10. The `import std;` decision | nothing - the recommendation is to keep the status quo |

**FMT-14 is answered (c)** — step 7 is **unblocked but depends on QUIL-1**. If QUIL-1 succeeds,
the single fmtlib formatter replaces the hand-rolled one. If QUIL-1 fails, fall back to (a) or (b).

**One thing the answers will not do.** None of these fourteen changes the library's code today -
the build lane is parked, and the answers are recorded as decisions, not applied. What they do is
settle what the implementation *should* be, so that the day the lane reopens, the first build is
an implementation and not a re-litigation.

---

## Where the evidence is

| what | where |
|---|---|
| the full argument for each decision | [decisions.md](decisions.md) |
| every open item, with what settles it | [open-items.md](open-items.md) |
| the measurements this brief quotes | [measurements.md](measurements.md) |
| the acceptance bar these answers move | [acceptance.json](acceptance.json) |
| the registry, sliced | `mise run audit:summary -- --owner` |
| the bar, checked | `mise run audit:acceptance` |
