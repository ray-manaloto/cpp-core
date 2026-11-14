# The build system and the dependency tree, which the audit never treated as a subject

**Date:** 2026-11-11
**Status:** research. **Nothing here is applied to the build.** The features audit looked at the
project's *source*. It did not look at the **build** - the CMake, the presets, the vcpkg overlays,
the triplets - and that turned out to hide a few facts that change decisions.

## What was read

Every file below was read in full:

| Area | Files |
|---|---|
| the build | `CMakeLists.txt`, `modules/CMakeLists.txt`, `modules/logging/CMakeLists.txt`, `tests/CMakeLists.txt` |
| the CMake support | `cmake/prelude.cmake`, `cmake/project-is-top-level.cmake`, `cmake/variables.cmake`, `cmake/dev-mode.cmake`, `cmake/cpp-core-check.cmake`, `cmake/iwyu.cmake`, `cmake/catalog.cmake`, `cmake/lsan.supp` |
| the presets | `CMakePresets.json`, `cmake/presets/cpp-core.json` |
| the toolchain | `cmake/toolchains/cpp-core.cmake` |
| the dependencies | `vcpkg.json`, `vcpkg-configuration.json`, `ports/*` (6 ports), `triplets/*` (5 triplets) |
| the installed tree | `build/p2996-debug/vcpkg_installed/vcpkg/info/*.list`, `build/*/vcpkg-manifest-install.log` |

## The facts

### 1. `fmt` is already installed - declaring it is free

**The project's `vcpkg.json` lists only `intel-cib`, `quill` and `ut`. fmt is not one of them.** But
fmt 12.2.1 **is** in the installed tree, because `intel-cpp-std-extensions` depends on it:

```text
ports/intel-cpp-std-extensions/vcpkg.json
  "dependencies": ["boost-mp11", "fmt", "intel-baremetal-concurrency"]
```

and the installed package list confirms it:

```text
build/p2996-debug/vcpkg_installed/vcpkg/info/fmt_12.2.1_arm64-osx-p2996.list
build/p2996-debug/vcpkg_installed/vcpkg/info/intel-cpp-std-extensions_2026-11-09_arm64-osx-p2996.list
```

**So step 2 of the plan - adding `"fmt"` to `vcpkg.json` - costs nothing**: no download, no version
change, no port rebuild, no reconfigure of the dependency graph. It changes the package from
*transitive* to *direct*, which is the point: the project is about to depend on it directly, and a
transitive dependency is not a dependency. (The rule that a project must not depend on a
transitive dependency is the same reason the project has its own overlay ports rather than relying
on the registry for `ut`.)

### 2. The two copies of fmt are structural, not accidental

The vcpkg `quill` port installs **only** `quill/bundled/fmt/`:

```text
build/p2996-debug/vcpkg_installed/vcpkg/info/quill_13.1.0_arm64-osx-p2996.list
  arm64-osx-p2996/include/quill/bundled/fmt/
  arm64-osx-p2996/include/quill/bundled/fmt/args.h
  arm64-osx-p2996/include/quill/bundled/fmt/base.h
  ...
```

No standalone `fmt/` comes from the quill port. So:

- quill 13.1.0 uses its **bundled** fmt 12.2.0, in the namespace `fmtquill`, and the installed
  headers have no `QUILL_USE_EXTERNAL_FMT` option;
- the project's fmt 12.2.1 is the **standalone** package, in the namespace `fmt`, pulled in by
  `intel-cpp-std-extensions`;
- **the two copies coexist whatever the project does.** Declaring `fmt` directly does not change
  that - it only makes the project honest about using it.

This settles `ENV-1` and most of `FMT-9` in the audit's open-items list: the two-copies problem is
structural. The project rule stands - **custom formatters are written for `fmt` only** - and the
cib path does not need them, because it formats primitives and decays its one project type to its
underlying integer (`decay_enum_value`, `cib_quill.hpp:55-61`).

**What is still open:** whether the *upstream* vcpkg port has an opt-in feature for an external fmt
that this installation simply did not enable. The builtin registry is not checked out on this
machine (`$VCPKG_ROOT` is the mise-installed vcpkg *tool*; it has `scripts`, `triplets`,
`buildtrees` and `downloads`, but no `ports` tree and no `.git`), so the port's `vcpkg.json` at the
pinned baseline cannot be read here. That is `VCPKG-1` in
[open-items.md](open-items.md).

### 3. The overlay ports pin a *date*, not a version

All four Intel overlay ports use `version-date`, which is vcpkg's form for a port with no semantic
version:

