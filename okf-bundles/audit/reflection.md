---
type: Audit Document
title: C++26 Static Reflection (P2996) Against the C++26 Text
description: Analysis of C++26 static reflection (P2996) against the C++26 draft text
resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/cxx26-features-audit/reflection.md
tags:
  - audit
  - reflection
  - cpp26
  - p2996
  - static-reflection
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - audit
  - reflection
  - cpp26
  - p2996
  - static-reflection
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/cxx26-features-audit
    title: Original audit documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## C++26 Static Reflection (P2996) Against the C++26 Text

**Date:** 2026-11-11
**Status:** research. Nothing here is applied to the build.

Every compiler-behaviour claim is sourced from documentation with a URL, or from an installed header with a file:line. Claims are marked **[doc]** (read from a source) or **[inferred]** (reasoned). Anything that can only be settled by compiling is in the open questions at the end.

### 1. The Verdict

C++26 static reflection was adopted into the working draft at the 2025 Sofia WG21 meeting **[doc]**. GCC 16 and clang-p2996 both implement `^^`, `std::meta::info` and the splicers `[: … :]` - but the range-returning metafunctions (`members_of`, `nonstatic_data_members_of`, `bases_of`, `enumerators_of`, `template_arguments_of`) **allocate**, and neither compiler implements constexpr allocation (P2680 / P1974), so a reflection range **cannot be walked in a constant expression** **[doc]**.

On top of that, cpp-core's logging module interface is deliberately standard-library-free, which excludes `<meta>`, `<string_view>`, `<span>` - and the Intel `stdx` headers, which pull in seven standard headers of their own (see [macro-reduction.md](macro-reduction.md), section 4) **[doc]**.

**The recommendation: adopt `^^` / `std::meta::info` only in the already-validated `reflection_demo.cpp` pattern; keep the hand-rolled `format.hpp` scanner and dispatch unchanged; wait for non-transient constexpr allocation (the C++29 horizon) before using reflection to generate compile-time formatting logic.**

### 2. The Summary Table

| Facility | In the C++26 draft? | Required? | GCC 16 | clang-p2996 | Applicability here | Verdict |
|---|---|---|---|---|---|---|
| the `^^` operator | yes - [expr.reflect] (N5046 §7.6) | required | `-freflection`, `__cpp_impl_reflection = 202603` | `-freflection`, `__has_feature(reflection)=1` | the core enabler; usable outside constant evaluation | **adopt now, in limited form** |
| `std::meta::info` | yes - §21.4.1 (N5046 §21.4, "Reflection") | required | `-freflection` | `-freflection` | the core enabler | **adopt now** |
| splicers `[: … :]` | yes - [basic.splice], [expr.prim.splice] | required | `-freflection` | `-freflection` | member access; not needed by the logger | **adopt now** |
| `members_of` / `nonstatic_data_members_of` / `bases_of` / `enumerators_of` / `template_arguments_of` | yes - [meta.reflection.member.queries] | required in principle, but **not walkable in `constexpr` today** | `-freflection`; **requires a second `access_context` argument** | `-freflection`; the 1-argument form compiles; expanding over a constexpr range is **not supported** | cannot be iterated in a `consteval` | **not yet** |
| the `access_context` parameter | yes - [meta.reflection.access.context], [meta.reflection.access.queries] | required | the 2nd argument is **required** (`access_context::unchecked()`) | the 1-argument form compiles; P1306R5 writes `std::meta::access::unprivileged()` | the source is **not portable** across the two toolchains as written | **blocker** |
| `define_static_string` / `define_static_array` (P3491R3) | **no** - removed from P2996 between R7 and R8, spun out to P3491R3, not in the draft | paper only | not in the standard library | behind `-freflection-latest` | excluded from the module interface anyway | **not yet / irrelevant** |
| expansion statements, `template for` (P1306R5) | yes - N5046 §8.7 | required | on by default | behind `-fexpansion-statements`; constexpr-range expansion **not supported** | cannot iterate a `members_of` result in `constexpr` | **not yet** |
| `std::define_static_string` (type to string) | paper only (P3491R3) | paper | no | `-freflection-latest` | excluded from the module interface anyway | **not yet / irrelevant** |
| non-transient constexpr allocation (P2680 / P1974 / P3554) | **no** - not in C++26; P2996R13 §2.3 lists it as a prerequisite | paper | no | no | the root blocker for walking reflection ranges in `constexpr` | **wait** (C++29) |
| annotations `[[= …]]` / `annotations_of` (P3394R4) | **no** | paper | no | `-fattribute-reflection` | could name format fields | **wait** (C++29) |
| `constexpr std::format` (P3391R2) | **yes** - the draft's synopsis declares `format`, `format_to`, `vformat_to` and `format_to_n` `constexpr`, with the feature-test macro `__cpp_lib_constexpr_format 202511L` | required in C++26 | **not implemented** (libstdc++ 16 defines no `__cpp_lib_constexpr_format`) | **not implemented** (libc++ 21 defines no `__cpp_lib_constexpr_format`; llvm#171292 is open) | relevant to the formatter, not to reflection | **wait for the libraries** |

