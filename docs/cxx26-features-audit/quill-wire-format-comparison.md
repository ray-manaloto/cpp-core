# Quill wire format vs. catalog-typed proposal

**Date:** 2026-11-13
**Status:** research. Read from installed quill 13.1.0 headers in the vcpkg tree.

## 1. What quill sends over the queue today

The frontend thread reserves space in an SPSC queue and encodes a **record** that the backend consumes.

### 1.1 The header (fixed, 32 bytes = 4 × uint64_t)

```cpp
// LoggerImpl::_encode_header (Logger.h:1031-1048)
struct Header {
  uint64_t timestamp;        // rdtsc() or system time
  uint64_t metadata_ptr;     // reinterpret_cast<uintptr_t>(MacroMetadata const*)
  uint64_t logger_ptr;       // reinterpret_cast<uintptr_t>(LoggerImpl*)
  uint64_t decoder_ptr;      // reinterpret_cast<uintptr_t>(FormatArgsDecoder)
};
```

- `metadata_ptr` → `MacroMetadata` (compile-time constants, never on queue)
- `logger_ptr` → the logger instance
- `decoder_ptr` → a function pointer `decode_and_store_args<Args...>` (per call-site type list)

### 1.2 The payload (variable, per `Codec`)

For each argument `Args...`, `Codec<Arg>::encode()` writes:

| Type category | Encoding |
|---|---|
| Arithmetic, enum, `void*`, `void const*` | `memcpy` of `sizeof(Arg)` |
| `char[N]` | length (cached `uint32_t`) + bytes + `\0` |
| `char*` / `char const*` | length (cached `uint32_t`, includes `\0`) + bytes + `\0` |
| `std::string` / `std::string_view` | `uint32_t` length + bytes |
| Other | **compile error** (`codec_not_found_for_type`) |

The **format string is NOT in the payload** — it lives in `MacroMetadata::message_format()` (a compile-time `char const*`). The backend reads it from the `MacroMetadata` object via the `metadata_ptr` in the header.

### 1.3 The decoder

`FormatArgsDecoder` is a function pointer:

```cpp
using FormatArgsDecoder = void (*)(std::byte*&, DynamicFormatArgStore&);
```

Per call site, `decoder_ptr<Args...>` is instantiated. On the backend, it decodes the payload into a `DynamicFormatArgStore`, which holds `fmtquill::basic_format_arg<fmtquill::format_context>` for each argument.

### 1.4 Backend formatting

`BackendWorker::_write_log_statement` (BackendWorker.h:1487) calls:

```cpp
sink->_pattern_formatter->format(
  timestamp, thread_id, thread_name, process_id, logger_name,
  log_level_description, log_level_short_code,
  *macro_metadata,          // → has message_format()
  transit_event.get_named_args(),
  log_message,              // the **formatted** message string
  mdc
);
```

The formatter receives:

- The **format string** from `macro_metadata->message_format()`
- The **decoded arguments** from `DynamicFormatArgStore`
- It produces `log_message` (the fully formatted string) using fmtlib

---

## 2. What the catalog-typed proposal wants

**Compile-time:** Each distinct `(format string + parameter types)` → a **unique catalog ID** (a type, e.g. `sc::undefined<sc::args<Args...>, -1, ...>`).

**Runtime:** The queue carries **only the parameter values** — **no format string**, no `MacroMetadata` pointer to a format string. The catalog ID (or its equivalent) identifies the message schema.

**Backend:** Uses fmtlib to **deserialize** the catalog-typed payload directly into structured fields (or re-format using the schema associated with the catalog ID).

---

## 3. The delta — what changes

| Aspect | Quill today | Catalog-typed proposal |
|---|---|---|
| **Queue payload** | Format string (via `MacroMetadata` pointer) + encoded args | **Only encoded args**; catalog ID identifies schema |
| **Header** | 32 bytes: timestamp, metadata_ptr, logger_ptr, decoder_ptr | Could shrink: no `metadata_ptr` needed for format string |
| **Decoder** | Per-call-site `decoder_ptr<Args...>` → `DynamicFormatArgStore` | **One decoder per catalog ID** (schema known at compile time) |
| **Backend** | fmtlib formats using `message_format()` + decoded args | fmtlib **deserializes** into typed fields / re-formats from schema |
| **Format string** | Stored in binary, pointed to by `MacroMetadata` | **Never on queue**; only in catalog (compile-time) |
| **Schema evolution** | Implicit (format string in binary) | Explicit (catalog ID = schema version) |

---

## 4. Can quill support this today?

### 4.1 What exists

- `Codec` encodes arbitrary `Args...` into a byte buffer (the payload part)
- `DynamicFormatArgStore` holds decoded args for fmtlib
- `MacroMetadata` carries compile-time metadata (but includes format string)
- The SPSC queue is just bytes — payload format is up to the encoder/decoder