| Port | `version-date` |
|---|---|
| `ports/intel-baremetal-concurrency` | 2026-10-28 |
| `ports/intel-baremetal-senders-and-receivers` | 2026-11-11 |
| `ports/intel-cib` | 2026-11-09 |
| `ports/intel-cpp-std-extensions` | 2026-11-09 |

**That is legitimate**, and it is what vcpkg wants for a port that tracks a branch rather than a
release. But it means the overlay does not pin an upstream release: it pins a snapshot of a moving
target. `ports/README.md` already says the important half - *"a port in `ports/` always wins over
a vcpkg port of the same name, so never shadow a vcpkg port by accident: a shadowed library stops
following the baseline pinned in `vcpkg.json`."*

**The open question is which of these five overlay ports actually shadow a builtin vcpkg port.**
`ut` is the likely one - it is a popular header-only test library and vcpkg ships it. If the
builtin `ut` at the pinned baseline is newer than the overlay's 1.2.1 (REF
`dc65567be78febd265ca36c324e1c504512d4d74`), the project is silently pinned to an older version
than the baseline would have given it. The Intel ports are less likely to be in the registry, but
"less likely" is not a check. That is `VCPKG-2`.

### 4. There are no compiler warning flags

`cmake/toolchains/cpp-core.cmake` sets, in order: the compiler, the sanitizer
(`-fsanitize=address,undefined` / `-fsanitize=thread`), the standard library's hardening mode
(`_LIBCPP_HARDENING_MODE` / `_GLIBCXX_ASSERTIONS`), the reflection flags
(`-freflection`, `-fexpansion-statements`, `-fannotation-attributes`), `-stdlib=libc++`, and
`-fPIC` for Linux port builds.

**There is no `-Wall`, no `-Wextra`, no `-Wpedantic`, no `-Wconversion`, no `-Wshadow` anywhere in
the project.** Not in the toolchain, not in `cpp-core-check.cmake`, not per target.

That is a real gap, and an odd one next to a clang-tidy plan: the tooling design proposes a
clang-tidy check set (part 3), but the compiler itself is silent about the warnings it could have
been reporting for free on every build, on both toolchains, with no extra infrastructure. Adding
warnings is also a **behavioural** change - new diagnostics on existing code - so it belongs to the
owner, not to a research note. That is `BUILD-1`.

### 5. There are no install or export rules

Not one `install()` call, and no `export()` / `install(EXPORT)`, in any of the five `CMakeLists.txt`
files. The library is **not consumable outside this repository**: another project cannot
`find_package(cpp-core)`, and the module cannot be imported by anything that is not built here.

For a project whose whole subject is a C++ module, that is worth a decision rather than an
accident. If cpp-core is meant to be consumed, it needs install rules, an export set, and - the
awkward part - a decision about what the *public* surface is. See `BUILD-2` and `BUILD-3`.

### 6. The public header surface is undefined

`include/cpp-core/logging/` holds three headers:

| Header | What it is | Standard library? |
|---|---|---|
| `internal.hpp` | the module's standard-library-free boundary | **no** - deliberately |
| `quill_logger.hpp` | `quill_logger()`, the implementation's accessor | **yes** - it `#include <quill/Logger.h>` |
| `cib_quill.hpp` | the CIB_* macro path | **yes** - `<string>`, `<string_view>`, `<type_traits>` |

All three sit under `include/`, and `target_include_directories(cpp-core-logging PUBLIC
"${PROJECT_SOURCE_DIR}/include")` publishes that directory to every consumer. But `quill_logger.hpp`
is the implementation's business - its own comment says so:

> The declarations live in com::rsm::logging::detail: they are the implementation's business, not
> part of the module's public interface.

So a consumer can include a header that drags quill and the standard library into their
translation unit, and that header is *published*. With no install rules there is no install-time
boundary either. The public surface is currently "whatever happens to be under `include/`" - which
is not a decision, it is an accident. That is `BUILD-3`.

### 7. `clang23` is an unreachable configuration

`cmake/toolchains/cpp-core.cmake` accepts `CPP_CORE_COMPILER` = `gcc16 | clang23 | p2996`, and
`cmake/cpp-core-check.cmake` has a full validation branch for `clang23`:

```cmake
elseif(CPP_CORE_COMPILER STREQUAL "clang23")
  if(_id STREQUAL "Clang" AND _ver VERSION_GREATER_EQUAL 23 AND _ver VERSION_LESS 24 AND NOT _path MATCHES "p2996")
    set(_ok TRUE)
  endif()
  set(_want "LLVM clang 23 (not Apple clang, not clang-p2996)")
```