**Sources for the table.** N5046 (the C++26 working draft, 2026-05-12): <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2026/n5046.pdf>. P2996R13: <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p2996r13.html>. P3491R3: <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p3491r3.html>. P3560R2: <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p3560r2.html>. P3394R4: <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p3394r4.html>. P1306R5: <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p1306r5.html>. P3391R2: <https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p3391r2.html>. GCC's dialect options: <https://gcc.gnu.org/onlinedocs/gcc/C_002b_002b-Dialect-Options.html>. clang-p2996's implementation notes: <https://github.com/bloomberg/clang-p2996/tree/p2996/P2996.md>.

### 3. The C++26 Standard Text

Draft: **N5046**, "Working Draft, Programming Languages - C++", 2026-05-12 **[doc]**.

#### The `^^` Operator

P2996R13 §4.1 introduces "a reflection operator (prefix `^^`) that computes a reflection value for its operand construct" **[doc]**. The revision history records that the operator was "changed from `^` to `^^` following adoption of [P3381R0]" **[doc]**. There is **no `::^` operator** - it was removed **[doc]**. The example in P2996R13 §3.1 is `constexpr auto r = ^^int; typename[:r:] x = 42;` **[doc]**.

#### `std::meta::info`

P2996R13 §2: reflections are "of an opaque type `std::meta::info`" **[doc]**. In N5046 that is §21.4.1, inside §21.4 "Reflection" **[doc]**. P2996R13 R9 to R12: "do not specify `sizeof(std::meta::info)`" **[doc]**. The header is `<meta>`, synopsis [meta.reflection.synop] **[doc]**.

#### The Member-Enumeration Facilities

P2996R13 §4.4.15 lists "`members_of`, `static_data_members_of`, `nonstatic_data_members_of`, `bases_of`, `enumerators_of`" **[doc]**. The draft section is [meta.reflection.member.queries] "Reflection member queries" (§21.4) **[doc]**. P3560R2 §2 is the decisive sentence: "Some (such as `members_of`) return `vector`" **[doc]**. P2996R13 §2.3 lists the non-transient constexpr allocation papers (P0784R7, P1974R0, P2670R1, P3554R0) as prerequisites **[doc]**.

#### `define_static_string`

**Not in N5046** **[doc]**. Removed from P2996 between R7 and R8: "removed `define_static_array`, `define_static_string`, and `reflect_invoke`" **[doc]**. Spun out to **P3491R3** "define_static_{string,object,array}" (2025-06-20) **[doc]**, which proposes, in `namespace std`, `define_static_string(R&&) -> range_value_t const*` and `define_static_array(R&&) -> span<range_value_t const>` **[doc]**. There is no `[meta.static.str]` section in either paper, and `define_static_string` is in `namespace std`, not `std::meta` **[doc]**.

#### The `access_context` Parameter

The draft sections are [meta.reflection.access.context] "Access control context" and [meta.reflection.access.queries] "Member accessibility queries" (§21.4) **[doc]**. `access_context` has the members `current()`, `scope()` and `naming_class()` (added between P2996R10 and R12 "in response to CWG feedback") **[doc]**. cpp-core's `src/reflection_demo.cpp:23-25` calls `std::meta::nonstatic_data_members_of(^^point, std::meta::access_context::unchecked())` **[doc]**. P1306R5 §2 writes `nonstatic_data_members_of(type, std::meta::access::unprivileged())` - a different spelling, and whether the two are the same API is unsettled **[doc / inferred]**.

#### The Rules on What a Reflection May Be Used In

The draft's constant-expression rules are in §7.7 [expr.const] **[doc]**. P2996R13 replaced "plainly constant-evaluated expressions" with **consteval blocks** (P3289R1, merged between R9 and R12) **[doc]**. "Producing an injected declaration from a non-plainly constant-evaluated context is prohibited for core constant expressions" **[doc]**. The operand of `^^` is unevaluated, and non-type template parameters and pack-index expressions cannot be operands of `^^` **[doc]**. Injected declarations must not escape their "cone of instantiation" **[doc]**. On errors: P3068R6 (throwing in constant evaluation) was adopted, and P3560R2 §2-§3 changes reflection failures from "not a constant expression" into throwing `std::meta::exception` **[doc]**.

### 4. What the Standard Requires, and What Is Only a Paper

