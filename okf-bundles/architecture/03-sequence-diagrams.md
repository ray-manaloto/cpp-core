---
type: Architecture Document
title: Sequence Diagrams — cpp-core Runtime Flows
description: Detailed runtime interaction sequences for module and catalog paths
resource: https://github.com/ray-manaloto/cpp-core/blob/main/docs/architecture/03-sequence-diagrams.md
tags:
  - architecture
  - sequence-diagrams
  - cpp-core
  - runtime
  - mermaid
generated:
  by: human:ray-manaloto
  at: 2026-11-14T00:00:00Z
verified:
  - by: human:ray-manaloto
    at: 2026-11-14T00:00:00Z
status: stable
tags:
  - architecture
  - sequence-diagrams
  - cpp-core
  - mermaid
sources:
  - id: source-code
    resource: https://github.com/ray-manaloto/cpp-core/tree/main/docs/architecture
    title: Original architecture documentation
    author: human:ray-manaloto
    last_modified: 2026-11-14T00:00:00Z
---

## Sequence Diagrams — cpp-core Runtime Flows

Detailed runtime interaction sequences for module and catalog paths.

### Module Path — Full Call Sequence

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#36454f', 'secondaryColor': '#708090' }}}%%
sequenceDiagram
    participant Consumer as Consumer Code
    participant Module as com.rsm.logging
    participant Format as format.hpp
    participant Internal as internal.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend
    participant Sink as Console/File Sink

    Consumer->>Module: info("answer: {}", 42)
    Module->>Module: format_string ctor (consteval)
    Note right of Module: Validates format string at compile time
    Module->>Format: format_message(buf, fmt, args...)
    Format->>Format: parse_spec, format_integer, format_value
    Module->>Internal: emit(level, file, line, func, msg, len)
    Internal->>QuillLogger: emit(int level, file, line, func, msg, len)
    QuillLogger->>QuillLogger: to_quill_level(level)
    QuillLogger->>Quill: log_statement_runtime_metadata<true>(...)
    Note right of QuillLogger: Event: LogWithRuntimeMetadataDeepCopy
    Quill->>Quill: Queue: fmt + args → backend thread
    Quill->>Quill: Backend formats with fmtquill → sink
    Sink->>Consumer: Formatted log output
```

### Catalog Path — Full Call Sequence

```mermaid
sequenceDiagram
    participant App as app.cpp
    participant CIB as CIB_LOG macro
    participant CIB_QUILL as cib_quill.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend
    participant Sink as Console/File Sink

    App->>CIB: CIB_INFO("answer: {}", 42)
    CIB->>CIB_QUILL: logging::log<cib_log_env_t>(file, line, fmt, args)
    CIB_QUILL->>CIB_QUILL: to_quill_level(cib::level)  %% DEF-7: INVERTED!
    CIB_QUILL->>QuillLogger: log_statement_runtime_metadata<true>(meta, fmt, file, "", tags, line, level, args)
    Note right of CIB_QUILL: Uses LogWithRuntimeMetadataDeepCopy event
    Note right of CIB_QUILL: format string SENT on queue!
    QuillLogger->>Quill: Queue: fmt + args → backend thread
    Quill->>Quill: Backend formats with fmtquill → sink
    Sink->>App: Formatted log output
```

### Logger Initialization Sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant Module as com.rsm.logging
    participant Internal as internal.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    App->>Module: setup()
    Module->>Internal: start_logger()
    Internal->>QuillLogger: quill_logger()
    Note right of QuillLogger: Static local lambda initialization
    QuillLogger->>Quill: Backend::start()
    QuillLogger->>Quill: Frontend::create_or_get_sink()
    QuillLogger->>Quill: Frontend::create_or_get_logger()
    QuillLogger->>Quill: PatternFormatterOptions{pattern}
    QuillLogger-->>Internal: Logger* pointer
    Internal-->>Module: void
    Module-->>App: void
```

### Log Message — Format String Validation (Module Path)

```mermaid
sequenceDiagram
    participant Consumer as Consumer Code
    participant Module as com.rsm.logging
    participant Format as format.hpp

    Consumer->>Module: info("answer: {}", 42)
    Module->>Module: format_string ctor (consteval)
    Note right of Module: Validates format string at compile time
    Note right of Module: Throws if format string malformed or args mismatch
    Module->>Module: capture source location
    Module->>Format: format_message(buf, fmt, args...)
```

### Logger Flush Sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant Module as com.rsm.logging
    participant Internal as internal.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    App->>Module: flush()
    Module->>Internal: flush_logger()
    Internal->>QuillLogger: quill_logger()
    QuillLogger->>QuillLogger: if (logger != nullptr)
    QuillLogger->>Quill: logger->flush_log()
    Quill->>Quill: Backend::flush()
    Quill->>Quill: Sink flush
```

### Level Change Sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant Module as com.rsm.logging
    participant Internal as internal.hpp
    participant QuillLogger as quill_logger.cpp
    participant Quill as quill Backend

    App->>Module: set_level(level::warning)
    Module->>Internal: set_log_level(static_cast<int>(level))
    Internal->>QuillLogger: quill_logger()
    QuillLogger->>Quill: logger->set_log_level(to_quill_level(level))
    Quill->>Quill: Backend applies level filter
```

### Reflection Demo — Module Path with C++26 Reflection

```mermaid
sequenceDiagram
    participant Demo as reflection_demo.cpp
    participant Module as com.rsm.logging
    participant Meta as <meta> header

    Demo->>Module: import com.rsm.logging
    Demo->>Meta: import <meta>
    Demo->>Meta: nonstatic_data_members_of(^^point)
    Meta-->>Demo: member count = 2 (x, y)
    Demo->>Module: info("point has {} members", count)
    Module->>Module: format_string validation
    Module->>Module: info("C++26 static reflection OK...")
    Note right of Demo: GCC 16's member range cannot outlive constant evaluation
```

### Test Execution Flow

```mermaid
sequenceDiagram
    participant Test as logging_test.cpp
    participant Module as com.rsm.logging
    participant UT as ut framework
    participant Internal as internal.hpp
    participant Capture as stdout_capture

    Test->>UT: suite tests = [...]
    UT->>Test: "level can be set" test
    Test->>Module: set_level(warning)
    Test->>Module: current_level()
    Module->>Internal: get_log_level()
    Internal-->>Module: int level
    Module-->>Test: level == warning
    UT->>Test: "logging does not throw" test
    Test->>Module: setup()
    Test->>Module: info("...")
    Test->>Module: warning("...")
    Test->>Module: flush()
    Module->>Module: internal emit/flush
    Test->>Module: flush()
    Module->>Capture: capture stdout
    Capture->>Capture: dup2/fflush/dup2/restore
    Capture-->>Test: captured output
    Test->>UT: expect(true)
```
