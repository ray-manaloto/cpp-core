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
| **FMT-14** | the module path's format dialect | plan step 7 | **(a)** document now, **(b)** if the API is public, **(c)** only if the Codec experiment works | judgement | |
| **TOOL-13** | `.cmake-format.yaml` or `.cmake-format.json` | plan step 8 | **JSON** | judgement, and YAML has a prerequisite | |
| **TOOL-14** | accept a one-shot `cmake-format -i` sweep? | plan step 8 | **accept the canonical layout** | judgement | |
| **BUILD-7** | where the stable catalog lives | **DEF-6** | **a committed file** | **STRONG** | |
| **BUILD-1** | what warning flags? | - | `-Wall -Wextra` now, measure the rest before adding it | judgement | |
| **BUILD-2** | consumable outside this repository? | - | **defer**, until the module's API stops moving | judgement | |
| **BUILD-3** | what is the public header surface? | - | make `quill_logger.hpp` private | judgement, strongly indicated | |
| **BUILD-4** | is `clang23` kept? | - | keep the acceptance branch, add no preset | **STRONG** | |
| **BUILD-5** | should there be CI? | - | **no CI yet**; keep the gates local | **STRONG** | |
| **BUILD-8** | check the catalog against the call sites? | - | **yes**, as part of the coverage work | judgement, and cheap | |
| **BUILD-9** | should the build gain a feature-check gate? | - | **(c)** - a check only where the answer gates a code path, a test for the rest | judgement, and it rests on what a check cannot see | |
| **QUIL-9** | what should the public `flush()` say? | - | **document the caveat** | **STRONG** | |
| **ENV-2** | the abandoned `build/coverage-clang/` | - | **delete it** | **STRONG** - and now measured | |
| **ENV-3** | `ZAI_API_KEY` for the `zai-coding-plan` provider | - | `opencode service set env` | **STRONG** - and not a cpp-core decision | |

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

**Recommendation: (a) now, (b) if the API is public, (c) only if the Codec experiment works.**
**A judgement call**, but a constrained one: (b) is only coherent if the module's *renderer* comes
from the same library as the validator. A check that is present and wrong is worse than no check.

**What the measurements added.** The hand-rolled formatter is **492 of the library's 967 lines of
code - 51% of it**. The acceptance bar's target is that share going **down**. The question is not
"is fmt better than a 492-line formatter" in the abstract; it is "is fmt better than **half the
project**". And **the two paths already disagree today**: `{:>06}` renders `000042` on the module
path and `    42` on the catalog path, and `info("{:s}", 42)` compiles and is silently ignored
where `std::format` and fmt reject it - that is **DEF-5**.

**If deferred:** the two paths keep disagreeing silently, and DEF-5 keeps shipping.