**Required of a conforming C++26 implementation** (in N5046) **[doc]**: `<meta>`, `std::meta::info`, the `^^` operator, the splicers `[: … :]`, the metafunctions in [meta.reflection.*], and expansion statements (`template for`, §8.7).

**Paper only - not in the draft, and not required** **[doc]**:

- `define_static_string` / `define_static_array` - P3491R3 only.
- Non-transient constexpr allocation - P2680 / P1974 / P3554 only; P2996R13 §2.3 lists these as prerequisites but C++26 does not contain them.
- Annotations `[[= …]]` / `annotations_of` - P3394R4 only.
- P3096R12 (function parameter reflection) - listed by clang-p2996, but it is not needed by the logging path.

**The point for cpp-core:** a conforming C++26 implementation must provide `^^` and `std::meta::info`, but it is **not** required to make the range-returning metafunctions usable in constant evaluation - that needs P2680 / P1974, which C++26 does not have **[doc]**. So a project that must work on two implementations that are still catching up cannot rely on walking a reflection range in a `consteval` function.

### 5. What It Means for Each Hand-Rolled Construct in `format.hpp`

#### (a) The Compile-Time Type Traits - `is_same`, `remove_cvref_t`, `remove_extent_t`, `is_array`, `is_integral`, `is_floating_point`, `is_signed_v`, `type_identity_t` (`format.hpp:20-105`)

Verdict: **no, and reflection is the wrong tool.** These are plain language rules - type-category and transformation queries - that the type system answers on its own. Reflection enumerates *program structure* (members, bases, enumerators); there is no reflection metafunction that answers "is T an integral type?" **[doc / inferred]**. cpp-core implements them without `<type_traits>` for one reason only - the module interface must stay standard-library-free **[doc]**. The blocker is the standard-library-free rule, not reflection.

#### (b) The `consteval` Scanner `scan_format` and the `format_matches` Argument-Count Check (`format.hpp:220-294`)

Verdict: **not yet.** `scan_format` walks the format string's *text* character by character; no reflection metafunction operates on the contents of a string literal, so reflection cannot replace the parse **[inferred]**. The argument-count check already works through `sizeof...(Args)` without reflection **[doc]**. A reflection-driven count would need to walk a `members_of`-style range in a `consteval`, which is blocked by the allocation limitation below **[doc]**.

#### (c) Naming a Member or a Type as a Compile-Time String - Named Fields Like `{"count": 42}` Instead of `{0}` (`format.hpp:239-241, 575-578`)

Verdict: **not yet.** `identifier_of(reflection)` can yield an entity's name as a `std::string_view` (P2996R13 §4.4.11) **[doc]**, but:

1. Collecting the names means walking `members_of`, which is blocked in `constexpr` by allocation;
2. Producing named output needs `<string_view>` and `<span>`, and the module interface may not name the standard library **[doc]**;
3. The Intel `stdx` alternative is excluded too - `stdx/ct_string.hpp:8-14` includes `<array>`, `<concepts>`, `<cstddef>`, `<iterator>`, `<string_view>`, `<type_traits>` and `<utility>` **[doc]**.

Wait for non-transient constexpr allocation and for the annotations story (P3394R4) to settle.

#### (d) Replacing the Per-Type `format_value` Dispatch with a Generated Formatter (`format.hpp:423-463`)

