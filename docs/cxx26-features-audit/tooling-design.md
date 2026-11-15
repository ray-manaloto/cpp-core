# Design note: clang-tidy, cmake-format/cmake-lint and 100% unit-test coverage in cpp-core

Date: 2026-11-11 · Status: design (RESEARCH ONLY - nothing here is committed or applied)
Scope: `modules/`, `include/`, `src/`, `tests/` + `cmake/` tooling. No repository file was modified.
Author of this note: SDLC researcher. Verification basis per claim: **[doc]** = tool documentation
read by URL, **[source]** = installed cmakelang 0.6.13 source read directly, **[measured]** = read-only
tool run against the repo (clang-format stays untouched; no build/compiler/test/coverage commands were run),
**[inferred]** = reasoning from documented behaviour, flagged as such.

---

## 0. Machine findings (verified, and deltas against the known facts)

- `lcov` / `genhtml`: not on PATH - **confirmed** by probe (`command -v` fails). Cannot install (constraint) -> lcov route is out.
- `gcovr`: present at `~/.local/bin/gcovr` **but broken** - the symlink points at `~/.local/share/uv/tools/gcovr/bin/gcovr`, whose interpreter `~/.local/share/uv/tools/gcovr/bin/python` does not exist ("bad interpreter ... no such file or directory"), and `uv tool list` reports "Tool `gcovr` environment not found". **gcovr is effectively unavailable.** This was not known before this research - it closes off the middle candidate route.
- `gcov-16`: present on PATH (`gcov-16` → `/opt/homebrew/opt/gcc/bin/gcov-16`, Homebrew GCC 16.2.0; `--version` reports **"JSON format version: 2"**).
- `/usr/bin/gcov` is **Apple LLVM 21.0.0's gcov**, not GCC's - the gate must invoke `gcov-16` explicitly, never bare `gcov`.
- `llvm-cov`/`llvm-profdata` 23.1.5 present; clang-p2996 raw profile is version 10 vs llvm-profdata's expected 11 (given) -> clang source-based coverage unusable; `build/coverage-clang/` is the abandoned experiment (PARKED.md).
- cmake-format/cmake-lint 0.6.13 live in `~/.local/share/mise/installs/pipx-cmakelang/0.6.13~uv~ebf25d09f858a795/bin/`. The mise shims (`~/.local/share/mise/shims/`) fail with "No version is set" - **nothing pins cmakelang in any mise config** (confirmed in `mise ls` and by probing the shims). The direct path works.
- **The cmakelang pipx install has no PyYAML** (`import yaml` → ModuleNotFoundError in that venv, verified). `.cmake-format.yaml` will **crash** (`load_yaml()` does `import yaml` outside any `except ValueError`; both the `-c` path (`get_one_config_dict`) and the autodiscovery path end there). `.cmake-format.json` (stdlib `json`) and `.cmake-format.py` (`exec`) work today; `try_get_configdict` tries JSON first, then YAML, then Python - but the extension-matched `.yaml` path crashes before any fallback. Fix: pin `pipx:cmakelang` in a project `.mise.toml` and install the `[YAML]` extra, or use JSON. (The task asked about `.cmake-format.yaml`; see Part 2.)
- [measured] `cmake-lint` on this repo's CMake sources: with default `line_width=80` → ~90 `C0301` + `C0103`/`E1120`/`C0113` hits; with `--line-width 100` → **19 `C0301`** + **9 `C0103`** + **1 `E1120`** + **1 `C0113`**. Exact list in Part 2.5.
- [measured] `cmake-format --check` (100 cols) fails on **9 of 12** CMake files (the hand-wrapped-call style collapses). Exact in Part 2.6.
- `build/` contains `coverage-clang/` (abandoned), plus the normal preset dirs; `.gitignore` covers `build/`, so instrumented `.gcno/.gcda` never enter git **if they land under `build/`**.
- `.editorconfig` says `indent_size = 3` for **all** files - it is stale against the rewritten `.clang-format` (2-space) and against the 2-space CMake files. Flag for the tooling lane (a formatting gate should make `.clang-format` the single source of truth; either fix `.editorconfig` to 2 or scope it).

---

## 1. clang-tidy

### 1.1 What its C++20-modules support actually is (2026-11 state)

Status is: **no supported configuration for module projects; checking a module interface unit (.cppm) is not possible in practice; checking non-module TUs is possible but fragile, and many checks crash or silently fail on module code.**

Evidence (all URLs verified during this research):

1. **Issue llvm/llvm-project#63939 - "[Clang Tidy][C++20 Modules] Clang Tidy too slow and buggy on modules"** (opened 2023-07-18, still **open**, updated 2026-08-25). With `import std;`, 33 listed checks crash (`bugprone-dangling-handle`, `bugprone-narrowing-conversions`, `bugprone-use-after-move`, `cppcoreguidelines-narrowing-conversions`, `cppcoreguidelines-missing-std-forward`, `cppcoreguidelines-pro-bounds-array-to-pointer-decay`, `cppcoreguidelines-rvalue-reference-param-not-moved`, `google-build-explicit-make-pair`, `misc-const-correctness`, `modernize-make-unique`, `modernize-make-shared`, `modernize-use-nullptr`, `modernize-use-transparent-functors`, `performance-avoid-endl`, `performance-move-const-arg`, `performance-unnecessary-value-param`, `portability-std-allocator-const`, `readability-redundant-*`, `readability-uppercase-literal-suffix`, ...). `misc-include-cleaner` does not crash but cannot see `std::` from `import std;`. ChuanqiXu9 (clang modules author): **"Yeah, it reveals that we lack a design (and the corresponding implementation) for modules in clang-tidy."**
   - <https://github.com/llvm/llvm-project/issues/63939>
2. **Issue llvm/llvm-project#62258 - "`clang-tidy` fails on CXX modules"** (open since 2023-04-20, label clang:frontend). CMAKE_CXX_CLANG_TIDY + Ninja dyndep → `error: unable to handle compilation, expected exactly one compiler job in '' [clang-diagnostic-error]`. ChuanqiXu9 (2025-04-08): **"In practice, we run clang-tidy after build so that clang-tidy can find them."**
   - <https://github.com/llvm/llvm-project/issues/62258>
3. **CMake discourse, "clang-tidy + cxx_modules"** (April 2023): `CMAKE_CXX_CLANG_TIDY` + `-E __run_co_compile --tidy=...` on a `.ixx` fails with `error: unable to handle compilation, expected exactly one compiler job` / `module 'foo' not found [clang-diagnostic-error]`. The workaround documented there is `-fprebuilt-module-path=<dir with the .pcm/.gcm>` after a completed build; `@module.modmap` arguments are invisible to compile_commands.json. **A compilation database does not carry enough information for clang-tidy to compile module TUs.**
   - <https://discourse.cmake.org/t/clang-tidy-cxx-modules/7938>
