# `import std;` and the standard-library-free module rule

**Date:** 2026-11-11
**Status:** research. Nothing here is applied to the build.

## The question

`modules/logging/logging.cppm` deliberately avoids the standard library. The reason is written at
the top of the file:

> The module's interface deliberately avoids the standard library. A module's global module
> fragment is copied into every translation unit that imports it, so a standard header that the
> module's interface depends on would end up next to the standard headers of any translation unit
> that includes them, and the two copies collide:
>
> ```
> GCC:    error: redefinition of 'constexpr bool std::__is_constant_evaluated()'
> Clang:  error: type alias template redefinition with different types ('std::__promote_t')
> ```

C++26 has a standard library *module*. Does `import std;` remove the constraint, or does it only
move it?

## The answer

**`import std;` works on both toolchains today - but it removes the constraint only on
clang-p2996.** On GCC 16 it moves the constraint from the module to every translation unit that
imports the module.

**And - this is the part that corrects the repository's own explanation - the standard does not
prohibit the mixing.** C++26 makes it an *implementation obligation*, so the GCC failures below are
**implementation deficiencies, not ill-formed programs**. The comment at the top of
`modules/logging/logging.cppm` describes the *observed failure mode* accurately, but it states the
standard's rule wrongly. See "What the standard actually says" below.

## What the standard actually says

The quotations below are from the C++26 working draft, rendered at `eel.is/c++draft` (source
commit `c7015b48`), consistent with **N5046** (2026-05-12) and **N5054** (2026-07-16). The `std`
module's subclause is **16.4.2.4 [std.modules]** - there is no `[module.std]` in the current
draft.

### The `std` module - 16.4.2.4 [std.modules]

- **/2**: "The named module `std` exports declarations in namespace `std` that are provided by the
  importable C++ library headers (Table 24 ...) and the C++ headers for C library facilities
  (Table 25)." It also exports the global-namespace allocation functions from `<new>`.
- **/4**: "**It is unspecified to which module a declaration in the standard library is attached.**
  *[Note: Conforming implementations ensure that mixing #include and import does not result in
  conflicting attachments ([basic.link]). - end note]*"
- **/5**: "**A declaration in the standard library denotes the same entity regardless of whether it
  was made reachable through including a header, importing a header unit, or importing a C++
  library module.**"
- **/6 note**: like all named modules, the C++ library modules "do not make macros visible"
  (`assert`, `errno`, `offsetof`).

### Importation - 10.3 [module.import]

- **/1**: a module-import-declaration "shall inhabit the global namespace scope"; in a module
  unit, import declarations "shall appear before all other declarations in the declaration-seq" of
  the purview. So a module-purview `import std;` must sit immediately after
  `export module com.rsm.logging;`.
- **/5**: an import naming a header-name imports a **header unit**. Note 4: only a header-name
  import makes macros visible; "Any other module-import-declaration does not make macros visible."
- **/7**: "When a module-import-declaration imports a translation unit T, it also imports all
  translation units imported by **exported** module-import-declarations in T." A **non-exported**
  `import std;` is therefore *not* re-imported to external importers.

### Is a TU that imports `std` and also includes standard headers ill-formed?

**No.** No rule in [module.import], [std.modules] or [cpp.import] prohibits the combination; the
draft deliberately pushes the work onto the implementation ([std.modules]/4-5). What *is*
prohibited:

| Prohibition | Rule |
|---|---|
| translating a `#include` into an import **inside a module unit** | [cpp.import]/2: "If a pp-import is produced by source file inclusion (including by the rewrite produced when a #include directive names an importable header) while processing the group of a module-file, the program is ill-formed." A "module-file" is the preprocessed form of a module unit, GMF included. |
| explicitly importing a header that is not "importable" | [module.import]/5, "H shall identify an importable header" |
| corresponding declarations of one entity **attached to different modules** | [basic.link] note: "If two declarations correspond but are attached to different modules, the program is ill-formed if one precedes the other" |
| a definition of one definable item in multiple TUs where any is attached to a named module | [basic.def.odr]/16 |

For the mixing that matters here, [std.modules]/4-5 makes a conforming implementation ensure that
both routes denote the same entities. **Rejecting the mixture is a quality-of-implementation
failure, not a diagnosable program error.**

### `export import std;` versus a non-exported `import std;`