**But there is no `clang23` triplet and no `clang23` preset.** The five triplets are
`arm64-osx-gcc16`, `arm64-osx-gcc16-asan`, `arm64-osx-p2996`, `arm64-osx-p2996-asan` and
`arm64-osx-p2996-tsan`. The toolchain and the configure check support a third compiler that cannot
be reached through the supported path.

The three clang-tidy questions in part 3 all assume Homebrew clang 23 is available to build a BMI
with, so `clang23` is not dead code - it is a compiler that the tooling plan needs and the preset
system cannot reach. Either it gets a triplet and a preset, or the support comes out. That is
`BUILD-4`.

### 8. There is no CI, and no remote

There is no `.github/` directory - the repository has no GitHub Actions workflow, no other CI
configuration, and no git remote:

```text
git remote -v     -> (empty)
```

**This changes one of the audit's open questions.** `TOOL-16` asks *"does CI (a GitHub Actions
runner) provide `gcov-16` at a known path or via `ubuntu-latest`'s GCC? If not, the gate must
either fetch/install GCC 16 ... or keep coverage as a local/preset gate only for now."* The
question is moot: **there is no CI to host the gate.** The coverage gate, the format check and the
clang-tidy check all have to be local presets until CI exists, and "should there be CI?" is an
owner decision that changes where three planned deliverables live. That is `BUILD-5`.

It also means the committed work has never been reviewed by anything but the owner - which is
consistent with the request to "keep everything needed for review offline".

### 9. The preset system is complete for what it covers, and that is all it covers

`cmake/presets/cpp-core.json` is thorough: configure, build, test and workflow presets for
`gcc16-{debug,release,asan}`, `p2996-{debug,release,asan,tsan}` and `p2996-iwyu`, with the
sanitizer environment variables the ASan and TSan work needs, and the `detect_leaks` asymmetry
between GCC and clang documented in a `$comment`.

What is missing is exactly what the tooling plan adds and has not been added yet: **no coverage
preset, no tidy preset, no format-check preset**. Part 3's design proposes `p2996-tidy`,
`gcc16-coverage` and `cmake-checks`; none of them exists. This is not a defect - the build lane is
parked - but it is the shape of the remaining work, and it is consistent with `PARKED.md`'s ordered
list.

### 10. The catalog's link graph is deliberate, and worth stating

`cmake/catalog.cmake` generates `cpp-core-catalog.cpp` from the `nm` output of `cpp-core-app` and
`cpp-core-test-code`, and compiles it into the `cpp-core-catalog` static library. The two
executables link it:

```cmake
add_executable(cpp-core src/main.cpp)
target_link_libraries(cpp-core PRIVATE cpp-core-app cpp-core::logging cpp-core-catalog)
```

Neither `cpp-core-app` nor `cpp-core-test-code` links it - correctly, because they only *refer* to
the specialisations (`catalog<Message>()`, `module<Module>()`) and the definitions arrive at link
time. The catalog library is also `PUBLIC intel::cib`, so the consumers get cib's headers.

The open question is not the link graph but the **IDs**: `gen_str_catalog` derives them from `nm`,
and `nm` output depends on the compiler's mangling. So the same source may produce different
catalog IDs under gcc16 and p2996. If it does, the "one catalog" story breaks - the application and
the tests would disagree about which ID is which message. That is `BUILD-6`, and it is a different
question from `MAC-2` / `FMT-11` (which ask whether the *macro* form changes the symbols).

## What this changes for the plan

| Plan step | Effect of this part |
|---|---|
| 2 - add `"fmt"` to `vcpkg.json` | **cheaper than expected**: fmt is already installed; it is a one-line manifest change with no download |
| 5 - fmt in `format_double` | unchanged, but the two-copies rule is now settled rather than open |
| the clang-tidy and coverage work | **need a home**: there is no CI, so they are local presets; and `clang-tidy` needs a Homebrew clang 23, which the presets cannot currently select |

## The new open questions

All of them are in [open-items.md](open-items.md): `VCPKG-1` and `VCPKG-2` (the dependency tree),
`BUILD-1` to `BUILD-6` (the build system), and `FMT-13` (the authoritative macro values, from
part 11).

## The method

Every claim in this part is **[source]**: read from a file in the repository or from the installed
dependency tree, with the path. The one claim about a git remote is **[measured]**
(`git remote -v` is empty). Nothing was built, configured or run.
