// cpp-core: the quill logger that backs the logging library.
//
// This header is used by the CIB_* macro path (cpp-core/logging/cib_quill.hpp), which calls
// quill's templated API directly so that only the runtime values go onto quill's queue. The
// module path talks to the implementation through cpp-core/logging/internal.hpp instead, because
// a module's interface cannot depend on quill (or on the standard library).
//
// The declarations live in com::rsm::logging::detail: they are the implementation's business,
// not part of the module's public interface.

#pragma once

#include <quill/Logger.h>

namespace com::rsm::logging::detail {

// The quill logger that every log message is routed to. Starts quill's backend on first use.
[[nodiscard]] auto quill_logger() -> quill::Logger*;

} // namespace com::rsm::logging::detail