- **`export import std;`** re-exports the std module: by [module.import]/7 every importer of
  `com.rsm.logging` also imports `std`, so `std::` names become visible to name lookup in the
  importers. Macros still are not ([std.modules]/6 note).
- **A non-exported `import std;`** is not re-imported to external importers. What an external
  importer may and may not do is fixed by [module.reach] (10.7): **/1 note**: "While module
  interface units are reachable even when they are only transitively imported via a non-exported
  import declaration, **namespace-scope names from such module interface units are not found by
  name lookup**." **/2**: additional TUs "may be considered reachable, but it is unspecified which
  are and under what circumstances."

So an importer may rely on the std entities being **reachable** for template instantiation and
completeness, but may **not** name `std::...` directly, and may **not** rely on macros. That
matches the measured clang-p2996 result exactly.

### The global module fragment versus the purview - what the standard says

| | Global module fragment | Module unit purview |
|---|---|---|
| extent | before the module-declaration ([module.unit] grammar) | "the sequence of tokens starting at the module-declaration and extending to the end of the translation unit" ([module.unit]/5) |
| purpose | "can be used to provide declarations that are **attached to the global module and usable within the module unit**" ([module.global.frag]/1) | declarations are "attached to the module in whose purview they appear" ([module.unit]/7, with the §7.2 exceptions: namespace declarations, type aliases, namespace aliases, linkage-specifications go to the global module) |
| belongs to | "The **global module** is the collection of all global-module-fragments and all translation units that are not module units" ([module.unit]/6) | the named module (`com.rsm.logging`) |
| seen by importers | not textually. A GMF declaration not decl-reachable from the purview "is discarded ... neither reachable nor visible to name lookup outside the module unit" ([module.global.frag]/3) | exported names are visible to lookup; non-exported names are at most reachable ([module.reach]) |
| macros | never reach importers - only header-unit imports make macros visible ([module.import]/5 note 4) - which is why `logging.cppm:59-60` can say that clang and GCC both drop it | the same |

**This is where the repository's comment overstates the standard.** It says a global module
fragment "is copied into every translation unit that imports it". The standard's model is the
opposite of a mandated copy: GMF declarations are **attached to the global module**, and they merge
with the importer's own global-module declarations through the same-entity rules of [basic.link] -
*if* they correspond (same tokens, same lookup results). The observed collisions
(`std::__is_constant_evaluated` redefinition; `std::__promote_t` alias redefinition) are therefore
merge deficiencies, plausibly triggered when the two parses of a header do not correspond - for
example because the macro state differs between them.

**The design conclusion is unchanged and, if anything, strengthened.** Keeping the global module
fragment down to the standard-library-free `internal.hpp`, and the purview to `format.hpp`, gives
every entity exactly one attachment - the configuration the standard's attachment rules favour. And
a deficiency is not something a project can design around: it has to be worked around until it is
fixed upstream.

### Include translation - what the standard requires, and what the compilers implement

**The standard requires nothing.** [cpp.include]/10 (15.3): "If the header identified by the
header-name denotes an importable header ([module.import]), it is **implementation-defined** whether
the #include preprocessing directive is instead replaced by an import directive ([cpp.import]) of
the form `import header-name ;`"

| Compiler | Include translation | The `std` module |
|---|---|---|
| GCC 16 | yes - to the `<bits/stdc++.h>` **header unit**: "Whenever the `<bits/stdc++.h>` header unit has been built, GCC now transparently translates an #include of any importable standard library header into an import of `<bits/stdc++.h>`"; the new `--compile-std-module` "builds the ... `<bits/stdc++.h>` header unit and the `std` and `std.compat` modules before compiling any source files" | shipped in GCC 15, improved in 16 |
| Clang 21 | not listed among the C++2c changes in the 21.1.0 release notes | usable via the libc++ / libstdc++ BMIs that the build system produces |

libc++'s own documentation still warns: "Including headers after importing the `std` module **may
fail**. This is hard to solve and there is a work-around by first including all headers".

CMake's side: `import std` support is gated in 4.4 by `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` (the
UUID is CMake-version-specific) and became non-gated in 4.5; **Ninja generators only**, because
"Header units are not supported" - which is exactly why CMake's GCC path never builds the
`<bits/stdc++.h>` header unit.

