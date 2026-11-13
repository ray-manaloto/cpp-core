# What the module's format strings actually mean

**Date:** 2026-11-12
**Status:** research. **Nothing here is applied to the build.** This part compares the three
format-string dialects that are live in this project at the same time, because part 9 settled *which
library formats* but not *which dialect the project ends up with*.

## The question

There are two logging paths, and after part 9's decision they use **two different format-string
dialects**:

| Path | Who formats | Which dialect |
|---|---|---|
| the **module path** (`com::rsm::logging::info(...)`) | the module itself, in the module interface (`modules/logging/format.hpp`) | **the module's own** - a hand-rolled scanner and parser |
| the **catalog path** (`CIB_INFO(...)`) | quill's backend thread, through quill's bundled fmt (`fmtquill`) | **fmt's**, which is the C++26 `std::format` dialect |

Part 9's decision was **fmt over `std::format`**, and fmt cannot enter the module interface (a
textual `#include` in a module unit yields global-module declarations). So the module's dialect
**stays**. The question this part answers is therefore not "which library" - it is:

> **What does the module's dialect accept, and where does it differ from the dialect the other path
> uses?** And: what does that mean for the plan?

## The three grammars

### 1. The standard's grammar

From the C++26 draft, [format.string.std] (`https://eel.is/c++draft/format.string`):

```
std-format-spec : fill-and-align_opt sign_opt #_opt 0_opt width_opt precision_opt L_opt type_opt
fill-and-align  : fill_opt align
fill            : any character other than { or }
align           : one of < > ^
sign            : one of + - space
width           : positive-integer { arg-id_opt }
precision       : . nonnegative-integer { arg-id_opt }
type            : one of a A b B c d e E f F g G o p P s x X ?
```

And the rule that governs everything else ([format.string.general]/5):

> If format-spec does not conform to the format specifications for the argument type referred to by
> arg-id, **the string is not a format string for args**.

That is the rule the module does not implement. The rest of this part is the consequence.

### 2. fmt's grammar

fmt 12.2.1 implements that grammar and **checks it against the argument's type**. Read from
`build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/fmt/base.h`:

```cpp
// base.h:1503-1512 - the '0' option
case '0':
  enter_state(state::zero);
  if (!is_arithmetic_type(arg_type))
    report_error("format specifier requires numeric argument");
  if (specs.align() == align::none) {
    // Ignore 0 if align is specified for compatibility with std::format.
    specs.set_align(align::numeric);
    specs.set_fill('0');
  }

// base.h:1473-1477 - every presentation type is checked against the argument's type
constexpr auto operator()(pres pres_type, int set) -> const Char* {
  if (!in(arg_type, set)) report_error("invalid format specifier");
  ...
```

