# The decisions the owner has to make

**Date:** 2026-11-12
**Status:** research. Nothing here is applied to the build.

The audit has **82 open items**. Sixty-nine of them are settled by a compile, a run or a
preprocessor pass - they are questions, not decisions, and they unblock the moment the build lane
reopens.

**Thirteen are decisions**, because the answer is a judgement about what the project should be, not
a fact about the world. They are scattered across `open-items.md`; this file gathers them into one
sheet, with a recommendation for each.

(Three further items - `VCPKG-1`, `VCPKG-2` and `QUIL-8` - were answered by part 18, sections 2
and 4, and are now in `open-items.md` section 12 rather than in the open list. The count was 83
until then; part 18, section 5 added `FMT-15` and `MOD-10` of its own.)

## The short version

**Four decisions gate the implementation. The rest shape it.**

| # | Decision | Gates | Recommendation |
|---|---|---|---|
| **FMT-14** | the module path's format dialect | plan step 7 (the big one) | (a) now, (b) if the API is public, (c) only if the Codec experiment works |
| **TOOL-13** | `.cmake-format.yaml` or `.cmake-format.json` | plan step 8 | **JSON** |
| **TOOL-14** | a one-shot `cmake-format -i` sweep? | plan step 8 | **accept the canonical layout** |
| **BUILD-7** | where the stable catalog lives | **DEF-6** | **a committed file** |

The other nine can be answered at any time, or left. The plan's first six steps - the level-filter
fix, the fmt manifest entry, the `constexpr` sweep, the `static_assert` tests, `format_double` and
the cib tag string - **need none of them**.

## The four that gate

### FMT-14 - what should the module path's format strings do?

**The question.** The module path and the catalog path do not share a format-string dialect, and
the difference is **structural**: fmt cannot enter the module interface, so the module's own
dialect stays as long as the module formats inside its own interface.

Two of the differences change output today:

| call | module path | catalog path | the standard |
|---|---|---|---|
| `info("{:>06}", 42)` | `000042` | `    42` | `    42` - the `0` is ignored when an alignment is given |
| `info("{}", 1234567.0)` | `1.23457e+06` | `1234567` | `1234567` - the shortest round-trip |

and one of them is not a formatting difference at all: the module **never validates the format
specification**, so `info("{:s}", 42)` compiles and is silently ignored, where `std::format` and
fmt reject it at compile time. That is **DEF-5**.

**The options.**

| | What it means | Cost |
|---|---|---|
| **(a) document** | write down the fifteen differences (D1-D15) and stop | one document |
| **(b) validate** | move the check from `format_matches<arg_count>` into `format_string`'s constructor, which knows the argument **types** | the scanner needs the type set; a real behaviour change |
| **(c) move** | move the formatting out of the module interface, so one formatter serves both paths | the plan's last step; needs **QUIL-1** to succeed |

**The recommendation: (a) now, (b) if the module's API is public, (c) only if the Codec experiment
works.** The reasoning is in part 13: (c) is the only option that makes the two paths *agree*, and
it is also the only one that needs a compile to know whether it is possible at all. Doing (c)
first, or without the Codec result, risks a rewrite on a guess. (a) costs nothing and is
prerequisite for reading (b) and (c) anyway.

**What it gates.** Plan step 7 - the only step that changes the module's design. Steps 3-6 make
the current design better whether or not (c) happens, so **steps 1-6 do not wait for this**.

**If deferred:** the two paths keep disagreeing silently, and DEF-5 keeps shipping.

---

### TOOL-13 - `.cmake-format.yaml` or `.cmake-format.json`?

**The question.** cmake-format accepts either. The **YAML** config **crashes** on this machine:
the pipx cmakelang 0.6.13 venv has no PyYAML, and the tool is not pinned in any config either -
the shims fail with "No version is set", so it has to be found by path or a project `.mise.toml`
added and trusted.

**The options.**

