# Decision Log — All 14 Owner Decisions

> **Every owner decision recorded with rationale, options, and impact**
> Theme: Modern Minimalist | Part of [Architecture Documentation](../../README.md)

---

## 📋 Decision Summary Table

| # | ID | Decision | Answer | Strength | Gates |
|---|----|----------|--------|----------|-------|
| 1 | **FMT-14** | Module path format dialect | **(c) Use fmtlib** — single formatter for both paths; depends on QUIL-1 | Judgement | Plan Step 7 |
| 2 | **TOOL-13** | cmake-format config format | **YAML** — add PyYAML via mise; keep `.cmake-format.yaml` | Judgement | Plan Step 8 |
| 3 | **TOOL-14** | cmake-format sweep | **Accept the sweep** — 9 of 12 files change; review diff | Judgement | Plan Step 8 |
| 4 | **BUILD-7** | Stable catalog location | **(a) CIB stable ID mechanism** per `logging.adoc` / `binary_stable_ids` | **STRONG** | DEF-6 |
| 5 | **BUILD-1** | Warning flags | **All at once** — `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` | Judgement | — |
| 6 | **BUILD-2** | Consumable outside | **Add install/export now** — `FILE_SET CXX_MODULES` + `install(EXPORT CXX_MODULES_DIRECTORY)` | Judgement | — |
| 7 | **BUILD-3** | Public header surface | **All three PRIVATE** — only `import com.rsm.logging;` is public | Judgement | — |
| 8 | **BUILD-4** | Keep clang23? | **Conditional** — add preset + triplet when Homebrew libc++ has `<meta>` | **STRONG** | — |
| 9 | **BUILD-5** | CI? | **No CI yet** — local presets (`mise run audit:verify/measure/acceptance`) | **STRONG** | — |
| 10 | **BUILD-8** | Catalog vs call sites check | **Yes** — small script, part of coverage work | Judgement | — |
| 11 | **BUILD-9** | Feature-check gate | **(c) Check only where answer gates code path** (HAVE_REFLECTION, module dialect, import std) | Judgement | — |
| 12 | **QUIL-9** | flush() caveat | **Document in both** — module header + README | **STRONG** | — |
| 13 | **ENV-2** | Abandoned build tree | **Keep + document** — add README explaining why | Judgement | — |
| 14 | **ENV-3** | ZAI_API_KEY | **Deferred** — not a cpp-core decision; owner's agent setup | **STRONG** | — |

---

## 📝 Detailed Decision Records

---

### 1. FMT-14 — Module Path Format Dialect

**Question**: The module path and catalog path have different format-string dialects (15 differences D1-D15). The difference is structural — fmt cannot enter the module interface. What should the module path do?

| Option | Description | Cost |
|--------|-------------|------|
| **(a) Document** | Write down the 15 differences (D1-D15) and stop | One document |
| **(b) Validate** | Validate format spec against argument **types** (move check into `format_string` ctor) | Real behaviour change — **renderer must change with it** |
| **(c) Move** | Move formatting out of module interface — one fmtlib serves both paths | Plan's last step; needs **QUIL-1** to succeed |

**Recommendation**: **(c) Use fmtlib** — single formatter for both paths; depends on QUIL-1

**Reasoning**:

- The hand-rolled formatter is **492 of 967 lines (51%)** of the library
- Acceptance bar target: that share goes **down**
- Two paths already disagree today: `{:>06}` → `000042` (module) vs `42` (catalog)
- `info("{:s}", 42)` compiles and is silently ignored where `std::format`/fmt reject it (DEF-5)
- **Constraint from Part 18**: (b) only coherent if module's *renderer* comes from same library as validator. A check that's present and wrong is worse than no check.

**If QUIL-1 fails**: Fall back to (a) document or (b) validate with fmt.

**Gates**: Plan Step 7 (move formatting out of module interface)

---

### 2. TOOL-13 — cmake-format Config Format

**Question**: cmake-format accepts `.cmake-format.yaml` or `.cmake-format.json`. The YAML config crashes on this machine (pipx cmakelang 0.6.13 lacks PyYAML). Which to use?

| Option | Description | Cost |
|--------|-------------|------|
| **JSON** | Commit `.cmake-format.json` | Config less pleasant to hand-edit |
| **YAML** | Keep `.cmake-format.yaml` | Install must gain PyYAML **and** pin the install |