**A TU that imports `std` and also includes a non-standard header such as `<unistd.h>` is not
prohibited either.** [std.modules] reaches only the Table 24 / Table 25 library headers;
`<unistd.h>` is in neither, so it is not a C++ library header at all. [cpp.include]/10 translation is
implementation-defined, and [cpp.import]/2's ill-formedness applies only inside module units.

Sources: [std.modules](https://eel.is/c++draft/std.modules), [module.import](https://eel.is/c++draft/module.import),
[module.reach](https://eel.is/c++draft/module.reach), [module.global.frag](https://eel.is/c++draft/module.global.frag),
[module.unit](https://eel.is/c++draft/module.unit), [basic.link](https://eel.is/c++draft/basic.link),
[cpp.import](https://eel.is/c++draft/cpp.import), [cpp.include](https://eel.is/c++draft/cpp.include),
[headers](https://eel.is/c++draft/headers), the
[GCC 16 changes page](https://gcc.gnu.org/gcc-16/changes.html), the
[CMake modules manual](https://cmake.org/cmake/help/latest/manual/cmake-cxxmodules.7.html),
[libc++'s Modules.html](https://libcxx.llvm.org/Modules.html).

## What was verified

The following was measured on this machine (scratch projects under the approved temporary
directory, CMake 4.4.5 + Ninja 1.13.2, `g++-16` = Homebrew GCC 16.2.0 with libstdc++
`__GLIBCXX__=20260807`, `clang++-p2996` = bloomberg/clang-p2996 21.0.0git with libc++
`_LIBCPP_VERSION=210000`). No file in the repository was written.

### The gate

`import std;` needs CMake's experimental support, which is off by default:

```cmake
# before project()
set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD "f35a9ac6-8463-4d38-8eec-5d6008153e7d")
# per target, or globally
set(CMAKE_CXX_MODULE_STD ON)
```

The UUID is version-specific and has to be looked up for the CMake in use:

| CMake | UUID |
|---|---|
| 4.4.0 and later | `f35a9ac6-8463-4d38-8eec-5d6008153e7d` |
| 4.3.x | `451f2fe2-...` |
| 3.30 - 3.31.7 | `0e5b6991-...` |

Other requirements: Ninja 1.11 or later (header units are not supported by CMake), and
`-fmodules` for GCC (not implied by `-std=c++26`; GCC 16 still defaults to `gnu++20`).

Sources: [CMake `CXX_MODULE_STD`](https://cmake.org/cmake/help/latest/prop_tgt/CXX_MODULE_STD.html),
[`CMAKE_CXX_MODULE_STD`](https://cmake.org/cmake/help/latest/variable/CMAKE_CXX_MODULE_STD.html),
[the cmake-cxxmodules manual's "import std Support" section](https://cmake.org/cmake/help/latest/manual/cmake-cxxmodules.7.html#import-std-support),
[the CMake experimental-gate UUID history](https://discourse.cmake.org/t/cmake-experimental-cxx-import-std-value-history-and-state/15712),
[the GCC 16 changes page](https://gcc.gnu.org/gcc-16/changes.html),
[the GCC 16 C++ modules manual](https://gcc.gnu.org/onlinedocs/gcc-16.2.0/gcc/C_002b_002b-Modules.html).

### The matrix that matters

> **Correction, added by part 18, section 6.** The matrix below was measured with **`-fmodules`**
> (see "The gate" above: *"`-fmodules` for GCC"*). **The project's own GCC 16 build uses
> `-fmodules-ts`** - CMake 4.4.5's `Modules/Compiler/GNU-CXX.cmake` sets `CMAKE_CXX_MODULE_MAP_FLAG`
> to `-fmodules-ts` for GCC >= 14, and `build/gcc16-debug/compile_commands.json` shows
> `-std=c++26 -freflection -fmodules-ts -fmodule-mapper=...`. **And the project's own GCC 16 build
> does the shape the last row says fails**: `tests/logging_test.cpp` imports the module and
> includes `<cstdio>`, `<string>` and `<unistd.h>`, the module exports no standard-library types,
> and `build/gcc16-debug/tests/cpp-core-tests` exists. So the matrix **does not price this
> project's configuration**, and *"option (c) is blocked on GCC 16 today"* is an unverified claim
> here. It is `MOD-11` in [open-items.md](open-items.md), and it is the one measurement that decides
> the price of option (c). The readings below stand as readings of the `-fmodules` configuration.

The same module was built three ways and imported four ways:

| The importing translation unit | GCC 16.2 | clang-p2996 + libc++ 21 |
|---|---|---|
| `import mylib; import std;` (no textual headers) | works | works |
| `import mylib;` + `#include <cstdio>` | **fails** - `conflicting imported declaration 'typedef struct __sFILE FILE'` | works |
| `import mylib; import std;` + `#include <cstdio>` | **fails** - `redefinition of 'void std::__terminate()'` | works |
| the module exports no std types, importer + `#include <cstdio>` | **fails** | works |

### Why

Two different mechanisms are at work.

**On clang**, in C++23+ semantics a module's global module fragment is *attached to the global
module* rather than textually re-included into each importer. Clang therefore merges the
importer's `#include <cstdio>` with the `std` module's own copy of the header declarations
without complaint.

**On GCC**, once the `std` module is reachable in a translation unit, any *textual* `#include` of a
standard or system header in that translation unit collides with the `std.compat` module's
declarations. GCC's "include translation" - which rewrites an `#include` of an importable standard
library header into an `import` of the `bits/stdc++.h` **header unit** - only fires when that
header unit exists. CMake's GCC path builds the `std` **module**, not the header unit, so the
translation does not fire.

The practical consequence for cpp-core is precise:

- **On clang-p2996 the module may `import std;` in its purview, with an empty global module
  fragment, and every importing translation unit keeps its own `#include`s.** That unblocks
  `std::source_location`, `std::format_string`, `std::expected` and `std::optional` inside
  `logging.cppm`, and the hand-rolled `__builtin_FILE` / `__builtin_LINE` / `__builtin_FUNCTION`
  triple can be replaced by `std::source_location`.
- **On GCC 16 the same import compiles, but every translation unit that imports the logging module
  would have to stop including standard headers.** In cpp-core that is `src/app.cpp`,
  `src/main.cpp`, `src/reflection_demo.cpp` and `tests/logging_test.cpp` - and those files include
  quill's and cib's headers, `<unistd.h>` and so on. It is a project-wide migration, not a change
  to one file.

### The manual route is not an option

Driving `import std;` by hand rather than through CMake does not work:

- **clang + libc++'s modulemap path fails**: libc++'s `<complex>` uses the `INFINITY` and `NAN`
  macros, which are not visible in a module context
  (`error: use of undeclared identifier 'INFINITY'`), and after working around that clang reports
  `error: import of module 'std' imported non C++20 importable modules` because the modulemap's
  `std` transitively imports the header modules `std_core` and `std_config`, which have non-empty
  global module fragments. The root cause of that error is not understood. CMake's `std.cppm` path
  avoids it.
- **GCC's manual path**: `g++-16 --compile-std-module -fmodules` produces `gcm.cache/std.gcm`, but
  GCC resolves the CMI path relative to the current working directory, so `-I` and `-isystem` do
  not help, and `-fmodule-mapper=std=file=...` is rejected ("failed opening mapper"). CMake
  generates a mapper file in GCC's format, which is why the CMake route works.

## The three options

### (a) Keep the module standard-library-free - the status quo

The 607-line `modules/logging/format.hpp` stays, and `std::source_location` stays out of reach.

- **Pro:** one code path, both compilers, no experimental CMake gate, no dependency on the
  standard library module's maturity, no risk to the importers. It is also the configuration the
  standard's attachment rules favour: every entity has exactly one attachment.
- **Con:** the project keeps re-implementing `std::format`, `std::to_chars` and the type traits,
  and the format specification it implements is a subset of the standard's with at least one
  divergence (`{:f}`).

### (b) `import std;` in the module's purview on clang-p2996 only

- **Pro:** the module can use the standard library on one of the two compilers; the importers do
  not change at all; `std::source_location` replaces the `__builtin_*` triple.
- **Con:** **two divergent code paths.** The formatter would have to exist twice - once as a
  standard-library-free header for GCC and once using `std::format` for clang - unless the
  implementation is factored so that the *interface* stays standard-library-free and only the
  *implementation* differs. That factoring is possible: `modules/logging/format.hpp` is already a
  module-private implementation detail, and `include/cpp-core/logging/internal.hpp` is already the
  standard-library-free boundary between the module and `src/logging/quill_logger.cpp`. Moving the
  formatting to the implementation side of that boundary would put `std::format` on the plain
  translation unit - but then the arguments have to cross the boundary, which is a type-erasure
  problem (see [quill-runtime-formatting.md](quill-runtime-formatting.md)).
- **Con:** it depends on an experimental CMake gate with a version-specific UUID, until CMake 4.5.
- **Con:** libc++ itself warns that "Including headers after importing the `std` module **may
  fail**" - so the importers' own `#include`s are not guaranteed to survive on the clang path
  either.

### (c) `import std;` everywhere, and migrate every importer

- **Pro:** one code path; the module can use the whole standard library; `std::format` can be used
  directly.
- **Con:** the migration is large and touches the third-party headers. The importing translation
  units would have to use `import std;` *and* keep including quill's, cib's and POSIX headers; the
  tests use `<unistd.h>`, which is not a standard header and is not in the `std` module at all, so
  the tests would have to mix `import std;` with a textual POSIX include. The catalog tooling
  (`gen_str_catalog`) scans the object files for undefined symbols, and the module's object layout
  would change.
- **Con:** it turns on an experimental CMake feature for the whole project.
- **Con:** it is **blocked on GCC 16 today** - any standard or system-header include in an importing
  translation unit fails. **Corrected by part 18, section 6: the block is unverified in the
  project's configuration** - the project compiles with `-fmodules-ts`, the matrix above was
  measured with `-fmodules`, and the project's own GCC 16 build does the shape the matrix says
  fails. See `MOD-11`.

## The recommendation

**Keep (a) for now, and design the code so that (b) is cheap later.**

The concrete way to do that: keep the module's *interface* standard-library-free (it is what the
importers see, and it is what makes the two compilers work), and put the standard-library-dependent
work behind `include/cpp-core/logging/internal.hpp`, which already exists for exactly this purpose.
Then `std::format` becomes available on both compilers without `import std;` at all - the
implementation is a plain translation unit (`src/logging/quill_logger.cpp`) and may use the standard
library freely today.

What that costs is the type erasure: the arguments of a log call would have to cross the
`emit()` boundary in a form that `std::format` can consume at the other end. That is the
subject of [quill-runtime-formatting.md](quill-runtime-formatting.md), and it is the same
investigation that decides whether `format.hpp` can shrink.

**Do not adopt (c).** It is a project-wide migration for a benefit that (b) plus the existing
`internal.hpp` boundary can deliver in a much smaller change.

**Revisit (b) when** CMake is 4.5 or later (the gate becomes unnecessary), clang-p2996 is pinned
and accepted as non-production, the GCC path stays standard-library-free and green, and
`format.hpp` remains the **single** formatter on both paths - the divergence buys
`std::source_location` and internal conveniences, not a second formatter whose output could
diverge from the one the tests assert on.

## Open questions

1. How large is the GCC migration in option (c), exactly? Which of the importers' headers would
   have to become `import std;`, and does the POSIX include in the tests survive the mix?
2. Can the type-erasure boundary of option (b) be made to work with a small, fixed-size
   representation - a function pointer table, a variant of primitives - and how much code would
   that be?
3. Does GCC 16.2 translate an `#include` of an importable header **inside a module unit** (the
   global module fragment or the purview), and does it then diagnose the [cpp.import]/2
   ill-formedness - or silently accept non-conforming code?
4. Does GCC 16.2 reject an importing translation unit that includes **only** `<unistd.h>` (no C++
   standard headers)? The measurement covers "any standard or system header"; the isolated case is
   untested.
5. Is `<unistd.h>` in GCC 16's importable-header set, so that [cpp.include]/10 translation could
   ever apply to it?
6. Does the GCC 16.2 failure persist when `--compile-std-module` has actually built the
   `<bits/stdc++.h>` header unit - i.e. is the failure an artefact of CMake not building header
   units, or a merge deficiency in GCC?
7. Does CMake's dependency scanning handle `#if` around `import std;` in `logging.cppm`?
8. Do quill's, cib's and ut's headers compile in a translation unit that imports `std` on
   clang-p2996 (libc++ documents include-after-import failures)?
9. Does the catalog's `nm` scan still find the same undefined `catalog<>` / `module<>` symbols
   when the importers use `import std;`?
