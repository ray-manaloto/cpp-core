# The decisions the owner has to make

**Date:** 2026-11-12
**Status:** research. Nothing here is applied to the build.

The audit has **84 open items**. Seventy of them are settled by a compile, a run or a
preprocessor pass - they are questions, not decisions, and they unblock the moment the build lane
reopens.

**Fourteen are decisions**, because the answer is a judgement about what the project should be, not
a fact about the world. They are scattered across `open-items.md`; this file gathers them into one
sheet, with a recommendation for each.

(Three further items - `VCPKG-1`, `VCPKG-2` and `QUIL-8` - were answered by part 18, sections 2
and 4, and are now in `open-items.md` section 12 rather than in the open list. The count was 83
until then; part 18 then added `FMT-15`, `MOD-10` and `MOD-11` of its own. It was 81 after
`FMT-9` and `TOOL-16` were answered and moved to section 13 as well; part 20 added `DEF-7` and
`DEF-8`, which is 83; and part 21 added `BUILD-9`, which is **84** today.)

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
| **(b) validate** | move the check from `format_matches<arg_count>` into `format_string`'s constructor, which knows the argument **types** | the scanner needs the type set; a real behaviour change. **And the renderer has to change with it** - see below |
| **(c) move** | move the formatting out of the module interface, so one formatter serves both paths | the plan's last step; needs **QUIL-1** to succeed |

**The constraint part 18, section 6 added: (b) is only coherent if the module's *renderer* comes
from the same library as the validator.** `std::basic_format_string` validates against the
**standard's** grammar, and fmt validates against fmt's - so a module that validates with one and
renders with the other accepts specifications it does not implement. `{:>06}` is the example: the
standard means *right-align in a width of 6* (`"    42"`), and the module renders it as zero-pad
(`"000042"`). **A check that is present and wrong is worse than no check at all**, so "validate
with the standard, format with the module" is not one of the options - it is a new defect.

**The consequence for each option:**

- **(b) with `std::format_to`** would fix DEF-5 and make the two paths agree - but
  `std::format_to` is **not `constexpr`** in libstdc++ 16 or libc++ 21, so it costs the
  `constexpr` formatter (plan step 3) **and** the `static_assert` formatter tests.
  **Part 18, section 8.5 qualifies this: it is a *today* statement, not a durable one.**
  GCC 17's libstdc++ has `__cpp_lib_constexpr_format 202511L` and marks `std::format`,
  `std::vformat`, `std::format_to` and `std::formatted_size` `constexpr` - so the cost of (b)
  **disappears on the GCC side** when GCC 17 lands (horizon: 2027; GCC 17 is not released). It
  does **not** disappear on the libc++ side: libc++ 21 and libc++ `main` have no
  `__cpp_lib_constexpr_format`, and llvm#171292 is still open with 0 comments. And because the
  project must keep **both** compilers working, the hand-rolled `constexpr` formatter **cannot be
  retired until libc++ catches up** - which is the same rule the rest of the project follows.
- **(b) with fmt** keeps the `constexpr` formatter - fmt's compile-time API is constexpr - and
  fixes DEF-5 - but **fmt cannot enter the module interface** (a textual `#include` in a module
  unit yields global-module declarations), so this needs fmt's *module*, which the pinned vcpkg
  port does not build. It needs an overlay port with `FMT_MODULE=ON`.
- **(c)** gets the same result through the implementation side, where `std::format` is available
  today with no modules work at all - which is why the recommendation has not changed.

**The fmt-over-`std::format` case weakens, but the recommendation does not.** The audit's case
for fmt was *"neither standard library implements P3391R2, so fmt is the only constexpr formatter
available"*. When libstdc++ 17 ships, that becomes *"libc++ does not"* - a **different and
weaker** argument, and one that leaves the project's two compilers **disagreeing** about whether
the standard's formatter is constexpr. That disagreement is itself a portability problem, and it
is the kind the project's two-compiler rule exists to avoid. **fmt remains the right answer for
this project; the *reason* changes** from "the standard is not there" to "the standard is not
there **on both compilers**".

**Your answer: (c) — use fmtlib; single formatter for both paths; depends on QUIL-1.**

**What this means.** The hand-rolled formatter (492 lines, 51% of the library) is replaced by fmtlib.
Both module path and catalog path use the same fmtlib-based formatter. This unblocks step 7 of the
plan but **depends on QUIL-1** (can a quill Codec push N fields from one pack element?). If QUIL-1
fails, this path is dead and we fall back to (a) or (b).