4. **ChuanqiXu9, "Clang doesn't find standard C++ modules ..." (discourse.llvm.org #71326):** BMIs are required and are not in the compilation database; downstream workaround is (2) build first then run tools against the BMIs; **"No, the required information to use just `compile_commands.json` for `clang-tidy` is not available yet."** And the broader statement: **clangd-like tools must compute the module DAG and build BMIs themselves; clang-tidy is accepted to use a "build first, then analyze" workflow; the required build-mode is not provided for clang-tidy.**
   - <https://discourse.llvm.org/t/clang-tidy-doesnt-find-standard-c-modules-despite-providing-compilation-database-and-prebuilt-modules-path/71326>
   - <https://chuanqixu9.github.io/c++/2025/12/03/Clangd-support-for-Modules.en.html>
5. **Issue #145628 → PR #145630 - "[clang-tidy] [Modules] Skip checking decls in clang-tidy"** (issue created 2025-06-25; PR **merged 2026-03-19**). When a TU imports module `a`, clang-tidy warned about the bodies of decls from `a` (e.g. cppcoreguidelines-narrowing-conversions fired for `use.cpp`). The fix sets `ASTMatchFinder::MatchFinderOptions SkipDeclsInModules = true` globally (the fix lives in ASTMatchers, not in clang-tidy itself - author unsure it is the right fix) and adds test `clang-tools-extra/test/clang-tidy/checkers/cxx20-modules.cppm`. This mitigates *duplicate* diagnostics from imported modules; it does **not** make `.cppm` invocations valid.
   - <https://github.com/llvm/llvm-project/pull/145630>
   - <https://github.com/llvm/llvm-project/issues/145628>
6. **PR #178471 - "[clang-tidy] Fix performance-trivially-destructible with C++20 modules"** (merged 2026-04-07). False positive: a class seen through both header include and module import gets its implicit destructor declared multiple times in the redeclaration chain, breaking `isFirstDecl()`. Fix: `unless(isImplicit())`. This confirms that even "correct" checks carry modules-specific false-positive/negative modes being fixed ad-hoc - there is no systematic modules QA for the check inventory.
   - <https://github.com/llvm/llvm-project/pull/178471>
7. **Default-set changes: 22.1.0 removed `clang-analyzer-*` from the default checks** (users must now opt in explicitly), and **clang-tidy now displays diagnostics from all non-system headers by default** (`-header-filter` now defaults to `.*`). **23.1.0 removed the `hicpp` module entirely** (all checks moved to their homes - e.g. `hicpp-special-member-functions` → `cppcoreguidelines-special-member-functions`) and deprecated `zircon`.
   - <https://releases.llvm.org/22.1.0/tools/clang/tools/extra/docs/ReleaseNotes.html>
   - <https://releases.llvm.org/23.1.0/tools/clang/tools/extra/docs/ReleaseNotes.html>
8. **Documentation (clang-tidy index)**: `-checks` is a glob list processed in order; `.clang-tidy` is YAML, discovered per-file from the closest parent dir; keys include `Checks`, `WarningsAsErrors`, `HeaderFilterRegex`, `ExcludeHeaderFilterRegex`, `ImplementationFileExtensions` (default `c,cc,cpp,cxx` - **`cppm` is NOT a default implementation-file extension**), `HeaderFileExtensions`, `SystemHeaders`, `ExcludeHeaderFilterRegex`; command-line overrides file; `--verify-config` validates configs; **`--enable-module-headers-parsing` exists** ("preprocessor-level module header parsing for C++20 and above, empowering specific checks to detect macro definitions within modules... experimental... may cause performance and parsing issues"); `-p` takes the build dir; `--dump-config` prints the effective configuration. Default header filter is `.*` (22.1.0+).
   - <https://clang.llvm.org/extra/clang-tidy/index.html>

### 1.2 Can clang-tidy check a module interface unit at all?

**No, not for this project.** Three independent blockers (in our configuration):

- **(a) Invocation**: CMAKE_CXX_CLANG_TIDY/co_compile cannot be consumed by clang-tidy (finding 2, 3).
- **(b) BMI version lock**: clang-tidy only understands BMIs produced by *the same clang build it is linked against*. clang-tidy 23.1.5 (Homebrew) cannot read BMIs from clang-p2996 (Bloomberg's clang 21.0.0git fork), and **GCC's `.gcm` BMIs are not readable by clang at all**. Making importers checkable would require BMIs built by clang-tidy's own clang build with exactly the same flags as the project - p2996 is not that compiler, and there is no preset that uses Homebrew clang to build the project.
- **(c) `-std=c++26` reflection dialect and module semantics**: parsing `logging.cppm` needs `-freflection` and `-std=c++26`, which Homebrew clang 23 does not fully implement for P2996 (Bloomberg's fork is the reference environment; Homebrew's `-freflection` support must not be assumed). And even if Homebrew clang parsed it, **checking the .cppm as a TU only re-derives what the module's consumers already see** - and if anything imports it, the importer hits blockers (a)/(b) anyway.

The honest fallback is what the IWYU integration does: **check only the non-module translation units** - `src/app.cpp` and `src/logging/quill_logger.cpp` (no `import` anywhere in them) - and state explicitly in the target output that the module interface (`modules/logging/logging.cppm`), `src/main.cpp`, `src/reflection_demo.cpp` and `tests/logging_test.cpp` are **not** clang-tidy-covered. That set is small but real: app.cpp contains the catalog-path calls and quill_logger.cpp contains the whole backend wiring.

`src/app.cpp` caveat: it is C++26 with cib macros; it parses with Homebrew clang 23 given `-std=c++26`, `-isystem` for vcpkg includes (already in compile_commands.json) and the reflection flags removed (see 1.5). `src/reflection_demo.cpp` cannot be parsed at all (`<meta>` absent from Homebrew's libc++) - skip it. `modules/logging/logging.cppm` and the other importers - skip (blockers (a)-(c)).

### 1.3 Check groups: appropriate vs misfire

Baseline rule: enable only `-*` + a curated allowlist, because the modules crash list touches exactly the groups this question names, and the crashes are not hypothetical - they reproduce in upstream CI fixtures (issue #63939 is `import std;`-triggered; we never `import std;`, but we *do* have module imports in importers we nonetheless skip, and future TUs will import the module).

| Group | Verdict | Reason |
|---|---|---|
| `clang-diagnostic-*` (compiler warnings surfaced as checks) | **enable** | mirrors the compiler; never crashes; these are bugs real diagnostics. With clang-tidy 22+, note the default set is empty - enabling explicitly is required for anything to fire. |
| `clang-analyzer-*` | **enable, gated** | CSA was dropped from default checks in 22.1.0 - must opt in or nothing fires. High-signal on this codebase (small, no macros of our own). Not modules-clean in general (#63939 lists several CSA-adjacent crashers? actually the crash list is checks; CSA core is separate) - but our checked TUs have no imports, so it is safe *there*; keep it enabled with the "disable on false positive" rule. |
| `bugprone-*` | **enable, minus two noisy ones** | The group with the best signal/noise here. Crash list under modules (see 1.1(1)) covers `bugprone-narrowing-conversions`, `bugprone-use-after-move`, `bugprone-swapped-arguments`, ... - our checked TUs don't import modules, so none are triggered; this is also why importers are excluded. Exclude `bugprone-easily-swappable-parameters` (notorious false positives, option-heavy) and `bugprone-exception-escape` (consteval format_string ctor `throw` is a compile-time fiction; the flag has form `[[maybe_unused]]`... note: format_string is only in the .cppm, not in checked TUs, so irrelevance in scope; enable but expect config). |
| `readability-*` | **OFF** | Stylistic; `readability-identifier-naming` would rename our whole lower_case style; `readability-magic-numbers`/`readability-function-size` fight the codebase's deliberate constants (e.g. buffer capacities); `readability-else-after-return` etc. duplicate .clang-format's layout job. The one that is arguably useful, `readability-container-size-empty`, is ok out of habit but off by policy. |
| `modernize-*` | **OFF (for now)** | "Modernize to C++11" checks: fix-it-heavy, opinion-laden (`modernize-use-auto` would erase our explicit types); also the biggest #63939 crash surface (`modernize-make-unique/make-shared/use-nullptr/use-transparent-functors`). Re-evaluate per check when modules are stable. |
| `cppcoreguidelines-*` | **OFF** | Aliases largely of bugprone/hicpp; the modules crash list includes `cppcoreguidelines-narrowing-conversions`, `cppcoreguidelines-missing-std-forward`, `cppcoreguidelines-pro-bounds-array-to-pointer-decay`, `cppcoreguidelines-rvalue-reference-param-not-moved` (#63939) and #145628/#145630 was a `cppcoreguidelines-narrowing-conversions` duplicate-*importer* failure. Keep `cppcoreguidelines-avoid-goto` only if wanted - we have no gotos; simplest: off. |
| `performance-*` | **OFF** | `performance-unnecessary-value-param` **will** fire on `log(level, format_string<...> fmt, ...)` and on `format_string` passed by value - the pass-by-value is deliberate (a ~64-byte consteval token). `performance-move-const-arg`, `performance-unnecessary-copy-initialization` etc. crash under modules (#63939). `performance-for-range-copy` style gains don't exist here. |
| `misc-*` | **OFF** | `misc-const-correctness` crashes under modules and is noisy; `misc-include-cleaner` cannot see module imports (#63939) and fights our include-block style; `misc-misplaced-const`-style checks are covered by the compiler. |
| `google-*` | **OFF** | Google style is a *different style* (CamelCase names, `int x` conventions); enforcing it here is wrong by definition; several `google-build-*` crash under modules. |
| `hicpp-*` | **OFF - and unavailable** | The `hicpp` module was **removed in 23.1.0** (checks moved to their homes; the table in the 23.1.0 release notes maps every one). Do not write config referencing `hicpp-*`; it would match nothing (and `--verify-config` would flag it if we wanted that signal). |
| `portability-*` | **OFF** | `portability-std-allocator-const` crashes under modules; the rest (windows/msabi) are irrelevant on macOS. |
| `cert-*` | **OFF** | Aliases/incomplete; not adding a second name for the same checkers. |
| `fuchsia-*, zircon-*, llvm-*, llvmlibc-*, linuxkernel-*, abseil-*, boost-*, altera-*, android-*, darwin-*, concurrency-*, mpi-*, objc-*, openmp-*` | **OFF** | Out of scope; `zircon` deprecated in 22, removed later. |

**Proposed `.clang-tidy`** (not committed - design sketch):

```yaml
---
# clang-tidy design for cpp-core (see docs/...). Module TUs are not checked: see note.
Checks: >-
  -*,
  clang-diagnostic-*,
  clang-analyzer-*,
  bugprone-*,
  -bugprone-easily-swappable-parameters,
  -bugprone-exception-escape
WarningsAsErrors: 'clang-diagnostic-*,clang-analyzer-*,bugprone-*'
HeaderFilterRegex: '^(?!.*vcpkg_installed).*$'   # all non-vcpkg headers; main file always reported
ExcludeHeaderFilterRegex: ''
SystemHeaders: false
ImplementationFileExtensions: ['c', 'cc', 'cpp', 'cxx', 'cppm']
HeaderFileExtensions: ['h', 'hh', 'hpp', 'hxx']
RemovedArgs: ['-freflection', '-fexpansion-statements', '-fannotation-attributes']
InheritParentConfig: false
```

Reasoning for the non-obvious keys:

- `WarningsAsErrors` equal to the enabled set (minus the two disabled bugprone entries): the gate is *"zero warnings from enabled checks"*, which is deterministic and does not enumerate codes. Not `'*'` (would silently enslave the build to whatever a future clang adds) and not `''` (would make CI pass with new warnings). [doc: warnings-as-errors same format as -checks]
- `HeaderFilterRegex` excludes vcpkg-installed headers (quill/cib/fmt) - diagnostics there are not ours to fix; our headers stay in scope. (`.*` is the default in 22+; we narrow deliberately.) [doc]
- `ImplementationFileExtensions` **adds `cppm`**: the default list lacks it; if a diagnostic ever points into `modules/logging/logging.cppm` we want it treated as implementation, not as a header swept by the filter. [doc]
- `RemovedArgs` strips the reflection flags so Homebrew clang-tidy parses the p2996-generated compile_commands.json without the unknown-flag problem. **[inferred]** - verify with `--verify-config` and one real invocation (open questions 1.6).
- `InheritParentConfig: false` pins the config; no stray `~/.clang-tidy` leaks in. [doc]

**Must stay off for a module project**: `misc-include-cleaner` (silently wrong on imports), any check from the #63939 crash list if module TUs are ever included, `readability-identifier-naming` (renames our style), `modernize-*` and `cppcoreguidelines-*` wholesale, and `bugprone-easily-swappable-parameters` (noise). If the project ever wants IWYU-style include hygiene in modules, that is what `cmake/iwyu.cmake` is for.

### 1.4 How it runs (target design; see Part 4)

- `find_program(CPP_CORE_CLANG_TIDY_EXECUTABLE NAMES clang-tidy PATHS /opt/homebrew/opt/llvm/bin NO_DEFAULT_PATH)` - **the keg-only path must be explicit**; a bare `find_program` finds Apple's clang-tidy or nothing.
- One custom target per checked TU (`tidy-app.cpp`, `tidy-quill_logger.cpp`), aggregate `tidy`, cache var `CPP_CORE_TIDY_ENABLED` default OFF, preset `p2996-tidy` (inherits `cc-p2996`/`cc-debug`/`cc-base`). [style: cmake/iwyu.cmake]
- Command: `${CPP_CORE_CLANG_TIDY_EXECUTABLE} -p build/p2996-tidy --config-file=${PROJECT_SOURCE_DIR}/.clang-tidy <TU>` - `-p` reuses the per-preset `build/<preset>` directory; `cc-base` already sets `CMAKE_EXPORT_COMPILE_COMMANDS=true`, so compile_commands.json exists. [doc: -p, --config-file]
- Output must *say*: "checked: app.cpp, quill_logger.cpp; not checked (no clang-tidy coverage): modules/logging/logging.cppm, src/main.cpp, src/reflection_demo.cpp, tests/logging_test.cpp (imports the module / needs <meta>)".
- The gate: each `tidy-*` target returns clang-tidy's exit code; with `WarningsAsErrors` equal to the enabled set, any warning is an error. **[doc: exit status of clang-tidy is non-zero when warnings are treated as errors]** Verify, don't assume - open question.
- Not a correctness oracle: clang-tidy is Homebrew clang, not the building compiler; a passing `tidy` says "no enabled-check findings", nothing about runtime correctness. The asan/tsan/tests remain the correctness gates.

### 1.5 Two-compilers note

The tidy target picks the *frontend* that parses: Homebrew clang 23.1.5. It therefore does not validate either building compiler's semantics (GCC 16 libstdc++ vs clang-p2996 libc++). It lints. Keep it in the `p2996-*` family for consistency with IWYU, but name it after the tool, not after a compiler (`tidy`, not `p2996-clean`). The GCC build's compile_commands.json would also work for the two non-module TUs (with `-freflection` removed by `RemovedArgs`); whichever is used, the commands for the module TUs are unusable by clang-tidy regardless (blockers (a)-(c)). One preset is enough; running both is wasted CI.

---

## 2. cmake-format and cmake-lint (cmakelang 0.6.13)

### 2.1 Configuration file: `.cmake-format.yaml`

The tools share one configuration system; the same file feeds `format:` and `lint:`. Auto-discovery searches the **ancestry** of each formatted file for `\.?cmake-format(.yaml|.json|.py)`; the first match wins (per-file, not merged). [doc: configuration.html] `.cmake-format.yaml` is the canonical name asked for, and the pyyaml caveat of Part 0 applies on this machine today: **use `.cmake-format.json` (or add pyyaml) until `pipx:cmakelang` is pinned with the `[YAML]` extra**. In CI, whichever is committed is fine for a formatted machine image with pyyaml; for zero-dependency robustness, commit the JSON. Whichever is chosen, the same keys/values apply (the schemas are identical).

`.cmake-format.yaml` by name - accepted by discovery, and `--config-file`/`-c .cmake-format.yaml` forces it. Key sections (all defaults from docs + the installed source):

```yaml
# Design for cpp-core (not committed). JSON equivalent: flat keys under the same sections.
format:
  line_width: 100          # default 80; matches .clang-format's 100
  tab_size: 2              # default 2
  use_tabchars: false      # default false
  fractional_tab_policy: use-space
  max_subgroups_hwrap: 2   # default 2
  max_pargs_hwrap: 6       # default 6
  max_rows_cmdline: 2      # default 2
  max_lines_hwrap: 2       # default 2
  min_prefix_chars: 4      # default 4
  max_prefix_chars: 10     # default 10
  dangle_parens: false     # default false
  dangle_align: prefix     # default prefix
  separate_ctrl_name_with_space: false
  separate_fn_name_with_space: false
  line_ending: unix        # default unix; matches .gitattributes (LF)
  command_case: canonical  # default canonical; the repo is 100% canonical already
  keyword_case: unchanged  # default unchanged; repo uses UPPER keywords - keep
  enable_sort: false       # default true; see 2.3 (we hand-order; no known-sortable lists used)
  autosort: false          # default false
  require_valid_layout: false
  always_wrap: []
markup:
  enable_markup: false     # default true - must be off (see 2.3) or the comment layout is reflowed
parse:
  additional_commands:     # teach the tools our one custom command (see 2.4)
    gen_str_catalog:
      kwargs:
        OUTPUT_CPP: 1
        OUTPUT_JSON: 1
        OUTPUT_XML: 1
        INPUT_LIBS: '*'
        GEN_STR_CATALOG: 1
        CLIENT_NAME: 1
        VERSION: 1
        OUTPUTS_TARGET: 1
lint:
  disabled_codes: []       # start empty; add only with justification
  # function_pattern / macro_pattern etc. keep defaults: the repo defines no functions/macros
```

### 2.2 Most useful keys, with defaults and what they do [doc: configopts.html + source config_util.py]

- `line_width` (80) - wrap column; **also feeds lint C0301** (`basic_checker.py:217` uses `cfg.format.line_width` - verified **[source]**). Setting 100 changes both tools' threshold.
- `tab_size` (2), `use_tabchars` (false), `fractional_tab_policy` (use-space) - indent. `.gitattributes` forces LF; `line_ending: unix` agrees; C0327 stays silent.
- Wrapping knobs: `max_pargs_hwrap` (6), `max_subgroups_hwrap` (2), `max_rows_cmdline` (2), `max_lines_hwrap` (2), `min/max_prefix_chars` (4/10) - how aggressively the pretty-printer collapses multi-line calls. The defaults reproduce hand-aligned call sites well for this repo; measure only if the diff is objectionable.
- `command_case` (`canonical`): `add_library(...)` stays lower-case-canonical; **`keyword_case` (`unchanged`)**: `PRIVATE`/`PUBLIC`/`CACHE STRING`/`FATAL_ERROR` stay as written. Repo is already uniform → no churn.
- `enable_sort` (true) - sorts *known-sortable* argument lists only; no such lists occur in this repo's CMake (`DEPENDS` of add_test? none). Setting it `false` removes a class of surprise "formatter reordered my args" diffs.
- `always_wrap` ([]) - commands forced multi-line. Candidates if desired: `gen_str_catalog`, `add_custom_target`. Optional.
- `require_valid_layout` (false) - on true, layout failure exits non-zero and writes nothing. Useful for the `cmake-format-check` gate; irrelevant with `--check` (which already fails on delta).
- `markup.enable_markup` (**true** by default) - reflows/joins comment paragraphs; the repo's hand-wrapped comment blocks and the IWYU "why skipped" list would collapse. **Set false**, mirroring `ReflowComments: false` in `.clang-format` and `ReflowComments: false` rationale (hand layout is deliberate). **[source + doc]**
- `disable` (false) - "Disable formatting entirely, making cmake-format a no-op" [doc verbatim]. Two no-op knobs exist: `format.disable: true` (global) and `# cmake-format: off` / `# cmake-format: on` (per region; "you can locally disable and enable code formatting by using the special comments" [doc: format-features.html]). For lint, the equivalent region pragma is `# cmake-lint: disable=<codes>` [doc: lint-inline.html] - it applies from the comment to the end of the *body scope* (function/macro/file scope), not line-scoped; misuse must be in review.
- `lint.disabled_codes` - global disable list; `# cmake-lint: disable=C0103` inline - local. `E0011`/`E0012` fire on malformed pragmas themselves.

### 2.3 Format-command semantics in this repo (why the tree will change) [measured]

`cmake-format --line-width 100` would reformat **9 of 12** CMake files (CMakeLists.txt, prelude, variables, iwyu, catalog, cpp-core-check, toolchains/cpp-core.cmake, project-is-top-level.cmake, modules/logging/CMakeLists.txt). The cause: the repo hand-wraps calls as "one argument per line, closing paren on its own line" (inherited from the existing "glaze-style" CMake), e.g. `message(\n FATAL_ERROR ...\n)` - cmake-format collapses those to two lines when they fit 100 cols; `--dangle-parens` does **not** preserve the hand style (verified: same 9 files still change; dangle only affects already-multi-line statements). Consequences to decide in review:

- Option A (recommended): one-shot `cmake-format -i` commit conforming the tree to cmake-format's layout - same trade-off the owner accepted for .clang-format. Review diff is mechanical.
- Option B: `format.disable: true` and cmake-lint-only enforcement - keeps hand style, loses the formatter's purpose.
- There is no Option C ("keep my exact style, still enforce with --check") - the check fails on delta by definition.
- A `.cmake-format.yaml` with `line_width: 100` then refuses anything longer; combined with `enable_markup: false`, diff churn is minimized after the one-shot.

### 2.4 The custom command: `gen_str_catalog`

`cmake/catalog.cmake` calls `gen_str_catalog(OUTPUT_CPP ... OUTPUT_JSON ... INPUT_LIBS ... GEN_STR_CATALOG ... )` - unknown to cmakelang, so the parser treats it as a plain positional function (no kwarg validation, layout as if `gen_str_catalog` were `foo`). Declare it under `parse.additional_commands` (spec above: `INPUT_LIBS: '*'`, others fixed arity) so (a) the formatter wraps its argument groups sanely, (b) lint can see its keyword arguments (E1125 missing required kwarg / E1121 too many positional args) instead of blind-parsing. [doc: configuration.html#additional_commands + source argument_nodes.py] `find_package` of the tooling is untouched.

### 2.5 Which cmake-lint rules fire on this repository - exact, measured

Tool: the cmakelang 0.6.13 install, `--line-width 100` (recommended config) and default 80 for contrast. Read-only runs; exit code 1 on findings. The repo CMake files scanned: CMakeLists.txt, prelude, variables, dev-mode, iwyu, catalog, cpp-core-check, toolchains/cpp-core.cmake, project-is-top-level, modules/CMakeLists.txt, modules/logging/CMakeLists.txt, tests/CMakeLists.txt.

At **100 cols**:

- **C0301 line too long (19)**: `cmake/cpp-core-check.cmake:14,22-27,42-43,50-54` (108/115/110/125 chars), `cmake/toolchains/cpp-core.cmake:1,11,14,24-29,38-45,66-69,85,105,107,122-125,145-148,153-156,160-165,172,181-184` (101-150 chars). [source: basic_checker.py counts physical lines; comment lines count too]
- **C0103 invalid name (9)**:
  - *directory-scope* vars must match `[A-Z][0-9A-Z_]+` (public) or `_[0-9a-z_]+` (private); the repo has lower-case directory-scope names → `variables.cmake:23,32` `warning_guard`; `iwyu.cmake:69,70,77,78` `skipped_count`, `reason_count`, `skipped_source`, `skipped_reason`; `catalog.cmake:17` `cpp_core_catalog_inputs`. [source: get_scope_of_assignment → DIRECTORY → public|private pattern]
  - *loop* vars must match `[a-z][a-z0-9_]+`; `cpp-core-check.cmake:47` `_flag`; `toolchains/cpp-core.cmake:197` `_kind`. [source: check_foreach → argument_var_pattern]
  - Note: `_cpp_core_flags`-style leading-underscore names elsewhere are fine (match private pattern). CACHE variables are all UPPER - fine. No `function()`/`macro()` definitions exist, so function/macro/argument-name rules (C0111, C0112, E0108, E0109, C0202, R0911-15) cannot fire.
- **E1120 missing required positional argument (1, false positive)**: `iwyu.cmake:76` `foreach(index RANGE ${skipped_last})` - cmakelang's RANGE parser requires exactly `RANGE start stop step` (`parse_foreach_range` → `PositionalParser(3)`), but CMake allows `RANGE <stop>` and `RANGE <start> <stop>`. Valid CMake; lint is wrong here → needs `RANGE 0 ${skipped_last} 1` rewrite or `# cmake-lint: disable=E1120`. [source: foreach.py]
- **C0113 missing COMMENT (by convention, 1)**: `iwyu.cmake:97` `add_custom_target(iwyu DEPENDS ...)` has no `COMMENT` (the per-TU targets do). Convention nit; add a COMMENT or disable inline. [source: add_xxx.py → required_kwargs COMMENT → C0113]
- Everything else clean: no C0303 (trailing ws), C0304 (final newline), C0306 (tabs), C0307 (indent), C0321, C0327 (LF everywhere via .gitattributes), C0305 (statement spacing), W0101 (no statements after return), W0104 (no deprecated commands), W0105 (no builtin-except-for-case; `PROJECT_IS_TOP_LEVEL` is not a builtin), W0106 (no dangling `$`/`{` in literals), E1122 (no dup kwargs), E1125/E1126, C0201 (no custom ARGN parser loops), C0202, E0103, I001x (no pragmas in use), C0102/C0103-vs-builtin. [doc: lint-summary.html implemented set; verified against source]

At **80 cols (default)**: those 19 C0301 become **~90** (every long comment line fires too). Keep 100.

### 2.6 cmake-format/cmake-lint command lines and CI behaviour

- In place: `cmake-format -i <files...>` (writes, exit 0 on success; exit 1 on internal error). Check: `cmake-format --check <files...>` - **silent success; on any delta raises "Check failed: <file>", exit 1**. [measured; source lines 613-622, 530-535]
- Lint: `cmake-lint <files...>` - prints per-file sections + summary; **exit 1 if any findings** (as opposed to 2 on internal errors). [source: lint/**main**.py 134-180]
- Note [measured]: lint's `--suppress-decorations` reduces output to bare findings; use it in CI logs.
- Exit-code contract for the wrapperlint targets: non-zero = gate failed → the `cmake-lint`/`cmake-format-check` targets fail → `cmake --build --preset <x> --target <t>` fails. The wrapperlint aggregate returns the first failing sub-target's code.
- `cmake-format` reads stdin if `-` is passed as file arg (irrelevant for CMake).
- The **in-place formatter should never run in CI**; only `--check`. The `format` target runs `-i` locally (developer-invoked only).

### 2.7 Invocation scope

Which files: every tracked CMake source - `CMakeLists.txt`, `cmake/**/*.cmake`, `modules/**/CMakeLists.txt`, `tests/CMakeLists.txt`. Not: `cmake/presets/*.json` (JSON, not CMake), `CMakePresets.json`. A `file(GLOB_RECURSE ...)` at target creation would pick up vcpkg overlay ports under `ports/` (their own upstream style) - **exclude `ports/`** or we reformat third-party files. Use an explicit list variable (like `CPP_CORE_IWYU_SOURCES`), not a glob, so `.cmake-format.yaml` apply uniformly.

---

## 3. Coverage: the viable route (GCC 16 + gcov-16's JSON)

### 3.1 Candidates on this machine, scored

| Route | Availability | Faithfulness for a C++20-modules project | CI friendliness | Verdict |
|---|---|---|---|---|
| GCC 16 `-fprofile-arcs -ftest-coverage` + `gcov-16 --json-format` + a ~150-line stdlib-only Python gate | `g++-16` ✓, `gcov-16` ✓ (PATH), no third-party deps | Best available: GCC compiles the module interface unit to an object file like any TU; coverage counters are per-TU and work for module TUs (no documentation contradicts it; no documentation confirms it either - flagged) | Excellent: no install, no network, deterministic exit codes, plain-text output | **WINNER** |
| `gcovr` | **Broken** (uv tool env missing; see Part 0) | Would be fine (it parses gcov JSON, supports `--json-summary`/`--fail-under-line`); but not installable offline | Would be the ergonomic winner if it worked | Rejected here |
| `lcov` + `genhtml` | Not installed | Same gcov-format limits; genhtml needs Perl (present) + lcov install (forbidden) | OK in Linux CI, not here | Rejected |
| clang source-based coverage (`-fprofile-instr-generate -fcoverage-mapping`, llvm-cov/llvm-profdata) | llvm-cov 23.1.5 present; **clang-p2996 raw profile is v10, llvm-profdata expects v11** (given; matches gcovr's note that clang 11-20 emit "2.0.1" identifiers and 21+ emits "3.0.1" [doc: gcovr gcov_parser]) | Also broken by the p2996 fork; and Homebrew clang ≠ p2996 anyway | Broken as-is | Rejected (build/coverage-clang is the abandoned evidence) |
| GCC `-fprofile-generate` PGO | Present | Not a coverage measure; wrong tool | - | Rejected |

### 3.2 GCC flags: compiling and linking

From GCC docs [doc: Instrumentation-Options]:

- Compile: `-fprofile-arcs -ftest-coverage` (measure counters + emit `.gcno` notes file). `--coverage` = `-fprofile-arcs -ftest-coverage` at compile **and** `-lgcov` at link.
- Link: `--coverage` (or `-lgcov`); static libs don't need it, the final executable does.
- Add `-fprofile-abs-path`: records absolute paths in `.gcno` so gcov resolves sources regardless of cwd. [doc]
- `-O0` is the recommended test-coverage optimization level; debug builds here are already `Debug` for the gated config, which is `-O0` on GCC by default (CMAKE_CXX_FLAGS_DEBUG / no opt). Note gcovr's guidance that `-O1` sometimes yields "better" C++ coverage - keep `-O0` for honesty; do not mix optimization levels.
- `-fprofile-dir=<path>` can relocate `.gcda` (runtime writes); not required if objects stay in `build/gcc16-coverage/` (gitignored). Keep default; simpler for `gcov -o`.
- Where files land: `.gcno` is written **next to the `.o`** (`<objdir>/<name>.gcno`); `.gcda` is written to the same directory (or `-fprofile-dir`) when the instrumented binary exits. With Ninja, e.g. `build/gcc16-coverage/CMakeFiles/cpp-core-logging.dir/modules/logging/logging.cppm.gcno` (name derived from the object filename: "logging.cppm" → suffix removed → `logging.cppm.gcno`). [doc: `-fprofile-arcs` auxname rules - "auxname is generated from the name of the output file, if explicitly specified and it is not the final executable, otherwise the basename of the source file; in both cases the suffix is removed"] For the merged static libs (cpp-core-logging), its member `logging.cppm.o`'s `.gcno` sits under the library target's `.dir` - i.e., coverage data sources depend on *where the TU's object lives*, which is what the gate walks. **OPEN QUESTION (3.6-Q1): exact .gcno path layout for `CXX_MODULES` file-set members under Ninja - must be verified by a build.**
- Instrumenting vcpkg ports: **do not** (ports would rebuild Release-only logic with coverage and link `-lgcov`; also the triplet doesn't pass our coverage var, and should not). Guard the coverage flags to project code only (`NOT CPP_CORE_PORT_BUILD`, same shape as the reflection flags). This keeps the gate's scope = our sources, and keeps vcpkg intact. [inferred from toolchain file mechanics]
- Tests are the instrumented consumers: the test binary `cpp-core-tests` links the instrumented objects + catalog lib; running it writes all `.gcda`. `ctest --preset gcc16-coverage` is the execution. A bare run of the binary works too but the gate uses ctest.

### 3.3 gcov `--json-format`: what it emits (verified against docs; JSON version 2)

`gcov-16 --json-format` writes `<object>.gcov.json.gz` (gzip-compressed). Structure [doc: Invoking-Gcov + man7 gcov(1)]:

```json
{ "current_working_directory": "...", "data_file": "<gcda path>",
  "format_version": "2", "gcc_version": "16.2.0 ...",
  "files": [ { "file": "<source path>",
               "functions": [ { "blocks","blocks_executed","demangled_name",
                                "end_line","execution_count","name","start_line", ... } ],
               "lines":     [ { "block_ids","count","line_number",
                                "unexecuted_block","function_name", ... } ] } ] }
```

- gcov-16 on this machine reports "JSON format version: 2" (measured). gcovr accepts only version 2, confirming version alignment. [doc: gcovr gcov_parser]
- `lines[]`: one entry per instrumented line; `count` = executions; `unexecuted_block` = some block(s) on that line never ran. Line-covered ⇔ `count > 0`. (`unexecuted_block` is a stricter signal we report but do not gate on - decide in review.)
- `functions[]`: per-function `execution_count`; function-covered ⇔ `> 0`.
- Branches only with `-b` (branch probabilities; `lines[].branches[]` with `count`, `fall_through_true/false`... actually branch records have `count`, `fallthrough`, `throw`, `source/destination_block_id`); conditions need `-fcondition-coverage` at compile time. Gate **lines** (and functions) for 100%; print branches as advisory.
- Multiple `.o` files instrument the same line (templates/inline in headers, weak symbols): each reports the line independently. **Merge rule: a line is covered if *any* reporting unit shows `count > 0`**; the denominator is the union of lines reported by any unit. (Sum would double-count; max/equals "any>0" coincides with sum for the >0 predicate - implement as a set union.)

### 3.4 Computing the line-coverage percentage (the gate's math)

1. Walk `build/gcc16-coverage` for `*.gcno`; for each, find its `.gcda` and object; run `gcov-16 --json-format -o <dir> <object>` in a scratch dir; parse each `*.gcov.json.gz`.
2. Filter files by repository-relative path; **exclude**: `tests/`, `build/`, `vcpkg_installed/`, `ports/`, generated `cpp-core-catalog.cpp` (it lives in the build dir, so already excluded by path).
3. Merge by `file` (absolute path after `-fprofile-abs-path`) → set of covered lines (count>0) and total instrumented lines.
4. `pct = 100 * Σ covered / Σ total`; threshold from `CPP_CORE_COVERAGE_THRESHOLD` (default `100`); fail below it; print per-file `file: uncovered/total` table and every uncovered `file:line` with the source line content (readable from the JSON - source reading optional, not required).
5. The gate script is **stdlib-only Python** (gzip, json, argparse) because `find_package(Python3)` is already required by `cmake/catalog.cmake`. No lcov/gcovr/pip.

### 3.5 The module-interface risk and the honest 100% claim

**The risk.** GCC compiles a module interface unit to an object file, and the coverage
machinery is per-translation-unit; the *source attribution* in gcov's output is the path
recorded at compile time, i.e. `modules/logging/logging.cppm` - not the `.gcm` module
artifact and not an object-named-anything. The concrete risks, in order of severity:

1. **Never-instantiated templates emit no counters (or zero-count counters) - behavior unknown.** `modules/logging/logging.cppm`'s `log()`, `trace()`, `debug()`, `critical()` etc. are templates; only `info`/`warning`/`error` are called by tests. If GCC emits no arc for an uninstantiated template, those lines vanish from the instrumented set (coverage % rises, silently dishonest). If it emits zero-count arcs, they show as uncovered (honest but forces new tests). Which one happens is a **must-verify** question - see Open Questions (3.6-Q2). Either way it never *lies*; the gate must therefore always print the instrumented file set, not only the percentage.
2. **`consteval` code paths.** `scan_format`, `format_matches` (and `format_string`'s ctor body) run at *compile* time; their runtime arcs are only folded away after instantiation - GCC may or may not attribute them to the TU. If they appear as zero-count lines, 100% line coverage is *impossible without an exclusion*; those lines are genuinely "coverage not applicable" (they only exist at compile time). **OPEN QUESTION (3.6-Q3)** - the gate may need a reviewed `coverage: ignore` marker on consteval bodies; deciding which is part of the first real run.
3. **Weak/inline duplicates**: template code instantiated in N TUs is recorded in each; merging by union (3.4) is correct; nothing else to do.
4. **The `.cppm` includes `format.hpp` (module-private)** - lines live in `modules/logging/format.hpp`, attributed to that header, still in repo scope. Same union-merge applies.
5. **GCC bug surface**: none documented for modules+coverage; also nothing documented - treat as unverified.

**What the honest 100% target means.** It means: every instrumented, non-excluded line of *this repository's* library/application/module code is executed at least once by `ctest --preset gcc16-coverage` - no more, no less. It does **not** mean: branch/MC/DC coverage (needs `-b` / `-fcondition-coverage` - report advisory only); code eliminated by the preprocessor; vcpkg or system code; the tests themselves; or code whose only definition is compile-time (`consteval`), if any such lines register as uncoverable (Q3).

**What the baseline must be, honestly.** Today it is certainly **not 100%**. From the tests' content (read, not run), the uncovered set will include at least: the `trace`/`debug`/`critical` shortcuts and every `level` value path in the logging module; `set_level`'s `<=`-filtering branches (quill_logger.cpp), every unexercised `format` specification branch in `format.hpp` (alignment/fill, sign, `#`, zero-pad, precision, `x/X/o/b`, uppercase digits); the `is_array`/`string_like`/`self_formatting` paths (no `self_formatting` type exists in the codebase); the 2048-byte buffer-truncation branch in `message_buffer`/`format_integer` capacity guards; `log_raw`'s length path (partially exercised); the cib/catalog path (`demo::run()` in `src/app.cpp` is never called by any test - the catalog IDs are produced, never executed); much of `src/logging/quill_logger.cpp` (logger creation races, `current_level` getter edge cases); `src/reflection_demo.cpp` is compiled but its runtime line (the `info(...)`) only runs if reflection works at runtime (it does) - but nothing calls it in tests. The PARKED.md "Not started" item 2 lists this predicted uncovered set already. **The first gate run will print the actual list; PARKED's list is a hypothesis to be confirmed or refuted.** The 100% gate then means: extend tests until the uncovered list is empty, plus a small reviewed exclusion file with justification per entry (e.g. consteval-body exclusions, `#if`-the-other-compiler paths). 100% = measured 100 on the merged data, or it does not ship.

**"Code only reachable through the module interface"** - e.g. `log()`/`trace()` bodies and `format_string`'s API surface consumed from `import com.rsm.logging;` - is covered by running the test suite (which imports the module); the module itself contributes the TU. It is *not* special-cased by the gate; it must simply pass. If the never-instantiated-template question (Q2) shows GCC omits those arcs, the gate will report them absent - the answer to "why is 100% reachable here" is then: the instantiations that exist are the ones testing exercises; the rest are not emitted code at all.

### 3.6 Precise questions that need a run (not answered here)

- **Q1:** What is the exact on-disk layout after `cmake --build --preset gcc16-coverage` - where do `.gcno`/`.gcno`-relative `.gcda` land for `CXX_MODULES` members (`modules/logging/logging.cppm`) and for the `cpp-core-catalog` static lib member, and does the codegen compile allow `-fprofile-arcs` unmodified?
- **Q2:** Does GCC 16 emit instrumentation arcs, and zero-count arcs, for (a) uninstantiated templates in `logging.cppm`/`format.hpp`, (b) `consteval` functions (`scan_format`, `format_matches`, the `format_string` ctor body)? Which lines appear in gcov's JSON at all?
- **Q3:** Is `unexecuted_block` set on lines we count as covered (count>0 with some unexecuted blocks), and do we gate on it (strict) or not (line-only)?
- **Q4:** What is the *actual* uncovered-line list today (PARKED's hypothesis vs measured)?
- **Q5:** Does `ctest --preset gcc16-coverage` exit non-zero on test failure in a way the workflow preset propagates to the `coverage` target (vs. requiring `-fdiagnostics-color` etc.)?
- **Q6:** Does the catalog-generated object (`cpp-core-catalog.cpp`, in the build dir) need excluding explicitly, or does the build-dir exclusion suffice?
- **Q7:** Branch coverage: does `-b` produce usable `branches[]` in gcov-16's JSON for these TUs, and is the `-fcondition-coverage` bitset stable enough to gate on (likely: no gate, advisory only)?

---

## 4. Concrete target layout (design; not committed CMake)

`cmake/clang-tidy.cmake`, `cmake/format.cmake`, `cmake/coverage.cmake` + `cmake/coverage/gcov_json_gate.py`. Presets: **`p2996-tidy`** (clang-tidy; IWYU-style opt-in), **`gcc16-coverage`** (coverage; GCC-only), **`cmake-checks`** (no compiler needed - runs the formatter/lint targets; still expressed as preset for uniformity). Existing presets untouched.

Variables:

- `CPP_CORE_TIDY_ENABLED` (option, default OFF) - `cmake/clang-tidy.cmake`, mirrors `CPP_CORE_IWYU_ENABLED`
- `CPP_CORE_CMAKE_FORMAT_ENABLED` / fold into `CPP_CORE_TIDY_ENABLED`? - **separate**: `CPP_CORE_CMAKE_FORMAT_ENABLED` (OFF default) for `cmake/format.cmake`
- `CPP_CORE_COVERAGE_ENABLED` (BOOL, default OFF) - consumed by the toolchain; implies the coverage preset's cache vars
- `CPP_CORE_COVERAGE_THRESHOLD` (STRING, default `100`) - the gate

Toolchain `cmake/toolchains/cpp-core.cmake` extension (behind `NOT CPP_CORE_PORT_BUILD`):

```cmake
# Coverage: -fprofile-arcs -ftest-coverage -fprofile-abs-path + -fprofile-arcs at link.
# GCC only. Not for vcpkg ports. Implemented like CPP_CORE_SANITIZER handling.
if(CPP_CORE_COVERAGE)
  list(APPEND _cpp_core_cxx_only -fprofile-arcs -ftest-coverage -fprofile-abs-path)
  list(APPEND _cpp_core_link -fprofile-arcs -lgcov)
endif()
```

`cpp-core-check.cmake`: no change (CPP_CORE_COVERAGE independent of COMPILER guard).

`cmake/clang-tidy.cmake` (style = iwyu.cmake):

```cmake
find_program(CPP_CORE_CLANG_TIDY_EXECUTABLE NAMES clang-tidy
  PATHS /opt/homebrew/opt/llvm/bin NO_DEFAULT_PATH)
if(NOT CPP_CORE_CLANG_TIDY_EXECUTABLE)
  message(FATAL_ERROR "clang-tidy not found (expected /opt/homebrew/opt/llvm/bin/clang-tidy). "
                      "Or turn the check off (CPP_CORE_TIDY_ENABLED=OFF).")
endif()
set(CPP_CORE_TIDY_SOURCES "${PROJECT_SOURCE_DIR}/src/app.cpp"
                          "${PROJECT_SOURCE_DIR}/src/logging/quill_logger.cpp")
set(CPP_CORE_TIDY_SKIPPED_SOURCES "${PROJECT_SOURCE_DIR}/modules/logging/logging.cppm"
                                  "${PROJECT_SOURCE_DIR}/src/main.cpp"
                                  "${PROJECT_SOURCE_DIR}/src/reflection_demo.cpp"
                                  "${PROJECT_SOURCE_DIR}/tests/logging_test.cpp")
set(CPP_CORE_TIDY_SKIP_REASONS "module interface: clang-tidy cannot consume C++20 module TUs"
                               "imports com.rsm.logging"
                               "needs <meta>, not in Homebrew libc++"
                               "imports com.rsm.logging")
# ... length-check identical to iwyu.cmake, message(STATUS) the skip reasons
# one target per TU: tidy-app-cpp, tidy-quill-logger-cpp; aggregate: tidy
# COMMAND ${CPP_CORE_CLANG_TIDY_EXECUTABLE} -p ${CMAKE_BINARY_DIR}
#         --config-file=${PROJECT_SOURCE_DIR}/.clang-tidy <source>
add_custom_target(tidy DEPENDS ${CPP_CORE_TIDY_CHECK_TARGETS})
```

`cmake/format.cmake`:

```cmake
find_program(CPP_CORE_CMAKE_FORMAT_EXECUTABLE NAMES cmake-format
  PATHS ${PROJECT_SOURCE_DIR}/../_tools  $ENV{HOME}/.local/share/mise/installs/pipx-cmakelang
  # simpler: rely on mise pin; keep find_program default + clear FATAL_ERROR unless
  # CPP_CORE_CMAKE_FORMAT_ENABLED=OFF)
find_program(CPP_CORE_CMAKE_LINT_EXECUTABLE NAMES cmake-lint ...)
set(CPP_CORE_CMAKE_SOURCES CMakeLists.txt cmake/prelude.cmake cmake/variables.cmake
  cmake/dev-mode.cmake cmake/iwyu.cmake cmake/catalog.cmake cmake/cpp-core-check.cmake
  cmake/clang-tidy.cmake cmake/format.cmake cmake/coverage.cmake
  cmake/toolchains/cpp-core.cmake cmake/project-is-top-level.cmake
  modules/CMakeLists.txt modules/logging/CMakeLists.txt tests/CMakeLists.txt)
# one target per file would be 14 targets + 1 lint per file; simpler and honest:
# two targets, each running the tool over the explicit list (not a glob):
add_custom_target(cmake-format        COMMAND ${CPP_CORE_CMAKE_FORMAT_EXECUTABLE} -i ${CPP_CORE_CMAKE_SOURCES} ...)
add_custom_target(cmake-format-check  COMMAND ${CPP_CORE_CMAKE_FORMAT_EXECUTABLE} --check ${CPP_CORE_CMAKE_SOURCES} ...)
add_custom_target(cmake-lint          COMMAND ${CPP_CORE_CMAKE_LINT_EXECUTABLE} --suppress-decorations ${CPP_CORE_CMAKE_SOURCES} ...)
add_custom_target(cmake-checks DEPENDS cmake-format-check cmake-lint)
```

(.clang-format wired the same way: `clang-format -i` / `clang-format --dry-run --Werror` targets `format`/`format-check` - the PARKED.md next step; noted here for completeness, not expanded.)

`cmake/coverage.cmake`:

```cmake
find_program(CPP_CORE_GCOV_EXECUTABLE NAMES gcov-16 REQUIRED)  # never bare gcov (Apple LLVM 21)
find_package(Python3 REQUIRED COMPONENTS Interpreter)          # already required by catalog
# target: coverage
#   1) runs: cmake --build --preset <cov> --target cpp-core-tests   (build done by workflow)
#   2) runs: ctest --preset <cov>
#   3) COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/cmake/coverage/gcov_json_gate.py
#              --build-dir ${CMAKE_BINARY_DIR} --source-root ${PROJECT_SOURCE_DIR}
#              --threshold ${CPP_CORE_COVERAGE_THRESHOLD}
add_custom_target(coverage COMMAND ... )   # fails on non-zero; not USES_TERMINAL (CI-friendly)
```

The Python gate (design): walk `build/gcc16-coverage/**/*.gcno` (excluding `vcpkg_installed`),
invoke `gcov-16 --json-format` per object into a scratch dir, merge lines by
`(abs_file, line_number) -> count>0?`, print per-file table + uncovered lines, exit 1 below
`CPP_CORE_COVERAGE_THRESHOLD` (default 100). `gcov_json_gate.py` is deleted-at-first-run-safe
(idempotent). No network, no pip.

Presets to add to `cmake/presets/cpp-core.json` (configure + build + test + workflow):

| Preset | Kind | Contents |
|---|---|---|
| `p2996-tidy` (`configure`) | hidden `cc-p2996` + `cc-debug` + `cc-base` + `CPP_CORE_TIDY_ENABLED=ON` | configure only |
| `p2996-tidy` (`build`) | targets: `tidy` | the checks |
| `p2996-tidy` (`test`) | normal testRun (optional; not needed) | or omit |
| `gcc16-coverage` (`configure`) | `cc-gcc16` + `cc-debug` + `cc-base` + `CPP_CORE_COVERAGE=ON` + `CMAKE_BUILD_TYPE=Debug` | build dir `build/gcc16-coverage` |
| `gcc16-coverage` (`build`) | build cpp-core-tests | |
| `gcc16-coverage` (`test`) | `ctest` via `--preset gcc16-coverage` | runs instrumented binary |
| `gcc16-coverage` (`build` #2 or the aggregate `coverage` target) | `cmake --build --preset gcc16-coverage --target coverage` | the gate |
| `gcc16-coverage` (`workflow`) | configure → build → test → build `coverage` | one command: `cmake --workflow --preset gcc16-coverage` |
| `cmake-checks` (`configure`) | `cc-base` + no compiler constraint needed? - toolchain requires CPP_CORE_COMPILER; use `cc-gcc16` + `cc-debug` to be safe | build dir `build/cmake-checks` |
| `cmake-checks` (`build`) | targets: `cmake-checks` (+ `tidy` if enabled? no - keep separate) | |
| `cmake-checks` (`workflow`) | configure → build `cmake-checks` | one command check |

Naming follows the existing `<compiler>-<config>` + IWYU pattern (`p2996-iwyu` is the precedent for `p2996-tidy`/`gcc16-coverage`). `cmake-checks` is the first compiler-free preset; if that reads oddly, fold `cmake-checks` into `p2996-tidy` as an additional dependency and keep **three** new presets total.

`dev-mode.cmake` extension: after the IWYU include,

```cmake
if(CPP_CORE_TIDY_ENABLED)
  include(cmake/clang-tidy.cmake)
endif()
if(CPP_CORE_CMAKE_FORMAT_ENABLED)
  include(cmake/format.cmake)
endif()
```

`coverage.cmake` is included **unconditionally** from `dev-mode.cmake` but only builds the `coverage` target; the GCC-gate lives behind `gcc16-coverage` (cache var `CPP_CORE_COVERAGE=ON`), the gate target is a no-op-with-message otherwise? - No: keep it simple - create targets only when `CPP_CORE_COVERAGE` is ON (mirrors iwyu).

CI recommendation: a `checks` job runs `cmake --workflow --preset cmake-checks` + `--preset p2996-tidy` + `--preset gcc16-coverage`; the normal matrix stays unchanged.

---

## 5. OPEN QUESTIONS (need a run; do not answer in review)

1. **clang-tidy exit codes & `--verify-config`**: does the proposed `.clang-tidy` pass `clang-tidy --verify-config` on Homebrew 23.1.5, and does `clang-tidy -p <build> --config-file=.clang-tidy src/app.cpp` exit non-zero on any enabled-check warning (with `WarningsAsErrors` = enabled set), and parse the p2996 compile_commands.json without the `-freflection` `RemovedArgs` hack, and with it?
2. **Can clang-tidy parse `modules/logging/logging.cppm` at all** with `-x c++-module` standalone (Homebrew clang 23, `-std=c++26`, no module deps because the interface imports nothing)? If yes, is the diagnostic output usable (i.e., do enabled checks silently skip module decls via `SkipDeclsInModules` from PR #145630, and is that actually in 23.1.5 - or does the installed binary predate it)? → Decide the skip list empirically; the default stays "do not check the .cppm".
3. **BMI availability for importers**: can a BMI for `com.rsm.logging` produced by **Homebrew clang 23** be built from `logging.cppm` (std-free interface - plausible) and fed to clang-tidy via `-fmodule-file`/`-fprebuilt-module-path` for `src/main.cpp` and `tests/logging_test.cpp`? If yes, those two become checkable; if not (likely: p2996 flags/dialect mismatch), they stay skipped. Same for `src/reflection_demo.cpp` - impossible (`<meta>`) regardless.
4. **`clang-tidy` on `src/app.cpp`**: does the C++26 + cib-macro header parse cleanly with Homebrew clang 23 (`-std=c++26` + removed reflection flags), or do cib headers trip diagnostics/crashes? Measure, then finalize the enabled set (maybe drop `clang-analyzer-*` if CSA asserts on cib's macro machinery).
5. **gcov/.gcno layout for `CXX_MODULES`**: exact paths, exact `gcov-16 --json-format` invocation per module object, whether `-fprofile-abs-path` makes `files[].file` absolute, and whether GCC accepts `-fprofile-arcs` on the module interface TU unmodified.
6. **Consteval/template instrumentation**: do `scan_format`/`format_matches`/`format_string`'s ctor and the never-called `log`/`trace`/`debug`/`critical` template instantiations appear in gcov's JSON, and with what `count`/`unexecuted_block`? Decide line-gate semantics (Q3) after seeing real JSON.
7. **Actual baseline**: run `ctest --preset gcc16-coverage` on the unmodified tree once and record the full uncovered-line list (PARKED's hypothesis: trace/debug/critical, format specs, buffer truncation, cib/catalog path, quill_logger internals). Decide: new tests (preferred) vs justified exclusions; then the 100 gate can be turned on honestly.
8. **`gcov_json_gate.py` merge rule**: confirm that for lines instrumented in multiple TUs, "any count>0 ⇒ covered" yields the same result as summing (it does, for the >0 predicate) - and document that template lines common to TUs are merged by union, so the repository-total is the *union* of files.
9. **Catalog-generated file exclusion**: confirm `cpp-core-catalog.cpp` lands in the build dir and is automatically excluded by the path filter; confirm `cpp-core-test-code`'s `.gcno` merge behavior (object lib: same file `logging_test.cpp` - excluded by `tests/` filter anyway).
10. **ctest under coverage**: does `ctest --preset gcc16-coverage` return non-zero on test failure with default settings, and does the instrumented binary write `.gcda` atomically (counters are flushed at normal exit; `std::quick_exit`/signal would lose counts - ut's main returns normally)?
11. **`.cmake-format.yaml` vs `.cmake-format.json`** on the committed tree: if the YAML route is kept, the pipx install must gain pyyaml (`mise use pipx:cmakelang[yaml]` or project `.mise.toml`) - who pins it (a `mise.toml` in-repo, or documented Homebrew/pip install)? Or do we commit JSON? Owner decision needed before the gate can be green on a clean machine.
12. **Conformance commit**: is a one-shot `cmake-format -i` sweep acceptable (9/12 files change), and do we keep hand-wrapping via `.cmake-format.yaml` + `always_wrap` (e.g. never collapse `add_custom_target`) or accept cmake-format's canonical layout? Measure the post-conformance diff in review.
13. **`.clang-format` ↔ `.cmake-format.yaml` consistency**: line_width 100 both; anything else shared? (tab_size, line_ending, markup-off/reflow-off). Cosmetic but worth editing together.
14. **`.editorconfig` stale `indent_size = 3`**: confirm it should become 2 (or be scoped to git-handled files) - flag for the owner, out of this note's scope to change.
15. **CI image**: does CI (GitHub Actions runner) provide `gcov-16` at a known path or via `ubuntu-latest`'s GCC? If not, the gate must either fetch/install GCC 16 (package install - against constraints for this task, fine for CI) or keep coverage as a local/preset gate only for now.

---

## Appendix: URLs cited

- clang-tidy/modules: #63939, #62258, #145628→#145630, #178471, discourse.cmake.org/t/clang-tidy-cxx-modules/7938, discourse.llvm.org/t/clang-tidy-doesnt-find-standard-c-modules-.../71326, chuanqixu9.github.io/c++/2025/12/03/Clangd-support-for-Modules.en.html
- clang-tidy docs & releases: clang.llvm.org/extra/clang-tidy/index.html; releases.llvm.org/22.1.0/tools/clang/tools/extra/docs/ReleaseNotes.html; releases.llvm.org/23.1.0/tools/clang/tools/extra/docs/ReleaseNotes.html
- cmakelang: cmake-format.readthedocs.io/en/stable/{index,configuration,configopts,format-usage,format-example,lint-usage,lint-summary,lint-inline,lint-implemented}.html; pypi.org/project/cmakelang/
- gcov/coverage: gcc.sourceware.org/onlinedocs/gcc-14.1.0/gcc/Instrumentation-Options.html; gcc.sourceware.org/onlinedocs/gcc-14.1.0/gcc/Invoking-Gcov.html; man7.org/linux/man-pages/man1/gcov.1.html; gcovr.com/en/stable/guide/compiling.html; gcovr.com/en/stable/guide/gcov_parser.html; github.com/linux-test-project/lcov
- GCC modules: gcc.sourceware.org/onlinedocs/gcc/C_002b_002b-Compiled-Module-Interface.html

## What was verified how

- **[doc]**: all clang-tidy status claims, all cmakelang defaults and the YAML-without-pyyaml crash (crash path read in installed source), gcov JSON layout, flags.
- **[source]** (installed cmakelang 0.6.13): C0301←line_width, DIRECTORY-scope variable rule (public|private), foreach RANGE must be 3 positional args (E1120 false positive), C0113 required-by-convention COMMENT on add_custom_target, lint exit codes (1 on findings), format --check exit path, implemented-checks inventory, no pyyaml in the venv, markup/C0103 details.
- **[measured]** (read-only): cmake-lint default 80 and `--line-width 100` output (19 C0301, 9 C0103, 1 E1120, 1 C0113 listed above); cmake-format --check verdicts (9/12 files) and that `--dangle-parens` does not preserve the hand style; gcov-16 version/JSON v2; gcovr broken; lcov/genhtml missing; keg paths; /usr/bin/gcov is Apple LLVM 21; `.editorconfig` inconsistency; gitattributes LF.
- **[inferred]**: RemovedArgs need; BMIs version lock; coverage behavior of GCC with module TUs (Q2/Q5 are open questions, not answers); ctest exit-code propagation.
