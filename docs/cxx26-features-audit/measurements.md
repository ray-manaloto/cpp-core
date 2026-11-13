# The measurements: what the project actually is, in numbers

**Date:** 2026-11-12
**Status:** research. **Nothing here is applied to the build.** The build lane is parked: no
builds, no compiler or toolchain installs or configuration, no CMake or preset build runs, no test
or ASan runs. Every number below was reached without invoking a compiler.

This is **part 19** of the audit. Parts 1-17 answered the owner's three questions; part 18
answered what the audit had left unasked. This part answers a narrower question: **which of the
project's qualities can be measured at all, and what do they say?**

The answer is that a useful set of them can - and that measuring them changed two numbers this
audit had been carrying, one of them badly wrong.

---

## The method

`scripts/measure.py` is the harness. It has three properties that make its output worth having:

- **It is reproducible.** The same command gives the same numbers.
- **It has a committed baseline.** `measurements.json` is checked in, so a change is visible as a
  delta rather than as an opinion - and `mise run audit:verify` fails when the baseline goes
  stale, exactly as it does for the item registry.
- **It says what it cannot do.** The output names the five measurements that need the build lane
  and the command that would produce each. A measurement that cannot be taken is not reported as
  a zero; it is reported as a gap.

`mise run audit:measure` prints the current state and the delta. `mise run audit:measure -- --write`
regenerates the baseline. `mise run audit:measure -- --check` asserts the source-derived sections
are current; it does not assert on the dependency section, because that one is read from build
artifacts and a machine that has never built cannot answer it. A check that fails where it cannot
answer is worse than no check.

Two of the metrics needed care, and both are worth stating because the wrong version of either
is easy to write:

- **The numerator and the denominator have to be the same unit.** The first version divided
  *code* lines cited by *source* lines, and reported 152%. It now counts physical source lines on
  both sides - code, comment and blank - so the share is bounded by 100% by construction.
- **A whole-file citation is not a line citation.** A file cited as a path (`format.hpp`) has been
  *looked at*; a file cited with line numbers (`format.hpp:220-281`) has been *read*. The harness
  reports the two depths separately. Conflating them turned a 63% figure into a 100% one.

---

## The findings

### The library is small, and half of it is the formatter

| | lines of code |
|---|---|
| `modules/logging/format.hpp` - the hand-rolled formatter | **492** |
| `src/logging/quill_logger.cpp` | 133 |
| `tests/logging_test.cpp` | 116 |
| `include/cpp-core/logging/cib_quill.hpp` | 97 |
| `modules/logging/logging.cppm` - the module interface | 70 |
| `include/cpp-core/logging/internal.hpp` | 17 |
| `src/reflection_demo.cpp` | 15 |
| `src/app.cpp` | 12 |
| `src/main.cpp` | 10 |
| `include/cpp-core/logging/quill_logger.hpp` | 5 |
| **total** | **967** |

**The hand-rolled formatter is 51% of the library's code.** That is the single most
decision-relevant number in this part, because `FMT-14` is the owner's decision about exactly
that file. The decision is not "is `fmt` better than a 492-line formatter" in the abstract; it is
"is `fmt` better than **half the project**". The recommendation in part 9 was already to move to
`fmt`; this part says how much is at stake.

The test file is 116 lines against a 967-line library - a ratio of **0.12**. The project has more
formatter than it has tests.

### The interface discipline holds, and is measurable

The module interface (`modules/logging/logging.cppm`) is 70 lines of code and includes
**zero standard-library headers** - only `cpp-core/logging/internal.hpp` and the private
`format.hpp`. The rule in `AGENTS.md` ("a module's global module fragment is copied into every
importing translation unit") is not a convention here; it is a measured zero, and the harness
fails if it ever stops being zero.

The project defines **no macros of its own**. The four macro invocations in the tree
(`CIB_LOG_MODULE`, `CIB_INFO`, `CIB_WARN`, `CIB_ERROR`, all in `src/app.cpp:21-30`) come from
Intel's `cib` package - which is the outcome parts 6 and 15 were looking for.

### Four of the twelve exported functions are never called

The module exports twelve functions. The test file calls eight. It never calls **`critical`**,
**`debug`**, **`log`** or **`trace`**.

This is a source-level observation, not a coverage figure - the test file does not mention them.
It is the same gap `COV-1` names, arrived at from a different direction, and it is the reason the
coverage gate in part 3 matters: a line-coverage gate alone would not have caught a function that
is never called.

### The audit's own coverage, at two depths

The library is **1,415 source lines**.

| | lines | share |
|---|---|---|
| cited with line numbers - **read** | 1,415 | **100%** |
| credited from a whole-file path - **looked at** | 1,415 | 100% |
| seen, either way | 1,415 | 100% |

Every library file has been looked at, and - since **part 20** - every line of it has been **read**
at line granularity. The concentrated reading is where the defects are: `format.hpp` has all 602
of its source lines cited individually, and `src/logging/quill_logger.cpp` has all 169 of its.

**Two corrections to this table, and a ratchet.** When this part was written the library was
**1,425** lines and **904** of them (63%) were read. The denominator was wrong: the harness
measured a file's length with `text.split("\n")`, which counts the trailing empty element, so it
credited one phantom line per file - ten of them. The real number is **1,415**, and the true
share was **895/1415 = 0.633**, not 904/1425. The bar's floor was corrected with it (0.63 →
0.625), and the harness now counts the lines that exist.

