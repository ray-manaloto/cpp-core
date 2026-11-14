# Sequence Diagrams — Runtime Flows

> **Detailed runtime flows: initialization, logging paths, flush, reflection**  
> Theme: Modern Minimalist | Part of [Architecture Documentation](../../README.md)

---

## 🚀 Initialization Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Main as main.cpp
    participant Module as com.rsm.logging
    participant Detail as detail namespace
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    Main->>Module: setup()
    Module->>Detail: start_logger()
    Detail->>QuillLogger: start_logger()
    QuillLogger->>QuillLogger: quill_logger() [first call]
    QuillLogger->>Quill: Backend::start()
    QuillLogger->>Quill: Frontend::create_or_get_sink(ConsoleSink)
    QuillLogger->>Quill: Frontend::create_or_get_logger("cpp-core", sink, PatternFormatterOptions)
    QuillLogger-->>Detail: logger* (cached in static)
    Detail-->>Module: void
    Module-->>Main: void
    Note over Main,Quill: Idempotent — subsequent setup() calls return immediately
```

### Key Points

| Step | Function | Thread Safety |
|------|----------|---------------|
| 1 | `com::rsm::logging::setup()` | Called from `main()` — single thread |
| 2 | `detail::start_logger()` | Calls `quill_logger()` |
| 3 | `quill_logger()` | Static local — **thread-safe init (C++11)** |
| 4 | `quill::Backend::start()` | Starts backend worker thread |
| 5 | Sink + Logger creation | One-time, cached in `static` |

---

## 📝 Module Path Logging Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Caller as Consumer Code
    participant Module as com.rsm.logging
    participant Format as format.hpp
    participant Detail as detail namespace
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    Caller->>Module: info("answer: {}", 42)
    Module->>Module: format_string ctor (consteval)
    Note over Module: Validates format at compile time
    Module->>Format: format_message(buf, fmt, args...)
    Format->>Format: parse_spec, format_integer, format_value
    Module->>Detail: emit(level, file, line, func, msg, len)
    Detail->>QuillLogger: emit(int level, file, line, func, msg, len)
    QuillLogger->>QuillLogger: to_quill_level(level)
    QuillLogger->>Quill: log_statement_runtime_metadata<true>(...)
    Note over QuillLogger: Format string = "{}", msg = formatted string
    Quill->>Quill: Queue record (header + payload)
    Quill->>Quill: Backend thread formats with fmtquill
    Quill->>Sink: Write formatted output
```

### Module Path Characteristics

| Property | Value |
|----------|-------|
| **Formatting thread** | Calling thread (constexpr) |
| **Format string** | Validated at compile time via `format_string` ctor |
| **Queue payload** | Formatted message string + metadata |
| **Backend work** | Minimal — just sink write |
| **Allocation** | `std::string` for formatted message (small-string optimized) |

---

## 📋 Catalog Path Logging Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant App as app.cpp
    participant CIB as CIB_LOG macro
    participant CIB_QUILL as cib_quill.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    App->>CIB: CIB_INFO("answer: {}", 42)
    CIB->>CIB_QUILL: logging::log<cib_log_env_t>(file, line, fmt, args)
    CIB_QUILL->>CIB_QUILL: to_quill_level(cib::level)  %% DEF-7: INVERTED!
    CIB_QUILL->>CIB_QUILL: decay_enum_value(args)  %% strips enum to underlying
    CIB_QUILL->>QuillLogger: log_statement_runtime_metadata<true>(meta, fmt, file, "", tags, line, level, decayed_args)
    Note over CIB_QUILL: format string SENT on queue!
    QuillLogger->>Quill: Queue record (header + payload)
    Quill->>Quill: Backend formats with fmtquill
    Quill->>Sink: Write formatted output
