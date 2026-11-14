# Component Diagram — cpp-core Architecture

> **System components, modules, data flow, and boundaries**  
> Theme: Modern Minimalist | Part of [Architecture Documentation](../../README.md)

---

## 🏗️ High-Level Component View

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090', 'background': '#ffffff', 'textColor': '#36454f', 'edgeLabelBackground': '#f0f0f0' }}}%%
graph TB
    subgraph "External Consumers"
        CONSUMER[Consumer Project<br/>import com.rsm.logging;]
    end

    subgraph "cpp-core Library"
        direction TB
        
        subgraph "Module Path (Public API)"
            MODULE[com.rsm.logging<br/>C++ Module]
            CPPM[logging.cppm<br/>Module Interface]
            FORMAT[format.hpp<br/>Private Formatter]
            INTERNAL_H[internal.hpp<br/>Global Module Fragment]
        end

        subgraph "Catalog Path (CIB)"
            CIB_QUILL[cib_quill.hpp<br/>CIB Customization Point]
            CIB_LOG[Intel CIB<br/>CIB_LOG macros]
        end

        subgraph "Implementation (Private)"
            QUILL_LOGGER[quill_logger.cpp<br/>Backend Implementation]
            QUILL_LOGGER_HPP[quill_logger.hpp<br/>Implementation Detail]
        end

        subgraph "Application"
            APP[app.cpp<br/>Catalog Path Usage]
            MAIN[main.cpp<br/>Module Path Entry]
            REFLECTION[reflection_demo.cpp<br/>C++26 Reflection Demo]
        end
    end

    subgraph "External Dependencies"
        QUILL[quill 13.1.0<br/>Backend Queue + fmtquill]
        CIB[intel-cib<br/>Compile-time Logging]
        FMT[fmt 12.2.1<br/>Standalone Formatter]
        UT[ut 1.2.1<br/>Test Framework]
        INTEL_EXT[intel-cpp-std-extensions]
        INTEL_CONC[intel-baremetal-concurrency]
        INTEL_SR[intel-baremetal-senders-receivers]
    end

    %% Module Path connections
    CONSUMER -->|import| MODULE
    MODULE --> CPPM
    CPPM -->|includes| FORMAT
    CPPM -->|includes| INTERNAL_H
    INTERNAL_H -->|global module fragment| QUILL_LOGGER

    %% Catalog Path connections
    APP -->|includes| CIB_QUILL
    CIB_QUILL -->|uses| CIB_LOG
    CIB_QUILL -->|calls| QUILL_LOGGER

    %% Implementation connections
    CPPM -->|forwards via| INTERNAL_H
    INTERNAL_H -->|calls| QUILL_LOGGER
    QUILL_LOGGER -->|implements| QUILL_LOGGER_HPP
    QUILL_LOGGER -->|uses| QUILL
    QUILL_LOGGER -->|uses| FMT

    %% Reflection demo
    REFLECTION -->|imports| MODULE
    REFLECTION -->|uses| CIB_QUILL

    %% Test connections
    TESTS[logging_test.cpp] -->|imports| MODULE
    TESTS -->|uses| UT

    %% Styling
    classDef public fill:#36454f,color:#fff,stroke:#708090
    classDef private fill:#d3d3d3,color:#36454f,stroke:#708090
    classDef external fill:#f0f0f0,color:#36454f,stroke:#708090,stroke-dasharray: 5 5
    classDef module fill:#36454f,color:#fff,stroke:#708090

    class MODULE,CPPM,FORMAT,INTERNAL_H module
    class CIB_QUILL,CIB_LOG private
    class QUILL_LOGGER,QUILL_LOGGER_HPP,APP,MAIN,REFLECTION private
    class QUILL,CIB,FMT,UT,INTEL_EXT,INTEL_CONC,INTEL_SR external
    class CONSUMER public
```

---

## 📦 Component Responsibilities

| Component | Type | Responsibility | Public? |
|-----------|------|----------------|---------|
| `com.rsm.logging` | C++ Module | Public API: `info()`, `warning()`, `error()`, `trace()`, `debug()`, `critical()`, `log()`, `log_raw()`, `setup()`, `flush()`, `set_level()`, `current_level()` | ✅ Yes |
| `logging.cppm` | Module Interface | Exports module, defines `level` enum, `format_string` class, forwarding functions | ✅ Yes (BMI) |
| `format.hpp` | Private Header | Hand-rolled constexpr formatter (492 lines), format spec parsing, integer/float formatting | ❌ No (PRIVATE) |
| `internal.hpp` | Global Module Fragment | Standard-library-free interface: 6 level constants + 6 functions (`start_logger`, `flush_logger`, `set_log_level`, `get_log_level`, `emit`, `format_double`) | ❌ No (GMF) |
| `cib_quill.hpp` | CIB Customization | Implements CIB's `logging::config<>` specialization, catalog path level mapping, `decay_enum_value` | ❌ No (internal) |
| `quill_logger.cpp` | Implementation | Quill backend: logger creation, `log_statement_runtime_metadata`, level mapping, `format_double` | ❌ No (PRIVATE source) |
| `quill_logger.hpp` | Impl Detail | Single declaration: `quill_logger() -> quill::Logger*` | ❌ No (implementation detail) |
| `app.cpp` | Application | Catalog path usage: `CIB_INFO`, `CIB_WARN`, `CIB_ERROR` + calls reflection demo | ❌ No (object lib) |
| `main.cpp` | Entry Point | Module path: `import com.rsm.logging; setup(); flush()` | ❌ No (executable) |
| `reflection_demo.cpp` | Demo | C++26 static reflection: `import com.rsm.logging; <meta>` | ❌ No (separate TU) |

---

## 🔄 Data Flow — Module Path

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Consumer as Consumer Code
    participant Module as com.rsm.logging
    participant Format as format.hpp
    participant Internal as internal.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    Consumer->>Module: info("answer: {}", 42)
    Module->>Module: format_string ctor (consteval)
    Module->>Format: format_message(buf, fmt, args...)
    Format->>Format: parse_spec, format_integer, format_value
    Module->>Internal: emit(level, file, line, func, msg, len)
    Internal->>QuillLogger: emit(int level, file, line, func, msg, len)
    QuillLogger->>QuillLogger: to_quill_level(level)
    QuillLogger->>Quill: log_statement_runtime_metadata<true>(...)
    Quill->>Quill: Queue: fmt + args → backend thread
    Quill->>Quill: Backend formats with fmtquill → sink
```