**Answer**: **YAML — add PyYAML via mise; keep `.cmake-format.yaml`**

**Reasoning**:

- YAML is perfectly viable once PyYAML is installed and pinned
- The config is a machine-readable format either way
- Mise can manage the PyYAML dependency in the project environment

**Gates**: Plan Step 8 (wire formatting and checks into CMake)

---

### 3. TOOL-14 — cmake-format Sweep

**Question**: Running `cmake-format -i` changes 9 of 12 CMake files. Accept the canonical layout or encode hand-wrapping?

| Option | Description | Cost |
|--------|-------------|------|
| **Accept sweep** | cmake-format's canonical layout becomes project's layout | 9-file diff to review |
| **Keep hand layout** | Encode current wrapping in config | Config grows, fights tool on every new file |

**Answer**: **Accept the sweep** — 9 of 12 files change; review diff

**Reasoning**: Same reasoning that settled clang-format in `42d35bb`: project configuration should describe the project, not reconstruct a past hand-layout. Measure the diff in review — nine files, no behaviour change.

**Gates**: Plan Step 8

---

### 4. BUILD-7 — Stable Catalog Location

**Question**: Catalog IDs renumber on every regeneration (ID = rank in text order). The XML is MIPI Sys-T deployment collateral where IDs are wire identifiers. Where does the stable catalog live?

| Option | Description | Verdict |
|--------|-------------|---------|
| **(a) Committed file** | e.g., `cmake/catalog-stable.json` | ✅ **Recommended** |
| **(b) Build tree** | `${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.json` | ❌ **Does not work** — clean build renumbers |
| **(c) Leave it alone** | IDs are property of current message set | ⚠️ Only if XML not consumed as deployment collateral |

**Answer**: **(a) Use CIB's stable ID mechanism** per `logging.adoc` / `binary_stable_ids`

**Reasoning**: **STRONG** — The deciding fact is that the IDs are **wire identifiers**. A wire identifier that changes when a message is added is not an identifier. CIB's tooling already has the `STABLE_JSON` mechanism (`--stable_json`, `read_stable`, `assign_ids`); `cmake/catalog.cmake` just doesn't use it.

**Gates**: DEF-6 (catalog IDs renumber)

---

### 5. BUILD-1 — Warning Flags

**Question**: No compiler warning flags today — not `-Wall`, not `-Wextra`, not `-Wpedantic`, etc. What flags should the project use?

| Option | Description |
|--------|-------------|
| **Floor only** | `-Wall -Wextra` now, measure rest later |
| **All at once** | `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` |
| **Defer** | Wait until lane reopens |

**Answer**: **All at once** — `-Wall -Wextra -Wpedantic -Wconversion -Wshadow`

**Reasoning**: One sweep, one cleanup. All five flags enabled on both compilers from first implementation build. Noise handled in single pass. `-Wpedantic` on C++26 feature-test macros is known problematic but addressed directly.

---

### 6. BUILD-2 — Consumable Outside Repository

**Question**: No `install()` or `export()` in any CMakeLists.txt. Another project cannot `find_package(cpp-core)` or import the module. Should cpp-core be consumable outside?

| Option | Description |
|--------|-------------|
| **Defer** | Until module API stops moving (FMT-14 undecided, dialects differ) |
| **Add now** | `install(TARGETS ... FILE_SET CXX_MODULES ...)` + `install(EXPORT ... CXX_MODULES_DIRECTORY ...)` |
| **Minimal** | Install module BMI + BMI deps only |

**Answer**: **Add install/export now** — `FILE_SET CXX_MODULES` + `install(EXPORT CXX_MODULES_DIRECTORY)`

**Reasoning**:

- Three obstacles (from Part 18 §7.1): `format.hpp` is PRIVATE but public build-time dep; `internal.hpp` in GMF not in file set; export publishes quill/cib closure
- These are solved as part of implementation
- Install rules force API stability discipline earlier
- No consumer today, but forces discipline

---

### 7. BUILD-3 — Public Header Surface

**Question**: All three headers in `include/cpp-core/logging/` are PUBLIC. `quill_logger.hpp` includes `<quill/Logger.h>` but its comment says it's "the implementation's business, not part of the module's public interface". What is the public surface?

| Option | Description |
|--------|-------------|
| **Make quill_logger.hpp private** | Keep `internal.hpp` + `cib_quill.hpp` public |
| **Keep all three public** | Status quo |
| **All three PRIVATE** | Only the module (`import com.rsm.logging;`) is public |