The state machine is the standard's (`base.h:1440`): `start, align, sign, hash, zero, width,
precision, locale` - the same eight states, in the same order. The type set is the standard's too:
`'d' 'x' 'X' 'o' 'b' 'B' 'e' 'E' 'f' 'F' 'g' 'G' 'a' 'A' 'c' 's' 'p' '?'` (`base.h:1530-1558`).

Two details worth carrying:

- fmt **ignores `0` when an alignment is given**, and says so in a comment - "for compatibility with
  std::format" (`base.h:1508-1509`).
- fmt's default floating-point presentation is the **shortest round-trip** representation
  (`format.h:2991-3005`, "Generate the shortest representation"; Dragonbox at `format.h:3496`).

### 3. The module's grammar

The module's format string has two passes: a **compile-time scanner** and a **runtime parser**.

The scanner (`modules/logging/format.hpp:220-281`) walks the string, counts the replacement fields,
and finds the *boundaries* of each format specification - and that is all it does with it:

```cpp
// format.hpp:244-250 - the specification is skipped, not parsed
if (j < length && text[j] == ':') {
  // The format specification: scan it to the closing brace.
  ++j;
  while (j < length && text[j] != '}') {
    ++j;
  }
}
```

The parser (`format.hpp:477-514`) runs at *runtime*, once per message, and it is permissive:

```cpp
// format.hpp:511-513 - any character at the end is taken as the type character
if (i < length) {
  spec.type = text[i];
}
```

So: **the module checks the shape of the format string at compile time, and it does not check the
format specification at all - not at compile time and not at run time.**

## What the module gets right

The brace structure is right, and it matches the standard exactly:

| Rule | The standard | The module |
|---|---|---|
| `{{` and `}}` are escapes | [format.string.general]/1 | `format.hpp:227-230`, `:265-269` |
| a lone `}` is invalid | [format.string.general]/1 | `format.hpp:270-271` |
| automatic and manual indexing may not be mixed | [format.string.general]/4 | `format.hpp:276-279` |
| a manual index must be in range | [format.string.general]/2 | `format.hpp:290-292` (but stricter - see D9) |
| the field count must match the argument count | [format.string.general]/4 | `format.hpp:293` |

The layout rules are right too:

| Rule | The standard | The module |
|---|---|---|
| `<` is the default for strings, characters and `bool`; `>` for the other arithmetic types | Table 104 | `format.hpp:428` (`bool`), `:432` (`char`), `:419` (integers), `:452` (floats) |
| centring puts ⌊n/2⌋ fill characters before and ⌈n/2⌉ after | Table 104 | `format.hpp:183-191` |
| a fill character is only a fill when the next character is an alignment | Note 3 of [format.string.std]/3 | `format.hpp:479-486` |

So the module is not a bad implementation of the standard's dialect. It implements the **structure**
of the dialect faithfully, and it implements the **specification** loosely.

## The divergences

Every row is read from the source. The "what happens" column is what the code does - **not** what a
run has confirmed, because the build lane is parked.

| # | The format string | `std::format` and fmt | The module path | Where |
|---|---|---|---|---|
| **D1** | any spec that does not fit the argument's type - `{:s}` on an `int`, `{:d}` on a `double`, `{:z}` on anything | **a compile-time error** | **compiles**, and the offending part is ignored | `format.hpp:244-250` (the scanner skips the spec), `format.hpp:511-513` (any character is a type) |
| **D2** | `{:>06}` | "    42" - the `0` is ignored when an alignment is present ([format.string.std]/8) | "000042" - the zero padding happens regardless | `format.hpp:395-398` |
| **D3** | `{}` with `1234567.0` | "1234567" - the shortest round-trip | "1.23457e+06" - `%g`, six significant digits | `quill_logger.cpp:150-155` |
| **D4** | `{:f}` with `3.5` | "3.500000" - the precision defaults to 6 (Table 110) | "3.5" - `'f'` is treated like the default | `quill_logger.cpp:131-137` (this is DEF-2) |
| **D5** | `{:+}` with `3.5` | "+3.5" - the sign option applies to floating point (Table 105) | "3.5" - the float path never sees the sign | `format.hpp:487-490` reads it, `quill_logger.cpp:121-167` never gets it |
| **D6** | `{:#g}` with `3.0` | "3.00000" - the alternate form keeps the trailing zeros for `g`/`G` ([format.string.std]/7) | "3" - the alternate flag is ignored on the float path | `quill_logger.cpp:121-167` |
| **D7** | `{:L}` with `1234` | "1,234" - the locale form | "1234" - `'L'` is taken as the type character and dropped | `format.hpp:511-513` |
| **D8** | `"{:{}}"` - a dynamic width | valid: `width : positive-integer { arg-id_opt }` | **a compile-time error** - the inner `}` ends the field and the outer `}` is then a lone `}` | `format.hpp:247-250` and `:270-271` |
| **D9** | `"{0} {0}"` with one argument | valid - only the *largest* index has to be in range ([format.string.general]/2) | **a compile-time error** - the field count may not exceed the argument count | `format.hpp:290-292` |
| **D10** | `{:B}` with `42` | "101010" - the uppercase binary type (Table 107) | "42" - `'B'` is not in the integer type table, so it falls through to base 10 | `format.hpp:333-352` |
| **D11** | `{:c}` with `65` | "A" - the character type (Table 107) | "65" - `'c'` is not in the integer type table, so it falls through to base 10 | `format.hpp:333-352` |
| **D12** | `{:d}` with `'x'` | "120" - for `charT`, `d` converts to the unsigned value of the underlying type (Table 108) | "x" - the `char` branch runs before the integral branch | `format.hpp:431-433` |
| **D13** | `{:#o}` with `0` | "0" - the alternate octal prefix is empty when the value is zero (Table 107) | "00" - the prefix "0" is always written | `format.hpp:377-378` |
| **D14** | `{:d.3}` with `42` | **a compile-time error** - precision is only valid for floating-point and string types ([format.string.std]/15) | "42" - the precision is ignored on the integer path | `format.hpp:329-421` never reads `spec.precision` |
| **D15** | `{:?}` with `"a\n"` | "a\\n" - the escaped-string type (Table 106) | "a" followed by a real newline - the type character is dropped | `format.hpp:511-513` |

Three of these deserve a note of their own.

**D1 is the important one.** It is not a formatting difference; it is the difference between a
*checked* format string and an *unchecked* one. `std::format` and fmt reject `"{:s}"` on an `int`
at compile time, with the type of the argument in the diagnostic. The module accepts it and prints
the number. A user who writes a format string for the CIB path and moves it to the module path gets
no error - they get a different number in the log.

**D3 is the dangerous one.** `%g` has six significant digits by default. A log line that says
"1.23457e+06" where the value was 1234567 has silently lost precision, and nothing in the output
says so. This is the same defect as DEF-2, seen from the other side: DEF-2 records that `{:f}` is
wrong; D3 records that **the default is wrong too**, and the default is what every unadorned `{}`
uses.

**D8, D9 and D15 are the module being *stricter* or *older*.** Rejecting `"{:{}}"` and `"{0} {0}"`
at compile time is a limitation, not a defect - the module simply does not implement those forms.
They are listed because a format string that `std::format` accepts will not compile here, and that
is a portability fact a user needs to know.

## The consequence: the two paths in one project disagree

This is the part that matters for the review. **The same format string, in the same project, at the
same call site, produces different output depending on which path it goes through.**

```cpp
com::rsm::logging::info("{:>06}", 42);   // the module path  -> "000042"   (D2)
CIB_INFO("{:>06}", 42);                  // the catalog path -> "    42"   (fmt's rule)

com::rsm::logging::info("{}", 1234567.0); // the module path -> "1.23457e+06"  (D3)
CIB_INFO("{}", 1234567.0);                // the catalog path -> "1234567"
```

Both paths are documented in the root `README.md` as the project's two logging paths, and the
README's "What the two paths share" section lists *call site fidelity*, *levels*, *modules*,
*threading* and *ODR* as the things they share. **The dialect is not one of them**, and until this
part it was not recorded anywhere.

That is **DEF-4**: the two logging paths do not share a format-string dialect, and the differences
are silent.

The root README also claims, under "What the two paths share":

> **Threading:** quill formats on its backend thread, so runtime arguments are queued rather than
> formatted on the calling thread.

That is true of the **catalog path** and false of the **module path**. The module path formats the
message *on the calling thread* - `logging.cppm:110-112` builds the message in a stack buffer
before `emit()` is called - and then `emit()` copies it into a `std::string`
(`quill_logger.cpp:118`), so **each module-path message costs one copy of its bytes on the calling
thread, plus a heap allocation for any message longer than the small-string threshold** - 22
characters on libc++ 21, 15 on libstdc++ 16 (part 18, section 4). The catalog path queues the
*arguments* and lets the backend format them. The two paths
have different performance profiles as well as different dialects.

(The README was corrected when this part was written.)

## The consequence for the plan

The plan in [PARKED.md](../../PARKED.md) is unaffected in its order, but its steps divide the
divergences in two.

**Step 5 (fmt in `format_double`) fixes D3 and D4 - in both paths.** The module's float formatting
already happens *in the implementation translation unit*: `format_value` calls `format_double`
(`format.hpp:447`), which the module only *declares* (`internal.hpp:52-53`) and the implementation
*defines* (`quill_logger.cpp:121-167`). So replacing `snprintf` with fmt there changes what the
**module path** prints as well - "1234567" instead of "1.23457e+06", and "3.500000" instead of
"3.5" - and the float rows of the table stop being divergences at all. This is DEF-2, and it is
already step 5 of the plan.

**Everything else stays where it is.** D1, D2 and D5 to D15 are the module's *own* handling of the
format specification - the parser in `parse_spec`, the integer formatter, the padding rules - and
all of it lives in the module interface, where fmt cannot go. `constexpr` (step 3) does not change
any of it: `constexpr` changes *when* the formatting happens, not *what* it means.

**So the divergence is structural after step 5.** As long as the module parses the format
specification inside its own interface, the module path has its own dialect, and the only way to
make the two paths agree completely is to move the formatting out of the module interface - which is
the big change at the end of the plan, and the one that needs the `quill::Codec` experiment
(QUIL-1).

That leaves a decision the owner has to make, and it is **FMT-14**:

> **Option (a) - document the dialect.** Say in the README that the module path implements a subset
> of the C++26 format-spec grammar, list the differences, and stop there. Cheap, honest, and it
> leaves the two paths different.
>
> **Option (b) - validate the specification.** Make the module reject a format specification that
> does not fit the argument's type, the way `std::format` and fmt do. This is a real piece of work
> and it changes the shape of the check: `format_matches<arg_count>` (`format.hpp:284-294`) only
> knows the *number* of arguments, while the validation needs their *types* - so the check would
> have to move into `format_string`'s constructor (`logging.cppm:66-76`), which does know them
> (`format_string<detail::type_identity_t<Args>...>`). It would fix D1, and with it most of the
> others, because a rejected specification cannot be silently ignored.
>
> **Option (c) - move the formatting out of the module interface.** The plan's last step. It makes
> the two paths agree by construction, because there would be one dialect. It is also the most
> expensive and the most uncertain.

My recommendation is **(a) now, (b) if the dialect ever becomes public API, (c) only if the
`quill::Codec` experiment succeeds** - which is the same ordering the rest of the plan already
uses, and it keeps the parked work parked.

## The method

- The standard's grammar and rules: **[doc]** - the C++26 draft, `https://eel.is/c++draft/format.string`,
  read on 2026-11-12.
- fmt's behaviour: **[source]** - `build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/fmt/base.h`
  and `format.h`, read at the installed version (`FMT_VERSION 120201`, `base.h:24`).
- The module's behaviour: **[source]** - `modules/logging/format.hpp`,
  `modules/logging/logging.cppm`, `src/logging/quill_logger.cpp`, read in full.

**Nothing was built, configured or run.** The "what happens" column is what the code does, read from
the source; a run would confirm it, and that is part of the coverage work (COV-1 to COV-10) when the
build lane reopens.