### 4.2 What's missing / would need change

1. **No catalog-ID encoder**: The header encodes `metadata_ptr` (pointer to `MacroMetadata`). A catalog-typed path would encode a **catalog ID** (integer) instead.
2. **Decoder per catalog ID**: Today `decoder_ptr` is per call-site (`Args...`). The catalog path needs one decoder **per catalog ID**, shared across all call sites that map to that ID.
3. **Backend deserialization**: Today the backend uses `PatternFormatter` with the format string from `MacroMetadata`. The catalog path needs a **catalog-aware formatter** that looks up the schema by ID and deserializes directly.
4. **`log_statement_runtime_metadata` path**: This is what `cib_quill.hpp` uses (Logger.h:426-547). It passes `fmt` (format string) as a runtime string in the payload. The catalog path must **not** send `fmt`.

### 4.3 The key question: QUIL-1

> **Can a `Codec` push three arguments from one pack element?**

The catalog path wants: one catalog type = one `Args...` pack. But quill's `Codec` encodes **each argument separately**. If the catalog type is a single struct with 3 fields, the `Codec` for that struct would need to encode all 3 fields. This is what `DeferredFormatCodec` / `DirectFormatCodec` are for — but they require a custom formatter.

**The experiment needed:** Write a `Codec` specialization for the catalog message type that encodes N fields as if they were N separate arguments, and a matching decoder that puts them into `DynamicFormatArgStore` as N separate args.

---

## 5. What the cib_quill.hpp path does today

In `include/cpp-core/logging/cib_quill.hpp:157-159`, the catalog path calls:

```cpp
quill_logger()->template log_statement_runtime_metadata<true>(
  &metadata, fmt.c_str(), file, "", tags.c_str(), line, level, decay_enum_value(...));
```

This goes through `log_statement_runtime_metadata` with `LogWithRuntimeMetadataDeepCopy` — it **sends the format string `fmt.c_str()` on the queue** (Logger.h:504-505). The format string is encoded as a `char const*` (length + bytes + `\0`).

So today, **the catalog path still sends the format string on the queue** — it just sends it at runtime instead of via `MacroMetadata`. The proposal is to **not send it at all**.

---

## 6. Concrete next steps for the lane reopen

1. **Define the catalog message wire format**
   - Header: timestamp, catalog_id (uint32_t?), logger_ptr, decoder_ptr
   - Payload: `Codec<Arg1>::encode`, `Codec<Arg2>::encode`, ... (no format string)

2. **Implement a catalog-aware `Codec`** for the message type
   - `compute_encoded_size`, `encode`, `decode_and_store_arg`
   - The decoder puts N fields into `DynamicFormatArgStore` as N separate args

3. **Add a catalog-aware backend path**
   - Backend looks up schema by catalog_id
   - fmtlib deserializes / re-formats from schema (not from a format string on the queue)

4. **Verify the size win**
   - Current: header (32) + format string (len) + N args
   - Proposed: header (24?) + N args
   - Measure on real message shapes

---

## 7. Files that would change

| File | Change |
|---|---|
| `quill/core/Codec.h` | Add catalog-ID encoder/decoder or specialize for catalog message type |
| `quill/Logger.h` | New `log_statement_catalog` path (no format string in payload) |
| `quill/backend/BackendWorker.h` | Catalog-aware `_write_log_statement` (lookup schema by ID) |
| `cpp-core/include/cpp-core/logging/cib_quill.hpp` | Call new catalog path instead of `log_statement_runtime_metadata` |
| `cmake/catalog.cmake` | Ensure catalog ID is stable and used as wire identifier |

---

## 8. Open questions for the lane reopen

- **QUIL-1**: Can a single `Codec` for a catalog message type encode N fields as N separate arguments? (The `Codec` API is per-type, not per-argument-list.)
- **Schema lookup**: How does the backend map catalog_id → schema? (Shared memory? File? Embedded in binary?)
- **Backward compatibility**: Does the queue support mixed legacy + catalog records? (Different header layouts.)
- **Tag support**: The current pattern uses `%(tags)` in the format string. Catalog path needs tags in the schema.

---

## 9. Source references

All quill source read from:

```text
`<vcpkg_installed>/include/quill/`
  core/MacroMetadata.h           (compile-time metadata, has format string)
  core/DynamicFormatArgStore.h   (holds decoded fmtquill::basic_format_arg)
  core/Codec.h                   (per-type encode/decode, payload format)
  Logger.h                       (queue encoding, log_statement, log_statement_runtime_metadata)
  LogMacros.h                    (macro expansion, MacroMetadata creation)
  backend/BackendWorker.h        (backend formatting, sink write)
```

**No build, no compiler, no CMake** — read from installed headers only. The lane is parked.