**Answer**: **All three PRIVATE** — only `import com.rsm.logging;` is public

**Reasoning**:

- Module BMI is the **only** public interface
- `internal.hpp` → GMF, needed by importers via BMI
- `cib_quill.hpp` → catalog path API, reachable only through module's implementation
- `quill_logger.hpp` → implementation detail (5 lines, 21 unread lines)
- Install/export (BUILD-2) installs module BMI + BMI deps; headers not installed
- Consumers use `import com.rsm.logging;` only

---

### 8. BUILD-4 — Keep clang23?

**Question**: Toolchain and `cpp-core-check.cmake` accept clang23 with validation, but no clang23 triplet/preset. Part 3's clang-tidy needs Homebrew clang 23 for BMI, but clang23 can't build the project (no `<meta>`).

| Option | Description |
|--------|-------------|
| **Keep branch, no preset** | Validation code stays; no user-facing preset |
| **Remove entirely** | Delete validation branch from toolchain and check |
| **Conditional** | Add preset + triplet when Homebrew libc++ has `<meta>` |

**Answer**: **Conditional** — add clang23 preset + triplet when Homebrew libc++ has `<meta>`

**Reasoning**: **STRONG** — Third compiler the project **cannot build** is not a supported configuration. Homebrew's libc++ has no `<meta>`, so `src/reflection_demo.cpp` cannot parse. If clang-tidy needs a BMI, TOOL-3 measures whether the building compiler (GCC 16 or p2996) can provide it.

---

### 9. BUILD-5 — CI?

**Question**: No `.github/` directory and no git remote. Coverage gate, format check, clang-tidy check have no home until CI exists.

| Option | Description |
|--------|-------------|
| **No CI yet** | Keep gates as local presets |
| **Add workflow now** | Create `.github/workflows/` (testable via `act`/`jouet ci`) |
| **Defer explicitly** | Add CI only when remote exists |

**Answer**: **No CI yet** — local presets (`mise run audit:verify/measure/acceptance`)

**Reasoning**: **STRONG** — No remote = CI cannot run. A workflow with no remote rots. Gates are useful locally either way. Revisit when remote exists; design doesn't change, only where it runs.

**Superseded in part (2026-11-15)**: the repository now has a public GitHub remote and a workflow, `.github/workflows/ci.yml`, for the compiler-free checks (`hk check --all`, the audit checker, the lock check). The owner ruled the same day that cpp-core uses no paid services, so the workflow is advisory, not a required check, and the gate stays local: `hk check --all` before each merge. The coverage gate and the clang-tidy check still need a compiler, so they wait for the build lane.

---

### 10. BUILD-8 — Catalog vs Call Sites Check

**Question**: Catalog tooling's input regex drops non-matching lines; message set deduplicated by 64-bit hash — message can go missing silently. Link catches it (undefined `catalog<...>` symbol) but only at link time.

| Option | Description |
|--------|-------------|
| **Yes, in coverage** | Small script: count catalog entries vs `CIB_` call sites |
| **No** | Link-time check sufficient |
| **Defer to CI** | Only when CI exists |

**Answer**: **Yes** — small script, part of coverage work

**Reasoning**: Turns "undefined symbol at link" into "message X missing from catalog". Cheap, diagnostic, fits 100% coverage rule.

---

### 11. BUILD-9 — Feature-Check Gate

**Question**: ~20 of 30 compile items are checkable via `check_cxx_source_compiles` / `try_compile` at configure time. Should the build gain a feature-check gate?

| Option | Description |
|--------|-------------|
| **(a) Full gate** | One check per compile item, on every preset |
| **(b) On demand** | Scratch TU per item, when lane reopens |
| **(c) Gating only** | Check where answer gates code path; test for rest |

**Answer**: **(c) Check only where answer gates code path** — HAVE_REFLECTION, module dialect, import std capability

**Reasoning**:

- Cache variable worth having when something branches on it
- For rest, answer is a fact → coverage gate (100%) or tests
- Confines stale-answer problem to gating checks (stale = missing code path)
- Gives two decisive measurements a home: FMT-13 (preprocessor pass), MOD-11 (throwaway module)

---

### 12. QUIL-9 — flush() Caveat

**Question**: `flush_log()` blocks until messages up to timestamp are flushed. Quill warns: "Do not call from destructor of static object — may crash if ThreadContext destroyed first." Project's `flush()` says nothing about it. No bug today (main() calls from main).

