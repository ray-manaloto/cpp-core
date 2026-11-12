# The quill files that this item depends on

quill 13.1.0 (the version the vcpkg port installs), the four files that decide what the module
path's log line looks like:

| file | what it decides |
|---|---|
| `backend/PatternFormatter.h` | the `%(short_source_location)` and `%(caller_function)` attributes: the location is shortened to the file's base name, and the function name is available but not in this project's pattern |
| `sinks/StreamSink.h` | the sink writes to the `stdout` stream (`_file = stdout`) and flushes it, which is what the test's stdout capture redirects |
| `sinks/ConsoleSink.h` | the console sink on top of it |
| `core/MacroMetadata.h` | the metadata events: `LogWithRuntimeMetadataShallowCopy` is the one the module uses, and it stores the file and the function name as pointers, so they have to have static storage duration |

`Logger.h`, with `log_statement_runtime_metadata` (the function the module's implementation calls),
is in the leak-check bundle, because it was needed there as well:
[`../../../asan-leak-check/upstream/quill/Logger.h`](../../../asan-leak-check/upstream/quill/Logger.h).
