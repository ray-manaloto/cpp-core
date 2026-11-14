# Are the catalog IDs the same under both compilers?

**Date:** 2026-11-12
**Status:** research. **Nothing here is applied to the build.** This part answers **BUILD-6** - the
last open question that needed no compile - and it turns out to have a second half that nobody had
asked about: the IDs are stable across *compilers*, and they are **not** stable across *releases*.

## The question

`cmake/catalog.cmake` runs cib's `gen_str_catalog()` over the object files of the libraries that
log. The tool reads the undefined symbols with `nm`, works out which log messages they stand for,
assigns each one an integer ID, and writes the IDs into the generated `cpp-core-catalog.cpp`, the
JSON and the XML.

The ID ends up in the log line's tag field:

```text
07:01:52.811080209 [51816462] app.cpp:28 LOG_INFO  cpp-core [cpp_core id=1 mod=0] compile-time formatted: the answer is 42
```

**BUILD-6** asked: *are the IDs stable across compilers?* `nm` output depends on the compiler's
mangling, so the same source might produce different IDs under `gcc16` and `p2996` - and if the
application and the tests disagreed about which ID is which message, the catalog would be wrong.

## The answer

**Yes - and not by luck.** The ID is a function of the **message text**, and the text is carried in
the message's *type*, which both compilers spell the same way. The mangling contributes nothing to
the ID.

### The measurement

Nine catalogs are on disk from before the build lane was parked - two compilers, four build
configurations, and two different build times:

| Build tree | Compiler | Generated | Catalog JSON |
|---|---|---|---|
| `build/gcc16-debug/` | GCC 16.2.0 | 2026-11-11 15:35 | `cb34746734a4946ecd117471ae881b26` |
| `build/gcc16-asan/` | GCC 16.2.0 | 2026-11-11 15:01 | `cb34746734a4946ecd117471ae881b26` |
| `build/gcc16-release/` | GCC 16.2.0 | 2026-11-11 15:01 | `cb34746734a4946ecd117471ae881b26` |
| `build/p2996-debug/` | clang-p2996 21.0.0git | 2026-11-11 15:35 | `cb34746734a4946ecd117471ae881b26` |
| `build/p2996-asan/` | clang-p2996 21.0.0git | 2026-11-11 15:01 | `cb34746734a4946ecd117471ae881b26` |
| `build/p2996-release/` | clang-p2996 21.0.0git | 2026-11-11 15:01 | `cb34746734a4946ecd117471ae881b26` |
| `build/p2996-tsan/` | clang-p2996 21.0.0git | 2026-11-11 15:01 | `cb34746734a4946ecd117471ae881b26` |
| `build/p2996-iwyu/` | clang-p2996 21.0.0git | 2026-11-11 15:01 | `cb34746734a4946ecd117471ae881b26` |
| `build/coverage-clang/` | clang-p2996 21.0.0git | 2026-11-11 15:58 | `cb34746734a4946ecd117471ae881b26` |

**All nine are byte-identical** - the JSON and the XML outright, and the generated C++ in its body
(the generated C++ differs only in its four header lines, which record the tool's path and the
timestamp; the body is byte-identical in all nine).

### The mechanism

Four steps, all read from the installed tool
(`share/intel-cib/python/cib/gen_str_catalog.py`; the two installed copies are byte-identical, md5
`9c516bdb409fb8f0b03b1d0faf0e5695`).

**1. The message is carried in the message's *type*.** cib declares the catalog as

```cpp
// log_binary/catalog/catalog.hpp:7
template <char...> struct string {};

// log_binary/catalog/catalog.hpp:15
template <typename, auto, typename...> struct undefined;

// log_binary/catalog/catalog.hpp:24
template <typename> extern auto catalog() -> string_id;
```

and the log call instantiates `catalog<Message>()`, where `Message` carries the message's
characters as a `char` pack (`encoder.hpp:113-124`, `mipi_builder.hpp:144`). The `-1` in the
symbol is the *id placeholder*: the symbol reads

```text
unsigned int catalog<sc::message<sc::undefined<sc::args<>, -1,
    sc::string<(char)99, (char)111, (char)109, ...>, sc::tags<>, sc::named_args<>>>>()
```

and the generated file supplies the specialization that returns the real ID.

**2. The tool reconstructs the message *text* from the character codes.**

```python
# gen_str_catalog.py:175-177
string_tuple = m.group(4).replace("(char)", "")
return cls(
    "".join((chr(int(c)) for c in re.split(r"\s*,\s*", string_tuple))),
    ...
```

The text is recovered exactly - the *characters*, not the mangling.

**3. The messages are sorted by that text.**

```python
# gen_str_catalog.py:228-229
def __lt__(self, other):
    return self.text < other.text
```

**4. The IDs are handed out in that order.**

```python
# gen_str_catalog.py:300-304
def assign_ids_with(items, id_fn):
    sorted_items = sorted(items)
    for i in sorted_items:
        i.id = id_fn(i)
    return list(sorted_items)
```

So, with no stable input, **the ID of a message is its rank among the messages, in text order**.
For this project's three messages that is exactly what the catalog shows:

| text | rank | ID |
|---|---|---|
| `cib levels map onto quill levels: INFO -> Info, WARN -> Warning` | 0 | 0 |
| `compile-time formatted: the answer is 42` | 1 | 1 |
| `errors are logged too, at quill's Error level` | 2 | 2 |

**The mangling never enters the calculation.** It only has to be *parseable*.

### Why the type encoding cannot drift between the two compilers

The one part of the symbol that could have differed is `sc::args<...>`, the list of runtime
argument types. It does not, because cib's catalog encoder accepts only *packable* types:

```cpp
// log_binary/catalog/arguments.hpp:31-33
concept packable = signed_packable or unsigned_packable or
                   float_packable or enum_packable;
```

and encodes each one as `encode_32<T>`, `encode_64<T>`, `encode_u32<T>`, `encode_u64<T>` or
`encode_enum<T, underlying, size>` (`arguments.hpp:9-13`, `:47-75`). The only type names that can
appear are **fundamental types** (`int`, `long`, `float`, `double`, ...) and **the user's own enum
type** - and those are spelled identically by GCC and Clang. There is no `std::string` in the
catalog path at all, because `std::string` is not packable.

So the entire type that carries the message is compiler-independent, for every message the catalog
can represent.

### And the linker is the backstop

Suppose a compiler *did* spell the symbol differently - a different demangler, a different
character-constant spelling. Two things would happen:

- the tool's input regex is `^.*unsigned (?:int|long) (catalog|module)<(.+?)>\(\)$`
  (`gen_str_catalog.py:342`), and a line that does not match is **dropped silently** - so the
  message would go missing from the catalog; or
- the character codes would be misread, so the catalog would hold a *different* text under the
  same ID.

In both cases the generated `cpp-core-catalog.cpp` would not define the specialization the
application needs, and the application's `catalog<...>` symbol would stay undefined - **a link
error**. The catalog cannot drift from the source without the link failing. That is why the
observation above is not the only thing that makes this safe.

## What the answer does *not* prove

- **The project has no message with a runtime argument.** All three catalog messages have
  `"arg_types": []`: the two with `{}` in the source have *compile-time* arguments, which cib
  folds into the format string at compile time, so the catalog text is the **folded** text
  (`"compile-time formatted: the answer is 42"`, not `"compile-time formatted: the answer is {}"`).
  So the `sc::args<...>` path - the one part of the encoding that could have carried a
  compiler-dependent type name - has never been exercised here. The argument above says it *cannot*
  drift; it has not been *observed* not to.
- **The dedup is a 64-bit hash.** `key()` is `hash(self.text) ^ hash("".join(self.args))`
  (`gen_str_catalog.py:212-213`), and Python salts `str` hashes per process. Two distinct messages
  whose XOR-hashes collide would be silently merged (`gen_str_catalog.py:352`), and one of them
  would never get an ID - which is again a link error, not a wrong ID. The probability is
  negligible (of order n²/2⁶⁵), but it is not zero, and it is a property of the *tool*, not of this
  project.

## The corollary: the IDs are not stable across *releases*

This is the half nobody had asked about, and it is the more consequential one.

**The rule** - *the ID of a message is its rank among the messages, in text order* - means that
**adding one message can renumber every message after it.** A new message whose text sorts first
takes ID 0, and the existing messages shift to 1, 2, 3. The XML is **MIPI Sys-T deployment
collateral**, and the IDs are its wire identifiers:

```xml
<syst:Format ID="0x00000000" Mask="0x0FFFFFFF"><![CDATA[cib levels map onto quill levels: INFO -> Info, WARN -> Warning]]></syst:Format>
<syst:Format ID="0x00000001" Mask="0x0FFFFFFF"><![CDATA[compile-time formatted: the answer is 42]]></syst:Format>
<syst:Format ID="0x00000002" Mask="0x0FFFFFFF"><![CDATA[errors are logged too, at quill's Error level]]></syst:Format>
```

**The tool has the fix, and the project is not using it.** `gen_str_catalog()` takes a
`STABLE_JSON` argument (`string_catalog.cmake:16`), passes it as `--stable_json`
(`string_catalog.cmake:85`), and the tool then:

- reads the previous catalog's JSON (`read_stable`, `gen_str_catalog.py:492-506`);
- keeps the ID of every message that already had one (`assign_ids`, `gen_str_catalog.py:307-337`,
  with `get_id` at `:308-313`);
- hands out the *free* integers to the new messages, skipping the IDs already in use
  (`gen_str_catalog.py:321-325`);
- re-emits the old entries in the output JSON (`write_json`, `gen_str_catalog.py:465-472`), so the
  JSON is its own stable file - a removed message keeps its ID and is never reused.

The project's `cmake/catalog.cmake` does not pass `STABLE_JSON`, so the flag reaches argparse with
an empty list:

```text
--xml_output .../cpp-core-catalog.xml --stable_json --client_name cpp-core --version 0.1.0
```

`--stable_json` is declared with `nargs="*"` (`gen_str_catalog.py:707-713`), so it consumes
nothing, `read_stable([])` returns nothing, and **every regeneration renumbers the messages from
scratch**.