| Option | Description |
|--------|-------------|
| **Document in header** | Two-line comment on `flush()` in `logging.cppm:89` |
| **Make safe** | Defer flush to backend thread (sync→async contract change) |
| **Document in both** | Module header + README |

**Answer**: **Document in both** — module header + README

**Reasoning**: **STRONG** — No bug today (main() calls from main), but consumer must know. Safe implementation would change sync→async — bigger than hazard warrants. Two-line caveat in `logging.cppm:89` and module header comment.

---

### 13. ENV-2 — Abandoned build/coverage-clang/

**Question**: `build/coverage-clang/` — abandoned clang source-based coverage experiment. Raw-profile version mismatch (clang v10 vs llvm-profdata 23.1.5 v11) makes it unusable. It's in the build tree (not tracked).

| Option | Description |
|--------|-------------|
| **Delete** | Housekeeping; 8 trees still corroborate closure |
| **Keep + document** | Add README explaining abandoned + why |
| **Defer** | Delete when lane reopens |

**Answer**: **Keep + document** — add README explaining it's abandoned and why

**Reasoning**: All 9 build trees agree on 106-header closure; this is one of them. Cross-check is 8 trees without it — still exceeds acceptance floor of 2. The coverage run was broken; the **include record** it left behind corroborates the other eight.

---

### 14. ENV-3 — ZAI_API_KEY

**Question**: `ZAI_API_KEY` for `zai-coding-plan` provider. Two saved Z.AI accounts belong to `zai` integration, not `zai-coding-plan`.

| Option | Description |
|--------|-------------|
| `opencode service set env` | One command, restarts background service |
| `opencode auth login zai-coding-plan` | Saved account, no restart |
| **Deferred** | Not a cpp-core decision; owner's agent setup |

**Answer**: **Deferred** — not a cpp-core decision; owner's agent setup

**Reasoning**: **STRONG** — This is the agent environment, not a cpp-core project decision. Listed only because it appeared in the original 13.

---

## 📈 Decision Impact Visualization

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
graph TD
    subgraph "Gate Implementation"
        FMT14c[FMT-14(c): fmtlib] --> STEP7[Step 7: Move formatting]
        QUIL1[QUIL-1: Codec N fields?] -.->|If YES| STEP7
        QUIL1 -.->|If NO| FMT14ab[Fallback: (a) or (b)]
    end

    subgraph "Enable Consumability"
        BUILD2[BUILD-2: Install/export now] --> BUILD3[BUILD-3: All headers PRIVATE]
        BUILD7[BUILD-7: CIB stable IDs] --> DEF6[DEF-6 fixed]
    end

    subgraph "Quality Gates"
        BUILD1[BUILD-1: All warnings] --> STEP3[Step 3: constexpr sweep]
        BUILD8[BUILD-8: Catalog check] --> COV7[COV-7: Catalog test]
        BUILD9[BUILD-9: Feature checks (c)] --> FMT13[FMT-13: Macro probe]
        BUILD9 --> MOD11[MOD-11: Throwaway module]
    end

    subgraph "Documentation"
        QUIL9[QUIL-9: flush() caveat] --> DOCS[Module header + README]
        ENV2[ENV-2: Keep coverage-clang] --> README2[README in build/]
    end
```

---

## 📋 Decision Quick-Reference for AI Agents

```yaml
decisions:
  FMT-14: "c"        # Use fmtlib; depends on QUIL-1
  TOOL-13: "YAML"    # Add PyYAML via mise
  TOOL-14: "sweep"   # 9 of 12 files change
  BUILD-7: "a"       # CIB stable ID mechanism
  BUILD-1: "all"     # -Wall -Wextra -Wpedantic -Wconversion -Wshadow
  BUILD-2: "install" # FILE_SET CXX_MODULES + install(EXPORT)
  BUILD-3: "private" # Only module is public
  BUILD-4: "cond"    # clang23 preset when libc++ has <meta>
  BUILD-5: "none"    # Local presets only
  BUILD-8: "yes"     # Catalog check in coverage
  BUILD-9: "c"       # Checks only where gates code path
  QUIL-9: "both"     # Module header + README
  ENV-2: "keep"      # + document
  ENV-3: "deferred"  # Not a cpp-core decision
```

---

*Part of the cpp-core Architecture Documentation Suite — [Back to Index](../../README.md)*