| | What it means | Cost |
|---|---|---|
| **JSON** | commit `.cmake-format.json` | the config is less pleasant to hand-edit |
| **YAML** | keep `.cmake-format.yaml` | the install must gain PyYAML (`mise use pipx:cmakelang[yaml]`) **and** the install has to be pinned somewhere, or the tool is found by path |

**The recommendation: JSON.** It is the smaller commitment: YAML needs a new dependency *and* a
pinning decision, and the project has neither today. The config is a machine-read format either
way - nobody hand-edits a line-width setting often enough to need YAML's readability.

**What it gates.** Plan step 8 (`cmake/format.cmake`).

---

### TOOL-14 - is a one-shot `cmake-format -i` sweep acceptable?

**The question.** Running cmake-format over the tree changes **9 of the 12** CMake files - the
project's own twelve: the four `CMakeLists.txt` and the eight in `cmake/` (the portfiles, the
triplets and the vendored `ut/CMakeLists.txt` are not in the set). The alternative is to keep the
current hand-wrapping and encode it as tool configuration (`always_wrap`, so `add_custom_target`
is never collapsed).

**The options.**

| | What it means | Cost |
|---|---|---|
| **accept the sweep** | cmake-format's canonical layout becomes the project's layout | a 9-file diff to review |
| **keep the hand layout** | encode the current wrapping in `.cmake-format.*` | the config grows and fights the tool on every future file |

**The recommendation: accept the sweep.** The reason is the same one that settled the clang-format
question in `61ba2da`: the project's configuration should describe the project, not reconstruct a
past hand-layout. The alternative is to spend the configuration budget encoding one file's
wrapping, and to keep doing it for every new file. **Measure the diff in review** - that is what
the audit says, and it is cheap: nine files, no behaviour change.

**What it gates.** Plan step 8, with TOOL-13.

---

### BUILD-7 - where does the stable catalog live?

**The question.** This is the decision **DEF-6** needs. The catalog IDs are **not stable across
releases**: the ID is a message's rank among the messages in text order, so adding a message that
sorts first renumbers every message after it. The XML is **MIPI Sys-T deployment collateral**,
where the IDs are the wire identifiers. The tool has the mechanism that prevents this -
`gen_str_catalog(STABLE_JSON ...)` -> `--stable_json` -> `read_stable` -> `assign_ids` - and
`cmake/catalog.cmake` does not use it. The flag reaches argparse with an empty list, so **every
regeneration renumbers from scratch**.

**The options.**

| | What it means | Verdict |
|---|---|---|
| **(a) a committed file** | for example `cmake/catalog-stable.json` | **recommended** - the IDs survive a clean tree, a branch switch and a new machine, and an ID change shows up in a diff |
| **(b) the build tree** | `${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.json` | **does not work** - a clean build renumbers everything, so it is the same defect with an extra step |
| **(c) leave it alone** | the IDs are a property of the current message set | defensible **only** if the XML is not consumed as deployment collateral |

**The recommendation: (a).** The deciding fact is that the IDs are *wire identifiers*. A wire
identifier that changes when a message is added is not an identifier.

**What it gates.** **DEF-6**, and the catalog's use as deployment collateral.

## The nine that shape but do not gate

### BUILD-1 - what warning flags should the project use?

**There are none today** - not `-Wall`, not `-Wextra`, not `-Wpedantic`, not `-Wconversion`, not
`-Wshadow`, in the toolchain or in any target. That is a gap next to a clang-tidy plan.

This is the owner's call because **adding warnings is a behavioural change**: new diagnostics on
code that compiles today.

**The recommendation: `-Wall -Wextra` on both compilers, and measure the rest before adding it.**
`-Wall -Wextra` are the conventional floor, they are cheap, and they are what a reviewer expects.
`-Wconversion`, `-Wshadow` and `-Wpedantic` are worth having but each is a source of diagnostics
that will need real work - and `-Wpedantic` interacts with C++26 feature-test macros. Adding the
floor now and the rest later keeps the two changes separate, so the noise from each is readable on
its own.

**Do it after the `constexpr` sweep (step 3) and before the clang-tidy work** - that way the
compiler's warnings and clang-tidy's checks do not arrive in the same diff.