```

### Catalog Path Characteristics

| Property | Value |
|----------|-------|
| **Formatting thread** | Backend thread (runtime) |
| **Format string** | Sent on queue (runtime metadata path) |
| **Queue payload** | Format string + runtime arguments |
| **Backend work** | fmtquill formats using format string |
| **Catalog ID** | Assigned at compile time via `sc::undefined<...>` type |

---

## 🔄 Level Mapping — The DEF-7 Bug

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
graph LR
    subgraph "CIB Levels (MIPI Sys-T)"
        CIB_MAX[CIB::MAX = 0<br/>MOST SEVERE]
        CIB_FATAL[CIB::FATAL = 1]
        CIB_ERROR[CIB::ERROR = 2]
        CIB_WARN[CIB::WARN = 3]
        CIB_INFO[CIB::INFO = 4]
        CIB_USER1[CIB::USER1 = 5]
        CIB_USER2[CIB::USER2 = 6]
        CIB_TRACE[CIB::TRACE = 7<br/>LEAST SEVERE]
    end

    subgraph "Quill Levels"
        QUILL_TRL3[TraceL3<br/>LEAST SEVERE]
        QUILL_TRL2[TraceL2]
        QUILL_TRL1[TraceL1]
        QUILL_DBG[Debug]
        QUILL_INFO[Info]
        QUILL_WARN[Warning]
        QUILL_ERR[Error]
        QUILL_CRIT[Critical<br/>MOST SEVERE]
    end

    CIB_MAX -.->|WRONG: MAPS TO| QUILL_TRL3
    CIB_FATAL -.->|MAPS TO| QUILL_CRIT
    CIB_ERROR -.->|MAPS TO| QUILL_ERR
    CIB_WARN -.->|MAPS TO| QUILL_WARN
    CIB_INFO -.->|MAPS TO| QUILL_INFO
    CIB_USER1 -.->|MAPS TO| QUILL_DBG
    CIB_USER2 -.->|MAPS TO| QUILL_TRL1
    CIB_TRACE -.->|WRONG: MAPS TO| QUILL_TRL2

    classDef wrong fill:#ffcccc,stroke:#ff0000,stroke-width:2px
    class CIB_MAX,CIB_TRACE wrong
```

### Impact

| Sink Threshold | CIB MAX Message | CIB FATAL Message |
|----------------|-----------------|-------------------|
| `Error` | **DROPPED** (maps to TraceL3 < Error) | **KEPT** (maps to Critical ≥ Error) |

> **Latent defect**: Project never logs at `MAX` today (`app.cpp` uses `CIB_INFO`, `CIB_WARN`, `CIB_ERROR` only).

---

## 🏃 Flush Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Caller as Consumer
    participant Module as com.rsm.logging
    participant Detail as detail
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend
    participant Sink as Console/File Sink

    Caller->>Module: flush()
    Module->>Detail: flush_logger()
    Detail->>QuillLogger: flush_logger()
    QuillLogger->>QuillLogger: quill_logger()->flush_log()
    QuillLogger->>Quill: Logger::flush_log()
    Quill->>Quill: Backend processes queue up to timestamp
    Quill->>Sink: Sink writes buffered messages
    Quill-->>QuillLogger: flush complete
    QuillLogger-->>Detail: void
    Detail-->>Module: void
    Module-->>Caller: void

    Note over Caller,Sink: WARNING: quill docs say "Do not call from destructor of static object"
    Note over Caller,Sink: Project documents this in module header + README (QUIL-9 decision)
```

---

## 🪞 C++26 Static Reflection Demo

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Main as main.cpp
    participant Reflection as reflection_demo.cpp
    participant Module as com.rsm.logging
    participant Meta as std::meta (P2996)

    Main->>Reflection: reflection_demo()
    Reflection->>Meta: ^^reflect^struct(point)  %% or members_of
    Meta-->>Reflection: reflection range
    Reflection->>Reflection: count members (consteval)
    Reflection->>Reflection: static_assert(count == 2)
    Reflection->>Module: info("point has {} members", count)
    Module->>Module: format at compile time (consteval)
    Module->>Detail: emit(...)
    Note over Reflection,Module: GCC 16 constraint: member range cannot outlive consteval
    Note over Reflection,Module: Must call size() on temporary
```

### Reflection Constraints

| Compiler | Constraint |
|----------|------------|
| GCC 16 | Member range cannot outlive consteval — call `size()` on temporary |
| clang-p2996 | Uses `std::meta::access_context::unchecked()` |
| Both | `static_assert(member_count == 2)` is compile-time check |