Verdict: **not yet, and not worth it.** `format_value` dispatches per *argument type*; reflection enumerates *class members* and gives no "how do I format T" answer **[inferred]**. Generating the dispatch would mean walking an allocating range in `consteval` (blocked) **[doc]**, would raise compile time (clang-p2996's implementation notes warn that memory usage is "in many cases wasteful") **[doc]**, and would make the code less readable than the explicit `if constexpr` chain it replaces.

### 6. The Blockers, Precisely

| # | Blocker | Detail | Source |
|---|---|---|---|
| B1 | **constexpr allocation (the primary blocker)** | Every range-returning metafunction allocates and returns a `vector`-like range. Neither GCC 16 nor clang-p2996 implements P2680 (constexpr `operator new`) or P1974, so a `std::meta` range cannot be walked in a constant expression. P1306R5 §3.2: "directly expanding over `members_of(^^T)` [is] ill-formed for C++26"; the suggested workaround `define_static_array(...)` is P3491 (not in the draft) and needs `<span>` and `<meta>`. | P3560R2 §2; P2996R13 §2.3; P1306R5 §3.2 **[doc]** |
| B2 | **the GCC / libc++ `access_context` API difference** | GCC 16's `members_of` / `nonstatic_data_members_of` / `bases_of` **require** a second `access_context` argument; libc++'s 1-argument form also compiles, so the source is not portable as written. | `src/reflection_demo.cpp:23-25` **[doc]**; verified on this machine |
| B2b | **the `access_context` spelling is unsettled** | P1306R5 writes `std::meta::access::unprivileged()`; the project uses `std::meta::access_context::unchecked()`. Whether they are the same API under different names is unknown. | P1306R5 §2 **[doc / inferred]** |
| B3 | **the standard-library-free module interface** | The global module fragment is attached to the global module, and standard headers included there collide with the importing translation unit's own standard headers (GCC: `std::__is_constant_evaluated()` redefinition; Clang: `std::__promote_t` alias redefinition). `<meta>`, `<string_view>`, `<span>` and Intel's `stdx` are all excluded. | `modules/logging/logging.cppm:9-19` **[doc]**; `stdx/ct_string.hpp:8-14` **[doc]** |
| B4 | **`std::format` is not `constexpr` *in the implementations*** | C++26 **does** make `std::format` constexpr - P3391R2 was adopted at Kona in November 2025, and the draft's synopsis declares `format`, `format_to`, `vformat_to` and `format_to_n` `constexpr`, with `__cpp_lib_constexpr_format 202511L`. **Neither standard library on this machine implements it**: libstdc++ 16 defines no `__cpp_lib_constexpr_format` and declares `std::format` without `constexpr`; libc++ 21 defines no `__cpp_lib_constexpr_format` either (`__cpp_lib_format` is still `202110L`), and llvm#171292 is open. The underlying reason is that `std::string` is not constexpr in either library yet either. | P3391R2 **[doc]**; N5046 feature-test macro table **[doc]**; the installed headers **[doc]** |
| B5 | **`define_static_string` is not in the C++26 draft** | Removed from P2996 between R7 and R8; spun out to P3491R3, which is not in the draft. Only behind `-freflection-latest` in clang-p2996. | P2996R13 revision history; P3491R3 **[doc]** |
| B6 | **Annotations are not in C++26** | P3394R4 (`[[= …]]`, `annotations_of`) is not in N5046; behind `-fattribute-reflection` in clang-p2996. | P3394R4; clang-p2996 P2996.md **[doc]** |
| B7 | **`std::meta::exception` in `consteval`** | P3068R6 (throwing in constant evaluation) was adopted and P3560R2 §2-§3 changes reflection errors to throw `std::meta::exception`. Whether both compilers do this reliably for diagnostics is untested. | P3560R2 §2-§3 **[doc]** |

### 7. The Recommendation

**Adopt now** - usable today, outside constant evaluation:

- the `^^` operator, `std::meta::info` and the splicers `[: … :]` - both compilers implement them **[doc]**;
- **only** in the already-validated `reflection_demo.cpp` pattern: call `.size()` on a temporary `nonstatic_data_members_of(...)` result (`src/reflection_demo.cpp:23-25`) **[doc]**;
- **not** inside `modules/logging/` today.

**Wait for**:

- walking reflection ranges in a `consteval` - until non-transient constexpr allocation (P2680 / P1974 / P3554) lands, the C++29 horizon **[doc]**;
- `define_static_string` / `define_static_array` - until P3491 is adopted **[doc]**;
- named format fields via `identifier_of` plus annotations - until C++29, and only if the module interface may name the standard library **[doc]**.

**Irrelevant for this project**:

- `constexpr std::format` as a *reflection* feature - it is a library change, and the implementations are not there yet (B4) **[doc]**;
- the type traits - plain type rules, reflection is the wrong tool **[inferred]**;
- a generated replacement for the `format_value` dispatch - per-argument-type, not per-member; high compile-time cost, poor readability **[inferred]**.

**Bottom line:** keep `scan_format`, `format_matches` and `format_value` exactly as they are. Adopt `^^` / `std::meta::info` only where it is already validated. Everything else waits for non-transient constexpr allocation and for a settled `access_context` API.

### 8. Open Questions - These Need a Compile

1. Do clang-p2996's 1-argument `members_of` form and GCC's 2-argument form compile the *same* source, or is the incompatibility only in the standard-library wrapper? **[inferred]**

2. Are `std::meta::access::unprivileged()` (P1306R5) and `std::meta::access_context::unchecked()` (P2996R13, and what the project uses) the same API under different names, or distinct? **[inferred]**

3. Does `std::meta::exception` throwing work reliably inside `consteval` reflection calls in both compilers, for diagnostics like cpp-core's "format string does not match"? **[inferred]**

4. When libstdc++ and libc++ implement P3391R2, does `std::format_string<Args...>` accept every format string the project's own scanner accepts? The two dialects are not identical - the hand-rolled scanner rejects named arguments and a bare `}` (`format.hpp:239-241, 270`), and `std::format_string` rejects a few things the scanner allows. **[inferred]**