### BUILD-2 - should cpp-core be consumable outside this repository?

**Not today**: there is not one `install()` call and no `export()` set in any of the five
`CMakeLists.txt` files, so another project cannot `find_package(cpp-core)` and cannot import the
module.

**The recommendation: defer, until the module's API has stopped moving.** The API is still moving
- **FMT-14** is undecided, and the two paths' format dialects differ. An install/export set
published now would encode decisions that are about to be revisited. There is also no consumer
today, so nothing is blocked by deferring.

(For the record: the project's own four `CMakeLists.txt` files contain no `install()` call and no
`export()` set - **verified**.)

### BUILD-3 - what is the public header surface?

All three headers in `include/cpp-core/logging/` are published by
`target_include_directories(... PUBLIC ...)`, and `quill_logger.hpp` includes `<quill/Logger.h>` -
**even though its own comment says it is "the implementation's business, not part of the module's
public interface"**. With no install rules there is no install-time boundary either, so "public"
is currently an accident.

**The recommendation: make `quill_logger.hpp` private, and keep `internal.hpp` and
`cib_quill.hpp` as the public surface.** The header's own comment already says which side of the
line it is on; the build system just has not caught up. This is the low-risk half of the decision -
it needs no install rules and no export set, and it can be done together with **BUILD-2** or
before it.

### BUILD-4 - is `clang23` kept?

The toolchain and `cmake/cpp-core-check.cmake` both accept it, with a full validation branch, but
there is **no `clang23` triplet and no `clang23` preset** - so it cannot be reached through the
supported path.

There is a real tension here: **part 3's clang-tidy design needs Homebrew clang 23** to build a
BMI with. But clang 23 **cannot build this project** - Homebrew's libc++ has no `<meta>`, and
`src/reflection_demo.cpp` cannot even be parsed without it - so the BMI it would build is of a
project it cannot compile.

**The recommendation: keep the acceptance branch, do not add a preset or a triplet.** A third
compiler the project cannot build is not a supported configuration, and adding a preset for it
would only make the failure louder and later. If clang-tidy turns out to need a BMI, that need
should be met by the compiler that can build the project - and the answer is recorded as **TOOL-3**,
which is a measurement, not a decision.

### BUILD-5 - should there be CI?

There is **no `.github/` directory and no git remote**. The coverage gate, the format check and the
clang-tidy check therefore have **no home** until CI exists - they would be local presets. This
also makes **TOOL-16** (what a CI runner provides) moot.

**The recommendation: no CI yet; keep the gates as local presets.** There is no remote, so CI
cannot run at all, and a workflow file with no remote is a file that only rots. The gates are
useful locally either way - a preset that a developer runs is worth more than a workflow that
nothing runs. Revisit when a remote exists; the design does not change, only where it runs.

### BUILD-8 - should the build check the catalog's message set against the call sites?

The catalog tooling's input regex (`gen_str_catalog.py:342`) **drops a line that does not match**,
and the message set is deduplicated by a 64-bit hash (`:212-213`, `:352`), so a message can go
missing from the catalog - silently, at the tool's level.

The **link** catches it, because the application's `catalog<...>` symbol would stay undefined - but
only a build that links. A dedicated check (the number of catalog entries against the number of
`CIB_` call sites) would catch it earlier and **name the message**.

**The recommendation: yes, and as part of the coverage work.** It is a small script, and it turns
"the build failed to link" into "this message is missing from the catalog". The link-time check is
sufficient for correctness today; this is about *diagnosis*.

### QUIL-9 - what should the public `flush()` say?

`flush_log()` "blocks the calling thread until all log messages up to the current timestamp are
flushed" (`quill/Logger.h:605`) and carries the warning "Do not call this function from the
destructor of a static object. This may lead to application crashes if the thread-local
ThreadContext is destroyed before the static object invoking `flush_log`" (`Logger.h:613`).

The project's `com::rsm::logging::flush()` (`logging.cppm:89`) **says nothing about it**, and a
consumer cannot see quill's warning. **There is no bug today** - the project's own `main()` calls
it from `main` (`src/main.cpp:15`) - but the constraint has to be documented, or `flush()` has to
be made safe.