---

## 🧪 Test Flow (logging_test.cpp)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Test as logging_test.cpp
    participant UT as ut Framework
    participant Module as com.rsm.logging
    participant Capture as stdout_capture

    Test->>UT: suite = []
    Test->>Test: "level round-trip" → set_level + current_level → expect equal
    Test->>Test: "level ordering" → expect enum values ordered
    Test->>Test: "no throw" → info/warn → flush → expect(true)  %% 4 of 8 tests!
    Test->>Test: "every value kind" → 8 formatted calls → expect(true)
    Test->>Test: "raw message" → log_raw → expect(true)
    Test->>Test: "compile-time check" → error("{}", 1, 2) → expect(true)
    Test->>Test: "source location formatted" → capture stdout → expect(file:line in output)
    Test->>Test: "source location raw" → capture stdout → expect(file:line in output)
    Test->>UT: run suite
```

### Test Coverage Gap (Current)

| Test | Asserts | What It Proves |
|------|---------|----------------|
| Level round-trip | `expect(level == set)` | Get/set works |
| Level ordering | `expect(trace < debug < ...)` | Enum values ordered |
| No throw | `expect(true)` | Doesn't crash |
| Every value kind | `expect(true)` | Doesn't crash |
| Raw message | `expect(true)` | Doesn't crash |
| Compile-time check | `expect(true)` | Compiles |
| Source location (formatted) | `expect(output.contains(file:line))` | Location correct |
| Source location (raw) | `expect(output.contains(file:line))` | Location correct |

> **6 of 8 tests assert `expect(true)`** — would pass against a logger that discards everything.

---

## 🔧 Build + Test Presets Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
graph TB
    subgraph "Preset Matrix"
        GCC_DBG[gcc16-debug]
        GCC_REL[gcc16-release]
        GCC_ASAN[gcc16-asan]
        P2996_DBG[p2996-debug]
        P2996_REL[p2996-release]
        P2996_ASAN[p2996-asan]
        P2996_TSAN[p2996-tsan]
        P2996_IWYU[p2996-iwyu]
    end

    subgraph "Workflow Steps"
        CONFIG[configure]
        BUILD[build]
        TEST[test]
    end

    GCC_DBG --> CONFIG --> BUILD --> TEST
    GCC_REL --> CONFIG --> BUILD --> TEST
    GCC_ASAN --> CONFIG --> BUILD --> TEST
    P2996_DBG --> CONFIG --> BUILD --> TEST
    P2996_REL --> CONFIG --> BUILD --> TEST
    P2996_ASAN --> CONFIG --> BUILD --> TEST
    P2996_TSAN --> CONFIG --> BUILD --> TEST
    P2996_IWYU --> CONFIG --> BUILD --> IWYU_BUILD[build iwyu] --> TEST
```

### Preset Configuration

| Preset | Compiler | Build Type | Sanitizer | Hardening |
|--------|----------|------------|-----------|-----------|
| `gcc16-debug` | GCC 16.2 | Debug | none | debug |
| `gcc16-release` | GCC 16.2 | Release | none | none |
| `gcc16-asan` | GCC 16.2 | Debug | ASan+UBSan | debug |
| `p2996-debug` | clang-p2996 | Debug | none | debug |
| `p2996-release` | clang-p2996 | Release | none | none |
| `p2996-asan` | clang-p2996 | Debug | ASan | debug |
| `p2996-tsan` | clang-p2996 | Debug | TSan | debug |
| `p2996-iwyu` | clang-p2996 | Debug | none | debug + IWYU |

---

## 📖 Related Documentation

| Document | Focus |
|----------|-------|
| [01-component-diagram.md](01-component-diagram.md) | Static component view |
| [02-wire-protocol.md](02-wire-protocol.md) | Queue wire format |
| [04-dependency-graph.md](04-dependency-graph.md) | Dependencies and versions |
| [../cxx26-features-audit/quill-wire-format-comparison.md](../cxx26-features-audit/quill-wire-format-comparison.md) | Wire format research |

---

*Part of the cpp-core Architecture Documentation Suite — [Back to Index](../../README.md)*