**Full argument:** [decisions.md](decisions.md#fmt-14---what-should-the-module-paths-format-strings-do).

### TOOL-13 - `.cmake-format.yaml` or `.cmake-format.json`?

**The question in one line.** cmake-format accepts either; the YAML config **crashes** on this
machine because the pipx cmakelang 0.6.13 venv has no PyYAML, and the tool is not pinned in any
config either.

| | What it means | Cost |
|---|---|---|
| **JSON** | commit `.cmake-format.json` | the config is less pleasant to hand-edit |
| **YAML** | keep `.cmake-format.yaml` | the install must gain PyYAML **and** the install has to be pinned somewhere, or the tool is found by path |

**Recommendation: JSON.** **A judgement call** - YAML is perfectly viable once PyYAML is installed
and pinned - but JSON is the smaller commitment, and the project has neither today. The config is
a machine-read format either way.

**Full argument:** [decisions.md](decisions.md#tool-13---cmake-formatyaml-or-cmake-formatjson).

### TOOL-14 - is a one-shot `cmake-format -i` sweep acceptable?

**The question in one line.** Running cmake-format over the tree changes **9 of the 12** CMake
files; the alternative is to encode the current hand-wrapping in the config.

| | What it means | Cost |
|---|---|---|
| **accept the sweep** | cmake-format's canonical layout becomes the project's layout | a 9-file diff to review |
| **keep the hand layout** | encode the current wrapping in `.cmake-format.*` | the config grows and fights the tool on every future file |

**Recommendation: accept the sweep.** **A judgement call.** The reason is the one that settled the
clang-format question in `61ba2da`: the project's configuration should describe the project, not
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

**Recommendation: (a). STRONG.** The deciding fact is that the IDs are *wire identifiers*. A wire
identifier that changes when a message is added is not an identifier.

**What it gates:** **DEF-6**, and the catalog's use as deployment collateral.

**Full argument:** [decisions.md](decisions.md#build-7---where-does-the-stable-catalog-live).

---

## The ten that shape but do not gate

The plan's first six steps - the level-filter fix, the fmt manifest entry, the `constexpr` sweep,
the `static_assert` tests, `format_double` and the cib tag string - **need none of these**.

### BUILD-1 - what warning flags should the project use?

**There are none today** - not `-Wall`, not `-Wextra`, not `-Wpedantic`, not `-Wconversion`, not
`-Wshadow`. Adding warnings is a behavioural change: new diagnostics on code that compiles today.

**Recommendation: `-Wall -Wextra` on both compilers, and measure the rest before adding it.**
**A judgement call.** The floor is conventional, cheap, and what a reviewer expects; the rest each
need real work, and `-Wpedantic` interacts with C++26 feature-test macros. Adding the floor now
and the rest later keeps the two changes separate, so the noise from each is readable on its own.

**What the measurements added.** The library is **967 lines across 10 files** - small enough that
the floor is a cheap sweep, and the acceptance bar's *zero standard-library includes in the module
interface* is a rule a warning can help protect.

### BUILD-2 - should cpp-core be consumable outside this repository?

**Not today**: there is not one `install()` call and no `export()` set in any of the four
`CMakeLists.txt` files, so another project cannot `find_package(cpp-core)` and cannot import the
module.

**Recommendation: defer, until the module's API has stopped moving.** **A judgement call.** The
API is still moving - **FMT-14** is undecided and the two paths' format dialects differ - so an
install/export set published now would encode decisions that are about to be revisited. There is
no consumer today, so nothing is blocked by deferring.

### BUILD-3 - what is the public header surface?

All three headers in `include/cpp-core/logging/` are published by
`target_include_directories(... PUBLIC ...)`, and `quill_logger.hpp` includes `<quill/Logger.h>` -
**even though its own comment says it is "the implementation's business, not part of the module's
public interface"**. With no install rules there is no install-time boundary either, so "public"
is currently an accident.

**Recommendation: make `quill_logger.hpp` private, and keep `internal.hpp` and `cib_quill.hpp` as
the public surface.** **A judgement call, strongly indicated** - the header's own comment already
says which side of the line it is on, and the build system has not caught up. This needs no
install rules and no export set.

**What the measurements added.** `quill_logger.hpp` is **5 lines of code**, and the read-gap list
the harness now prints shows **all 21 of its source lines unread** at line granularity. A header
nobody has read, whose own comment says it is not public, is the clearest case in the project for
making the boundary explicit.

### BUILD-4 - is `clang23` kept?

The toolchain and `cmake/cpp-core-check.cmake` both accept it, with a full validation branch, but
there is **no `clang23` triplet and no `clang23` preset** - so it cannot be reached through the
supported path.

**Recommendation: keep the acceptance branch, do not add a preset or a triplet.** **STRONG.** A
third compiler the project **cannot build** is not a supported configuration: Homebrew's libc++
has no `<meta>`, so `src/reflection_demo.cpp` cannot even be parsed. If clang-tidy turns out to
need a BMI, that need should be met by the compiler that can build the project - and that is
**TOOL-3**, a measurement, not a decision.

### BUILD-5 - should there be CI?

There is **no `.github/` directory and no git remote**. The coverage gate, the format check and
the clang-tidy check therefore have **no home** until CI exists.

**Recommendation: no CI yet; keep the gates as local presets.** **STRONG.** There is no remote, so
CI cannot run at all, and a workflow file with no remote is a file that only rots.

**What the measurements added.** The recommendation's "local, not CI" is now the status quo
rather than a plan: `mise run audit:verify`, `mise run audit:measure` and
`mise run audit:acceptance` are commands anyone can run, and they already police the repository's
bookkeeping, its metrics and its acceptance bar.

### BUILD-8 - should the build check the catalog's message set against the call sites?

The catalog tooling's input regex **drops a line that does not match**, and the message set is
deduplicated by a 64-bit hash, so a message can go missing from the catalog silently. The **link**
catches it - but only a build that links.

**Recommendation: yes, and as part of the coverage work.** **A judgement call, and cheap.** It
turns "the build failed to link" into "this message is missing from the catalog". Correctness
today does not depend on it; **diagnosis** does.

### BUILD-9 - should the build gain a feature-check gate?

**The question in one line.** Twenty of the audit's 30 `compile` questions are a CMake feature
check's shape (`check_cxx_source_compiles`, `try_compile`), so should the build ask them at
configure time?

| | What it means | Cost |
|---|---|---|
| **(a) a gate** | one check per compile-bearing item, on every preset | a configure that can fail on a compiler the project does not support; one-shot answers that go stale |
| **(b) no - on demand** | a scratch translation unit per item, when the lane reopens | nothing is re-measured; the answer stays a note |
| **(c) only what gates** | a check where the answer **branches the build**; a test for the rest | two mechanisms, and the split has to be argued once |

**Recommendation: (c).** **A judgement call**, and it rests on what a check cannot see. A check
**cannot import the project's module**, so `MOD-10`, `FMT-4` and `REFL-4` are outside its reach;
the project's **reflection flags do not reach a check** (they are a directory-scope directive in a
file `CMAKE_PROJECT_INCLUDE` never delivers to a try_compile project), so every `REFL-` check
carries `-freflection` by hand; and a check's answer is **cached for the life of the build tree**.
A cache variable is worth having when something branches on it - `HAVE_REFLECTION`, the module
dialect, an `import std` capability - and for the rest the answer is a fact about the world that
the coverage gate is already the place to assert, at 100%.

**What part 21 added.** The two decisive measurements this gives a home: `FMT-13`'s preprocessor
pass (a probe that fails on purpose, with the value in a `static_assert` message, captured through
`try_compile(... OUTPUT_VARIABLE ...)`) and `MOD-11`'s throwaway module (`try_compile` with
`SOURCES_TYPE CXX_MODULE`, which compiles a module unit and its importer under the project's own
`-fmodules-ts` dialect).

**Full argument:** [cmake-feature-checks.md](cmake-feature-checks.md).

### QUIL-9 - what should the public `flush()` say?

`flush_log()` "blocks the calling thread until all log messages up to the current timestamp are
flushed" and carries quill's warning: *"Do not call this function from the destructor of a static
object. This may lead to application crashes..."*. The project's `com::rsm::logging::flush()` says
nothing about it, and a consumer cannot see quill's warning.

**Recommendation: document the caveat in the public header.** **STRONG.** **There is no bug
today** - the project's own `main()` calls it from `main` - but the constraint has to be
documented. A safe implementation would change the contract from synchronous to asynchronous,
which is a bigger decision than the hazard warrants. The caveat is two lines of comment. The
function is `logging.cppm:89`.

### ENV-2 - the abandoned `build/coverage-clang/`

An abandoned experiment (clang source-based coverage). The raw-profile version mismatch makes it
unusable - clang v10 against `llvm-profdata` 23.1.5's v11.

**Recommendation: delete it.** **STRONG.** It is in the build tree, which is not tracked, so this
is housekeeping rather than a commit.

**What the measurements added - and this is the one thing to know before answering.** The
abandoned tree is **one of the nine build trees** the closure measurement reads, and all nine
independently agree on the same 106-header closure. Deleting it drops the cross-check from nine
trees to eight: still two compilers and five configurations, and the acceptance bar's floor of two
trees still holds. The coverage run itself was broken; the **include record** it left behind was
not, and it is corroborating the other eight.

### ENV-3 - `ZAI_API_KEY` for the `zai-coding-plan` provider

The two saved `.Z.AI` accounts belong to the `zai` integration, not to `zai-coding-plan`, so they
do not satisfy it.

**Recommendation: `opencode service set env`** - one command, and the restart is a background
service, not a session. **STRONG**, and **not a cpp-core decision** - it is the agent environment,
and it is listed here only because it is one of the fourteen.

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

**If you answer only the four gating decisions**, every one of the plan's ten steps is unblocked.
The full step table is in [decisions.md](decisions.md#the-cheapest-path); the short version:

| Step | Needs |
|---|---|
| 1. Fix the level-filtering defect (**DEF-1**) + its test | nothing |
| 2. Add `"fmt"` to `vcpkg.json` | nothing - fmt 12.2.1 is already installed |
| 3. Mark the fifteen `format.hpp` functions `constexpr` | nothing - the compiler is the test |
| 4. Add the `static_assert` formatter tests | step 3 |
| 5. Replace `snprintf` with fmt in `format_double` | nothing - fixes DEF-2 and DEF-4 in both paths |
| 6. `fmt::format` for the cib tag string | nothing |
| 7. Move the formatting out of the module interface | **FMT-14**, and **QUIL-1** must succeed |
| 8. Wire the formatting and the checks into CMake | **TOOL-13**, **TOOL-14** |
| 9. The coverage gate | nothing - a separate track |
| 10. The `import std;` decision | nothing - the recommendation is to keep the status quo |

**And if FMT-14 is answered (a)**, step 7 is **deferred rather than blocked**, and steps 1-6 and
8-10 proceed without it.

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