**The recommendation: document the caveat in the public header.** A safe implementation would mean
deferring the flush to the backend thread, which changes the function's contract from "synchronous"
to "asynchronous" - that is a bigger decision than the hazard warrants. The caveat is two lines of
comment, and it is the constraint quill itself documents.

### ENV-2 - the abandoned `build/coverage-clang/`

An abandoned experiment (clang source-based coverage). The raw-profile version mismatch makes it
unusable - clang v10 against `llvm-profdata` 23.1.5's v11.

**The recommendation: delete it.** It is in the build tree, which is not tracked, so this is a
housekeeping act rather than a commit.

### ENV-3 - `ZAI_API_KEY` for the `zai-coding-plan` provider

The two saved `.Z.AI` accounts in `opencode auth list` belong to the `zai` integration (the
standard API), not to `zai-coding-plan`, so they do not satisfy it. Either
`opencode service set env ZAI_API_KEY <key>` (stops and restarts the background service) or
`opencode auth login zai-coding-plan` (a saved account, no restart). The local `opencode.json`
registers only `glm-4.7` for that provider; `glm-5.3` and `glm-5.3-flash` are in the catalog and
would have to be added.

**This is not a cpp-core decision** - it is the agent environment, and it is listed here only
because it is one of the thirteen. **The recommendation: `opencode service set env`** - it is one
command, and the restart is a background service, not a session.

## One that is *not* a decision - and is no longer open

**VCPKG-2** - "do the five overlay ports shadow builtin vcpkg ports?" - was in the list, but it is
**a research step, not a decision**: it is answered by reading the vcpkg registry at the pinned
baseline `245d37306671ea67d8f313081a81aae8079f8916`.

**It was believed to be blocked** because `$VCPKG_ROOT` here is the vcpkg *tool*, with no `ports`
tree and no `.git`. That is true of the local install and false of the registry: the registry is a
git repository and the baseline is a commit in it, so the reading is done over HTTP against that
commit, without a checkout. The same read answers **VCPKG-1** (does the upstream `quill` port
have an opt-in external-fmt feature?). **Both are now answered** - part 18, section 2, and
`open-items.md` section 12.

## The cheapest path

**If the owner answers only FMT-14, TOOL-13, TOOL-14 and BUILD-7**, then every one of the plan's
ten steps is unblocked:

| Step | Needs |
|---|---|
| 1. Fix the level-filtering defect (DEF-1) + its test | nothing |
| 2. Add `"fmt"` to `vcpkg.json` | nothing - fmt 12.2.1 is already installed |
| 3. Mark the fifteen `format.hpp` functions `constexpr` | nothing - the compiler is the test |
| 4. Add the `static_assert` formatter tests | step 3 |
| 5. Replace `snprintf` with fmt in `format_double` | nothing - fixes DEF-2 and DEF-4 in both paths |
| 6. `fmt::format` for the cib tag string | nothing |
| 7. Move the formatting out of the module interface | **FMT-14**, and QUIL-1 must succeed |
| 8. Wire the formatting and the checks into CMake | **TOOL-13**, **TOOL-14** |
| 9. The coverage gate | nothing - it is a separate track |
| 10. The `import std;` decision | nothing - the recommendation is to keep the status quo |

And if **FMT-14** is answered **(a)** - document the dialect - then step 7 is **deferred rather
than blocked**, and steps 1-6 and 8-10 proceed without it.

## What was checked

- **Every open item** in [open-items.md](open-items.md) was read; the thirteen marked "an owner
  decision" are the thirteen here. **No item is missing and none is extra.**
- The **recommendations** are the audit's, where it made one (FMT-14, BUILD-7, TOOL-13), and
  otherwise follow the evidence already in the audit's own parts - each recommendation above names
  the part it rests on.
- **Nothing was built, configured, run or regenerated.** Every claim here is a restatement of a
  finding recorded in an earlier part, with the evidence link.