---

## 🔄 Data Flow — Catalog Path

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
    CIB_QUILL->>QuillLogger: log_statement_runtime_metadata<true>(meta, fmt, file, "", tags, line, level, args)
    Note over CIB_QUILL: format string SENT on queue!
    QuillLogger->>Quill: Queue: fmt + args → backend thread
    Quill->>Quill: Backend formats with fmtquill → sink
```

---

## 🚫 Boundary Rules (Enforced)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
graph LR
    subgraph "Module Interface (Public)"
        MODULE[com.rsm.logging]
        INTERNAL_GMF[internal.hpp in GMF]
    end

    subgraph "Implementation (Private)"
        FORMAT[format.hpp]
        QUILL_LOGGER[quill_logger.cpp]
        QUILL_LOGGER_HPP[quill_logger.hpp]
        CIB_QUILL[cib_quill.hpp]
    end

    subgraph "External"
        QUILL[quill]
        FMT[fmt]
        CIB[Intel CIB]
        STD[std library]
    end

    MODULE -.->|exports| INTERNAL_GMF
    INTERNAL_GMF -.->|includes| FORMAT
    FORMAT -.->|used by| QUILL_LOGGER
    QUILL_LOGGER -.->|uses| QUILL
    QUILL_LOGGER -.->|uses| FMT
    CIB_QUILL -.->|uses| CIB
    CIB_QUILL -.->|calls| QUILL_LOGGER

    style STD fill:#ffcccc,stroke:#ff0000,stroke-width:2px
    style MODULE fill:#36454f,color:#fff
    style INTERNAL_GMF fill:#36454f,color:#fff
```

| Rule | Enforcement | Status |
|------|-------------|--------|
| Module interface includes no `<xxx>` standard headers | `internal.hpp` has zero includes | ✅ Enforced |
| `format.hpp` is PRIVATE source | `target_sources(... PRIVATE format.hpp)` | ✅ Enforced |
| `quill_logger.hpp` not in module BMI | Not in `FILE_SET CXX_MODULES` | ✅ Enforced |
| `format_double` only in implementation | Only in `quill_logger.cpp` | ✅ Enforced |
| Catalog path outside module | `app.cpp` includes `cib_quill.hpp`, no import | ✅ Enforced |

---

## 📐 Module Interface Surface

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
classDiagram
    class com.rsm.logging {
        +enum class level : unsigned char { trace, debug, info, warning, error, critical }
        +template<Wrapped...> class format_string
        +setup() void
        +flush() void
        +set_level(level) void
        +current_level() level
        +log_raw(level, msg, len) void
        +log(format_string, Args...) void
        +trace(format_string, Args...) void
        +debug(format_string, Args...) void
        +info(format_string, Args...) void
        +warning(format_string, Args...) void
        +error(format_string, Args...) void
        +critical(format_string, Args...) void
    }

    class format_string<Wrapped...> {
        +consteval format_string(char const*, source_location...)
        +text: char const*
        +length: unsigned long
        +file: char const*
        +line: unsigned
        +function: char const*
    }

    class detail {
        +start_logger() void
        +flush_logger() void
        +set_log_level(int) void
        +get_log_level() int
        +emit(int, file, line, func, msg, len) void
        +format_double(double, char, int, char*, ulong) ulong
    }

    com.rsm.logging ..> format_string : uses
    com.rsm.logging ..> detail : forwards to
```

---

## 🔑 Key Architectural Decisions (Visual Summary)

| Decision | Diagram Reference | Impact |
|----------|-------------------|--------|
| **Dual-path architecture** | Two parallel flows in component diagram | Module path = constexpr, Catalog path = structured logging |
| **Standard-library-free module** | `internal.hpp` in GMF, zero includes | Enables `import com.rsm.logging;` without collisions |
| **format.hpp is PRIVATE** | Not in BMI, only in module purview | Hand-rolled formatter hidden from consumers |
| **Catalog path outside module** | `app.cpp` uses `cib_quill.hpp`, no import | CIB macros work; structured logging via types |
| **Two fmt copies** | `fmt` (standalone) + `fmtquill` (bundled in quill) | Structural, not accidental — custom formatters for `fmt` only |

---

## 📖 Related Documentation

| Document | Focus |
|----------|-------|
| [02-wire-protocol.md](02-wire-protocol.md) | Quill wire format vs catalog-typed proposal |
| [03-sequence-diagrams.md](03-sequence-diagrams.md) | Detailed runtime flows |
| [04-dependency-graph.md](04-dependency-graph.md) | All external dependencies with versions |
| [../cxx26-features-audit/README.md](../cxx26-features-audit/README.md) | Full audit (21 parts) |

---

*Part of the cpp-core Architecture Documentation Suite — [Back to Index](../../README.md)*