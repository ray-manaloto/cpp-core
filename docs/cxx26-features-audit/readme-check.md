# The root README, checked line by line

**Date:** 2026-11-12
**Status:** research. **Nothing here is applied to the build.** The root `README.md` is the first
thing a reviewer reads, and this audit has already found that it was wrong in several places. This
part checks every factual claim in it against the sources, records what is wrong, and fixes it.

The claim that needed the most work to settle is the one the README makes first: *"Both compilers
build and pass the tests."* The answer turned out to be **yes - and provably so**, even though the
committed tree has never been rebuilt.

## The method

Every claim in `README.md` was checked against the file it describes:

| The README's section | Checked against |
|---|---|
| Layout | the directory tree |
| Compilers | `cmake/toolchains/cpp-core.cmake`, `cmake/cpp-core-check.cmake` |
| Build | `CMakePresets.json`, `cmake/presets/cpp-core.json` |
| Leak checking | `cmake/lsan.supp`, the test presets, `docs/asan-leak-check/` |
| Requirements | the root `CMakeLists.txt`, the toolchain, `vcpkg.json`, `vcpkg-configuration.json` |
| Logging | `modules/logging/logging.cppm`, `modules/logging/format.hpp`, `src/logging/quill_logger.cpp`, `include/cpp-core/logging/*.hpp` |
| The catalog path | `cmake/catalog.cmake`, the installed `intel-cib` tooling, the generated catalog |
| Tests | `tests/logging_test.cpp`, `tests/CMakeLists.txt` |
| Include-what-you-use | `cmake/iwyu.cmake`, `cmake/iwyu_mappings.txt` |
| Pieces | the triplets, the overlay ports, the presets |

## What is wrong

Four things. Three are small; the fourth is a gap in an instruction.

### R1 - the global-module-fragment claim, a third time

The README says, in the module-path section:

> A macro is the usual way to capture a call site, and it does not work here. A macro defined in
> the module's global module fragment does not reach the importing translation units - neither in
> clang nor in GCC, both of which drop it - and the module cannot include a header that its
> importers include, **because the global module fragment is copied into every importer and the two
> copies of the header would collide.**

That last clause is **DEF-3**, and it is the *third* place the claim appears - the other two were
corrected when part 4 was written, and this one was missed. It is the same overstatement: the
standard attaches the global module fragment to the global module ([module.global.frag]/1), and
[std.modules]/4-5 requires implementations to merge `#include` and `import` without conflicting
attachments. The collision is an implementation deficiency, not the rule.

### R2 - "does not match the arguments" is ambiguous in the wrong direction

The README says:

> The format string is checked at compile time: `format_string<>`'s constructor is `consteval` and
> throws (a compile-time error) when the format string is malformed or does not match the arguments.

