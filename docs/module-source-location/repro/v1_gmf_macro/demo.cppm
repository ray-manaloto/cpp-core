// Variant 1: the macro lives in the module's global module fragment.
module;

#define GMF_MACRO(x) com::rsm::logging::info(x)

export module demo;

export namespace com::rsm::logging {
auto info(int value) -> void;
}