**So: the IDs are stable across compilers, and unstable across releases.** That is **DEF-6**.

### The fix, and the decision it needs

The fix is one line in `cmake/catalog.cmake` - pass the previous catalog as `STABLE_JSON` - but
*where the previous catalog lives* is the owner's call, because it decides whether the IDs survive
a clean build tree:

| Option | How | What it buys | What it costs |
|---|---|---|---|
| **(a) a committed file** | `STABLE_JSON ${CMAKE_SOURCE_DIR}/cmake/catalog-stable.json` | the IDs survive a clean tree, a branch switch and a new machine; the file is reviewable and diffable | the file has to be committed, and it is an artifact in the source tree |
| **(b) the build tree** | `STABLE_JSON ${CMAKE_CURRENT_BINARY_DIR}/cpp-core-catalog.json` | nothing to commit | the IDs only survive *within* one build tree; a clean build renumbers everything, so it does not actually fix the problem |
| **(c) neither** | leave it as it is | - | the IDs are a property of the current message set, not of the project |

**(b) does not work** - it is the same defect with an extra step - so the real choice is (a) or
(c). I recommend **(a)**: the file is the durable record of which ID belongs to which message, it
makes an ID change visible in a diff, and it is the only option under which the collateral's IDs
mean the same thing on every machine. That is **BUILD-7**.

### What would break if the fix is wrong

The stable mechanism keys the lookup on `hash(text) ^ hash(args)` (`gen_str_catalog.py:212-213`,
and the same formula in `stable_msg_key`, `:744-745`). Two consequences:

- a message whose *text* changes is a **different** message, and it gets a new ID - which is
  correct, and is why the stable file is worth reviewing rather than trusting blindly;
- the stable file is compiler-independent (the argument types are fundamental types, as shown
  above), so the same stable file works for both toolchains.

## What else the catalog turned up

- **Only the CIB path reaches the catalog.** The catalog's three messages are all from
  `src/app.cpp`; `tests/logging_test.cpp` contributes nothing, because it uses the module path
  (`import com.rsm.logging`), which has no catalog symbol at all. The `cpp-core-test-code` input
  of `gen_str_catalog()` is scanned for nothing today. That matches the root README ("The module
  path has no catalog ID"), but it means the catalog covers a third of the project's log calls.
- **The catalog text is the post-folding text.** The source says
  `CIB_INFO("compile-time formatted: the answer is {}", answer)` and the catalog says
  `"compile-time formatted: the answer is 42"`. The catalog describes the message as it will
  actually be logged, which is the right thing for a wire format - and it is a source-level
  property, so it is the same under both compilers.
- **The module ID has a ceiling.** `check_module_limit` enforces `module_id_max`, 127 by default
  (`gen_str_catalog.py:719-724`). This project has one module.
- **The identifiers are traced from the source to the queue.** Part 20 read the whole catalog path
  line by line, and the chain is: the three `CIB_*` calls in `src/app.cpp:27-30` name the
  messages; `CIB_LOG_MODULE("cpp_core")` (`src/app.cpp:21`) names the module; the format string
  and the argument types become the message's **type**
  (`include/cpp-core/logging/cib_quill.hpp:89-105`), so the text never reaches the payload; the
  module name is kept in a `static constexpr` so that its characters have static storage duration
  (`include/cpp-core/logging/cib_quill.hpp:108-116`); and the two IDs are looked up at run time
  (`include/cpp-core/logging/cib_quill.hpp:139-140`) and attached to the message as a **tag**
  (`include/cpp-core/logging/cib_quill.hpp:146-148`) - `cpp_core id=<n> mod=<n>` - which the
  pattern prints as `[%(tags)]` (`src/logging/quill_logger.cpp:33-35`). The IDs are the only
  identification of the message that goes onto the queue.

## The method

- **The catalogs**: **[measured]** - read from the nine build trees under `build/`, which were
  generated before the build lane was parked. Nothing was rebuilt; the files were read as they
  are.
- **The tool**: **[source]** - read from
  `build/p2996-debug/vcpkg_installed/arm64-osx-p2996/share/intel-cib/python/cib/gen_str_catalog.py`
  and `.../share/intel-cib/string_catalog.cmake`, and from cib's
  `include/log_binary/catalog/{catalog,arguments,encoder,mipi_builder}.hpp`. The two installed
  copies of each tool file are byte-identical (md5 `9c516bdb409fb8f0b03b1d0faf0e5695` and
  `b40a977203c352fabfc23a5bb5709796`), so the line numbers hold in both trees. The port is
  `intel-cib` `version-date` 2026-11-09.
- **The project's own sources**: **[source]** - `cmake/catalog.cmake`, `CMakeLists.txt`,
  `tests/CMakeLists.txt`, `src/app.cpp`, `tests/logging_test.cpp`, read in full.

**Nothing was built, configured, run or regenerated.** The one claim that a run would settle
directly - what happens to the IDs when a message is added - is derived here from the tool's source
(the sort at `gen_str_catalog.py:300-304` and the id generator at `:321-325`), and the derivation
is recorded rather than the run.