**What it gates.** Plan step 7 - the only step that changes the module's design. Steps 3-6 make
the current design better whether or not (c) happens, so **steps 1-6 do not wait for this**.

**If QUIL-1 fails:** fall back to (a) document or (b) validate with fmt.

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

**Your answer: YAML — add PyYAML via mise; keep .cmake-format.yaml.**

**What this means.** Install PyYAML in the mise environment (mise.toml), pin the cmakelang version,
and keep the existing .cmake-format.yaml config. The config stays human-readable with comments.

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

**Your answer: (a) — use CIB's stable ID mechanism per logging.adoc / binary_stable_ids.**

**What this means.** The CIB tool already has a STABLE_JSON mechanism (`gen_str_catalog.py` has
`STABLE_JSON` / `--stable_json` / `read_stable` / `assign_ids`). `cmake/catalog.cmake` does not
use it — the flag reaches argparse with an empty list. Follow the CIB docs: `logging.adoc` and
the `binary_stable_ids` example. The stable file (e.g., `cmake/catalog-stable.json`) is committed;
IDs survive clean builds, branch switches, and new machines. An ID change shows in a diff.

**What it gates.** **DEF-6**, and the catalog's use as deployment collateral.

## The ten that shape but do not gate

### BUILD-1 - what warning flags should the project use?

**There are none today** - not `-Wall`, not `-Wextra`, not `-Wpedantic`, not `-Wconversion`, not
`-Wshadow`, in the toolchain or in any target. That is a gap next to a clang-tidy plan.

This is the owner's call because **adding warnings is a behavioural change**: new diagnostics on
code that compiles today.

**Your answer: all at once — `-Wall -Wextra -Wpedantic -Wconversion -Wshadow`.**

**What this means.** One sweep, one cleanup. All five flags enabled on both compilers from the
first implementation build. The noise is handled in a single pass. `-Wpedantic` on C++26
feature-test macros is known problematic but will be addressed directly.

**Do it after the `constexpr` sweep (step 3) and before the clang-tidy work** - that way the
compiler's warnings and clang-tidy's checks do not arrive in the same diff.

### BUILD-2 - should cpp-core be consumable outside this repository?

**Not today**: there is not one `install()` call and no `export()` set in any of the five
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

(For the record: the project's own four `CMakeLists.txt` files contain no `install()` call and no
`export()` set - **verified**.)

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

### BUILD-4 - is `clang23` kept?

The toolchain and `cmake/cpp-core-check.cmake` both accept it, with a full validation branch, but
there is **no `clang23` triplet and no `clang23` preset** - so it cannot be reached through the
supported path.

There is a real tension here: **part 3's clang-tidy design needs Homebrew clang 23** to build a
BMI with. But clang 23 **cannot build this project** - Homebrew's libc++ has no `<meta>`, and
`src/reflection_demo.cpp` cannot even be parsed without it - so the BMI it would build is of a
project it cannot compile.

**Your answer: conditional — add clang23 preset + triplet when Homebrew libc++ has `<meta>`.**

**What this means.** The validation branch in `cmake/cpp-core-check.cmake` stays. The preset and
triplet are added **only when** Homebrew's libc++ gains `<meta>` support (so `src/reflection_demo.cpp`
can parse). Until then, no clang23 preset/triplet exists — it's not a supported configuration.
If clang-tidy needs a BMI, TOOL-3 measures whether the building compiler (GCC 16 or p2996) can
provide it.

### BUILD-5 - should there be CI?

There is **no `.github/` directory and no git remote**. The coverage gate, the format check and the
clang-tidy check therefore have **no home** until CI exists - they would be local presets. This
also makes **TOOL-16** (what a CI runner provides) moot.

**Your answer: no CI yet — local presets (mise run audit:verify/measure/acceptance).**

**What this means.** No `.github/` directory, no workflow file. The gates are local commands
anyone can run: `mise run audit:verify`, `mise run audit:measure`, `mise run audit:acceptance`.
A workflow with no remote rots. Revisit when a remote exists; the design doesn't change, only
where it runs.

### BUILD-8 - should the build check the catalog's message set against the call sites?

The catalog tooling's input regex (`gen_str_catalog.py:342`) **drops a line that does not match**,
and the message set is deduplicated by a 64-bit hash (`:212-213`, `:352`), so a message can go
missing from the catalog - silently, at the tool's level.