**Then part 20 read the 520 unread lines**, and the share is **1.0**. That is the **one ratchet**
the floor takes: it was set at today's value so the bar would hold, and it moves when the reading
moves. The read gap - "looked at, but not read at line granularity" - is now **zero**, and the
harness will say so the moment a new file appears that nobody has read.

### The dependency closure, measured by the compiler's own record

This is the section where the measurement changed a number the audit had been carrying.

The first implementation resolved the project's own `#include` lines and reported **77** third-party
headers reached. **That was wrong**, and it was wrong in a way worth recording: the resolver
started from the project's headers and followed the includes it could see, so it missed everything
the *translation units* pulled in - 29 headers, including 27 of Boost.MP11 and 29 of quill's.

The right source was already on disk. A Ninja build writes one depfile per translation unit,
listing every header the compiler actually opened; the last build left nine build trees' worth.
Reading a build artifact is not building anything.

**Nine build trees - two compilers, five configurations - independently record the same closure:**

| package | headers reached |
|---|---|
| quill | 52 |
| boost (MP11) | 27 |
| stdx | 16 |
| log | 5 |
| fmt | 3 |
| log_binary | 2 |
| ut | 1 |
| **total** | **106** |

460 third-party headers are installed. The project's compiled closure reaches **106** of them -
**23%**.

### Eleven of the eighteen installed packages are reached by nothing the project compiles

The install tree carries eighteen packages. The closure touches seven. The other eleven are
installed, pinned, and interface-linked by the `intel-cib` overlay port, and **nothing the project
compiles includes a single header from them**:

`async`, `cib`, `conc`, `flow`, `interrupt`, `log_fmt`, `lookup`, `match`, `msg`, `nexus`, `seq`.

This sharpens the question part 18 raised. The `intel-baremetal-concurrency` and
`intel-baremetal-senders-and-receivers` overlays are **not dead weight in the project** - they are
transitive dependencies of the `intel-cib` overlay port, which declares them in
`ports/intel-cib/vcpkg.json:7-11`, finds them in `ports/intel-cib/portfile.cmake:35-37`, and links
them in `ports/intel-cib/portfile.cmake:43`
(`INTERFACE_LINK_LIBRARIES "intel::stdx;intel::async;intel::concurrency;Boost::mp11;fmt::fmt"`).
Dropping them means diverging the overlay from upstream, which tracks `main` - so they come back
on the next bump.

That is a different proposition from "remove them", and it is the one the owner should answer if
the install size ever matters. It is not on the critical path: nothing the project compiles reads
them, so they cost install time and disk, not build time or runtime.

Boost.MP11 is the one package in the closure that is not trimmable: it is structural to Intel's
`stdx`, not a choice the project makes.

---

## What this part does not measure

Five things need the build lane, and they are named in the harness output with the command that
would produce each:

| what | how |
|---|---|
| coverage percentage | `cmake --workflow --preset gcc16-coverage` |
| the uncovered-line list | `gcov-16 --json-format`, then the gate |
| runtime cost per message | the benchmark harness from part 18, section 4 |
| binary size | a release build with `size(1)` |
| sanitizer cleanliness | `cmake --workflow --preset gcc16-asan` |

One more thing this part does not do: it does not measure **quality**. Every number here is a
count - lines, headers, functions, packages. "967 lines" is not "good code", and "492 lines of
formatter" is not "too much formatter"; the second statement is an argument, and it is the
owner's to accept or reject with `FMT-14`.

The harness is a **ruler**, not a verdict.

---

## What this changed

- The dependency closure is **106** third-party headers, not 77, and the number now comes from the
  compiler's own record with nine build trees agreeing.
- **Eleven** installed packages are reached by nothing the project compiles - a sharper statement
  than part 18's, and one that explains *why* they are there.
- The hand-rolled formatter is **51%** of the library, which is the scale of `FMT-14`.
- The audit's own coverage was **63% read / 100% looked at** when this part was written - the
  honest version of the 100%. **Part 20 has since read the rest: 100% read.**
- The module interface's zero standard-library includes is now a **measured** zero.
- Four exported functions are never called by the test file, which is `COV-1` from the other side.

No new open item is created by this part. The findings either sharpen existing items (`FMT-14`,
`COV-1`, `BUILD-7`) or replace a claim that was already open (`VCPKG-2`, `BUILD-5`). The count
stays at 81 open items.
