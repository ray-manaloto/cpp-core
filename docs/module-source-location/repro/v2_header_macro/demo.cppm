// Variant 2: the macro lives in a header that the global module fragment includes.
module;
#include "macros.hpp"

export module demo;

export namespace com::rsm::logging {
auto info(int value) -> void;
}