The **link** catches it, because the application's `catalog<...>` symbol would stay undefined - but
only a build that links. A dedicated check (the number of catalog entries against the number of
`CIB_` call sites) would catch it earlier and **name the message**.

**Your answer: yes — small script, part of coverage work.**

**What this means.** A script counts catalog entries vs. `CIB_` call sites. Runs as part of the
coverage gate (100% rule). Turns "undefined symbol at link" into "message X missing from catalog".
Cheap, diagnostic, fits the 100% coverage rule.

### BUILD-9 - should the build gain a feature-check gate?

Part 21 answers *how* the audit's 30 `compile` questions could be settled: CMake's
`check_cxx_source_compiles` and `try_compile` compile a snippet at configure time and keep the
answer as a cache variable. About 20 of the 30 are that shape. But:

- a check **cannot import `com.rsm.logging;`** - the module does not exist at configure time, so
  `MOD-10`, `FMT-4` and `REFL-4` are outside its reach (`FMT-15` reached the same conclusion);
- the project's **reflection flags do not reach a check**, because they are a directory-scope
  `add_compile_options()` in `cmake/cpp-core-check.cmake:40-42` and `CMAKE_PROJECT_INCLUDE` is not
  propagated into a try_compile project - so a `REFL-` check must pass `-freflection` itself;
- a check's answer is **cached for the life of the build tree**, so it can outlive the compiler it
  was measured on.

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
flushed" (`quill/Logger.h:605`) and carries the warning "Do not call this function from the
destructor of a static object. This may lead to application crashes if the thread-local
ThreadContext is destroyed before the static object invoking `flush_log`" (`Logger.h:613`).

The project's `com::rsm::logging::flush()` (`logging.cppm:89`) **says nothing about it**, and a
consumer cannot see quill's warning. **There is no bug today** - the project's own `main()` calls
it from `main` (`src/main.cpp:15`) - but the constraint has to be documented, or `flush()` has to
be made safe.

**Your answer: document in both — module header + README.**

**What this means.** Two-line caveat on `com::rsm::logging::flush()` in `logging.cppm:89` and in
the module's public header comment. Quill's warning: "Do not call from destructor of a static
object — may crash if ThreadContext destroyed first." No bug today (main() calls from main), but
consumer must know. Safe implementation would change sync→async contract — bigger than hazard
warrants.

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

### ENV-3 - `ZAI_API_KEY` for the `zai-coding-plan` provider

The two saved `.Z.AI` accounts in `opencode auth list` belong to the `zai` integration (the
standard API), not to `zai-coding-plan`, so they do not satisfy it. Either
`opencode service set env ZAI_API_KEY <key>` (stops and restarts the background service) or
`opencode auth login zai-coding-plan` (a saved account, no restart). The local `opencode.json`
registers only `glm-4.7` for that provider; `glm-5.3` and `glm-5.3-flash` are in the catalog and
would have to be added.

**Your answer: deferred — not a cpp-core decision; owner's agent setup.**

**What this means.** This is the agent environment, not a cpp-core project decision. The two
saved Z.AI accounts belong to `zai` integration, not `zai-coding-plan`. Options (`opencode service
set env ZAI_API_KEY <key>` or `opencode auth login zai-coding-plan`) are handled by the owner
outside this project. Listed here only because it appeared in the original 13.

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
| 10. The `import std;` decision | nothing - the recommendation is to keep the status quo. **Part 18, section 6 priced it**: the four-file importer migration is the biggest item, the GCC blocker is unverified in the project's configuration (`MOD-11`), and the only things `import std;` uniquely buys are `std::source_location` (~10 lines) and the standard's format-string grammar - the latter of which needs the renderer to change with it |

And if **FMT-14** is answered **(a)** - document the dialect - then step 7 is **deferred rather
than blocked**, and steps 1-6 and 8-10 proceed without it.

## What was checked

- **Every open item** in [open-items.md](open-items.md) was read; the thirteen marked "an owner
  decision" were the thirteen here when part 17 wrote the sheet. Part 21 has since added the
  fourteenth, **BUILD-9**, and it is in both places. **No item is missing and none is extra.**
- The **recommendations** are the audit's, where it made one (FMT-14, BUILD-7, TOOL-13), and
  otherwise follow the evidence already in the audit's own parts - each recommendation above names
  the part it rests on.
- **Nothing was built, configured, run or regenerated.** Every claim here is a restatement of a
  finding recorded in an earlier part, with the evidence link.
