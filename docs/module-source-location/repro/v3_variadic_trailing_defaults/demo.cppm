// Variant 3: the location as defaulted parameters *after* a variadic pack.
//
// The defaulted parameters become part of the pack's deduction, so the runtime arguments end up
// in the location parameters and the call does not match the declaration.
export module demo;

namespace detail {
template <typename T> struct type_identity {
  using type = T;
};
template <typename T> using type_identity_t = typename type_identity<T>::type;
} // namespace detail

export namespace com::rsm::logging {

template <typename... Wrapped> class format_string {
public:
  template <unsigned long N> consteval format_string(char const (&text)[N]) : text(text) {}
  char const *text;
};

template <typename... Args> auto info(format_string<detail::type_identity_t<Args>...> fmt,
                                      Args &&...args, char const *file = __builtin_FILE(),
                                      unsigned line = __builtin_LINE()) -> void;

} // namespace com::rsm::logging
