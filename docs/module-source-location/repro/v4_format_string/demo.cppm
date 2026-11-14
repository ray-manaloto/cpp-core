// Variant 4: the location in format_string's constructor's default arguments.
//
// A default argument is evaluated at the call site, so the builtins name the caller. The format
// string is the first parameter and the runtime arguments keep their place.
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
  template <unsigned long N>
  consteval format_string(char const (&text)[N], char const *file = __builtin_FILE(),
                          unsigned line = __builtin_LINE(),
                          char const *function = __builtin_FUNCTION())
    : text(text), file(file), line(line), function(function) {}
  char const *text;
  char const *file;
  unsigned line;
  char const *function;
};

template <typename... Args>
auto info(format_string<detail::type_identity_t<Args>...> fmt, Args &&...args) -> void;

} // namespace com::rsm::logging