The check is `detail::format_matches<sizeof...(Wrapped)>`
(`modules/logging/logging.cppm:71`), and what it compares is the **number** of the replacement
fields against the **number** of arguments. The module's own comment says so precisely
(`logging.cppm:47-49`: "a format string that is malformed, or that does not match the number of
arguments, does not compile").

"does not match the arguments" can be read as a *type* check, which is exactly the check the module
does **not** do - **DEF-5**. The README elsewhere (in "What the two paths share") is careful about
this; here it is not.

### R3 - the catalog JSON is abridged without saying so

The README shows the catalog as

```json
{
  "messages": [
    { "msg": "cib levels map onto quill levels: INFO -> Info, WARN -> Warning", "id": 0 },
    ...
  ],
  "modules": [ { "string": "cpp_core", "id": 0 } ]
}
```

under the sentence *"The catalog of this project holds three messages (IDs 0 to 2) and one module
(`cpp_core`, ID 0)"*. The real file has five fields per message - `msg`, `type`, `arg_types`, `id`,
`args`, `tags` - and an `enums` object. The IDs and the texts are right; the shape is not. A reader
who diffs the block against the generated file sees a difference that is not a defect.

The corrected block is now **byte-identical** to the generated file, apart from the trailing newline
a fenced block needs:

```console
readme block len: 794   generated file len: 793
readme == generated + '\n': True
```

### R4 - the "Without vcpkg" instruction cannot work as written

The README says:

```sh
cmake --preset gcc16-release -B build/nv-gcc16-release -DCMAKE_TOOLCHAIN_FILE=$PWD/cmake/toolchains/cpp-core.cmake
```

Overriding the toolchain does take vcpkg out of the configure - but it also takes vcpkg's
**search path** out with it. vcpkg's toolchain is what puts the installed tree on
`CMAKE_PREFIX_PATH` (`vcpkg.cmake:452`, `z_vcpkg_add_vcpkg_to_cmake_path`), and the project's own
toolchain does not do it. The root `CMakeLists.txt` then asks for

```cmake
find_package(intel-cib CONFIG REQUIRED)
find_package(quill CONFIG REQUIRED)
```

and there is nowhere for them to be found. The instruction needs one more line: the prefix path of
an already-installed vcpkg tree.

## What is right

Everything else checks out. In particular, three claims that would have been expensive to get wrong
are exactly right:

| The claim | The evidence |
|---|---|
| **the module's API is `setup`, `flush`, `set_level`, `current_level`, `log_raw`, `log` and the six level shortcuts** | `logging.cppm:85-151` - the list matches, in that order, with nothing missing |
| **the `format_string<>` constructor is `consteval` and takes the location as defaulted parameters** | `logging.cppm:66-69` - the README quotes the signature verbatim, and it is verbatim |
| **the IWYU scope table** | `cmake/iwyu.cmake:39-67` - the three checked sources and the three skipped ones, with the same reasons, in the same order |

The preset table, the sanitizer options (`detect_leaks=1` with `cmake/lsan.supp` for
`p2996-asan`, `detect_leaks=0` for `gcc16-asan`), the hardening rules, the compiler check, the
triplet names, the `ut` port's reason and the catalog's three messages are all correct.

**The ports are pinned to their upstream HEAD.** The README says they are "pinned to the latest
upstream commit", and that is true as of 2026-11-12 - checked against the GitHub API, each of the
five pinned `REF`s is the current head of its repository:

| Port | Pinned | Upstream head | Date |
|---|---|---|---|
| `intel/cpp-baremetal-concurrency` | `77be79110fd8` | same | 2026-10-28 |
| `intel/cpp-baremetal-senders-and-receivers` | `5629659b781b` | same | 2026-11-11 |
| `intel/compile-time-init-build` | `b5c68e65801f` | same | 2026-11-09 |
| `intel/cpp-std-extensions` | `94546c5a9122` | same | 2026-11-09 |
| `stephenberry/ut` | `dc65567be78feb` | same | 2026-07-31 |

(The four Intel ports use `version-date` in their manifest, which is vcpkg's form for a port with
no semantic version. The *source* is pinned exactly, by the `REF` in the portfile - part 12's
section 3 is about the manifest metadata, not about the sources.)

## The one that took work: "both compilers build and pass the tests"

The README's claim is in the "Compilers" section, and it is the project's main build claim - so it
is worth knowing exactly what it rests on.

**The committed tree has never been built.** The timeline:

| when | what |
|---|---|
| 2026-11-11 15:03 | `079bedf` - the source-location study changes the source |
| 2026-11-11 15:35:52 | the last `p2996-debug` build (the test log's timestamp) |
| 2026-11-11 16:36:03 | the last `gcc16-debug` build (the test executable's timestamp) |
| **2026-11-11 16:37:30** | **`42d35bb` - the clang-format conformance changes eight source files** |
| 2026-11-11 17:37 onwards | every later commit is documentation |

So the formatter conformance landed **90 seconds after** the last build, and nothing has been built
since. The README's claim rests on the tree *before* that commit.

**But the change is provably semantics-preserving.** The eight files it touched were compared by
**token stream**, not by text: a small C++ lexer (comments, string literals, character literals,
raw string literals and escapes are recognised) was used to reduce each revision to its sequence of
tokens, and the two sequences were compared.

| File | tokens | identical? |
|---|---|---|
| `include/cpp-core/logging/cib_quill.hpp` | 1106 | **yes** |
| `include/cpp-core/logging/internal.hpp` | 148 | **yes** |
| `include/cpp-core/logging/quill_logger.hpp` | 41 | **yes** |
| `modules/logging/format.hpp` | 3939 | **yes** |
| `modules/logging/logging.cppm` | 838 | **yes** |
| `src/logging/quill_logger.cpp` | 1001 | **yes** |
| `src/reflection_demo.cpp` | 95 | **yes** |
| `tests/logging_test.cpp` | 1233 | **yes** |

Whitespace outside literals is not significant in C++, and the punctuators that *are* significant
inside macros - `#` and `##` - are tokens, so they are compared too. **The committed tree is the
same program as the tree that built and passed the tests.**

So the README's claim stands, and it now stands on a check rather than on an assumption. The
weaker statement - "it was built before the reformat" - would have been the honest thing to write
without this check.

## What this added to the audit's upstream copies

The audit quotes fmt's headers more than any other third-party source, and they were the only
major upstream dependency **not** vendored. They are now, under
[`upstream/fmt/`](upstream/README.md) - and the vendoring turned up something worth recording.

**The installed fmt is not pristine upstream 12.2.1.** vcpkg downloads the 12.2.1 release tarball
and applies a patch of its own:

```diff
--- a/include/fmt/format.h
+++ b/include/fmt/format.h
@@ -326,6 +326,9 @@ class uint128 {
+  friend constexpr auto operator~(const uint128& n) -> uint128 {
+    return {~n.hi_, ~n.lo_};
+  }
```

It is a backport of upstream PR **#4813** ("Fix fallback uint128 bitwise not"), and it is in the
vcpkg port's own `downloads/` directory as `fmt-backport-4813.patch`. The provenance is now exact:

| file | provenance | git blob |
|---|---|---|
| `base.h` | byte-identical to upstream 12.2.1 | `9df283418079f4745f2120e8647a447f4836ac30` |
| `compile.h` | byte-identical to upstream 12.2.1 | `f05d8426c680eada6bb1270c009a6e06038096f6` |
| `format.h` | upstream 12.2.1 **+ the #4813 backport** | `0bff24a6bfec476daa63976db457b439431e58ac` |
| `LICENSE` | byte-identical to upstream 12.2.1 | `795fdaec8f2ce6fcc97bbb15d1a6ac073af7bd17` |

and the three-line insertion was verified by applying the patch to pristine upstream 12.2.1 and
comparing the result with the installed header - **identical**.

**Why this matters to the audit's citations.** The patch inserts three lines at
`include/fmt/format.h:329-331`, so **every `format.h` line number after 328 is three higher in the
installed file than in pristine upstream**. The audit's citations are to the *installed* file - for
example `fmt/format.h:2991-3005` for the shortest-representation code, where pristine upstream has
it at 2988-3002:

```console
$ grep -n 'Generate the shortest representation' upstream-12.2.1-format.h
3002:    // Generate the shortest representation.
$ grep -n 'Generate the shortest representation' installed-format.h
3005:    // Generate the shortest representation.
```

`base.h` and `compile.h` are unaffected, so their citations are the same in both. A reviewer
checking a citation against pristine upstream would have been three lines out on every `format.h`
reference; now the vendored copy is the one the citations point at, and the patch is beside it.

Every fmt citation in the audit was checked against the vendored files: `base.h:1440` (the state
machine), `base.h:1473-1477` (the type check), `base.h:1503-1512` (the `0` rule),
`base.h:1530-1558` (the type set), `format.h:2991-3005` (the shortest representation),
`format.h:3496` (Dragonbox), `compile.h:55-60` (the `_cf` literal), `compile.h:565-578`
(`FMT_STATIC_FORMAT`) and `compile.h:594` - **all of them resolve to what the audit says they
resolve to**.

## Sources and method

- **The README's claims**: **[source]** - every file in the table at the top, read in full.
- **The token-stream comparison**: **[measured]** - a C++ lexer written for the purpose
  (comments, string and character literals, raw string literals and escapes are recognised);
  comments are stripped, since they cannot change what the compiler sees. The lexer is in
  `/private/var/folders/.../T/opencode/token_stream.py` - it is a research tool, not part of the
  project, and the *result* is recorded above.
- **The ports' upstream heads**: **[measured]** - the GitHub API, on 2026-11-12.
- **fmt's provenance**: **[measured]** - the upstream tag's commit
  (`208219daff58f2a7438f6931cc2ddc358acf33ef`), the git blob hashes of the upstream and the
  installed files, and `git apply` of vcpkg's patch to a pristine upstream checkout.

**Nothing was built, configured, run or regenerated.**
