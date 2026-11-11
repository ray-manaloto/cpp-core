// cpp-core: the module-private formatting helpers of the logging module.
//
// The module's interface cannot use the standard library (see the comment at the top of
// logging.cppm), so the module formats the messages itself. These helpers are the module's
// private implementation: they are not exported, and the compiler emits them into the
// translation units that instantiate the module's templates.
//
// The formatting follows the shape of std::format: a replacement field is "{}" (the next
// argument), "{N}" (the Nth argument) or "{:spec}" (with a format specification). The supported
// specifications are [[fill]align][sign][#][0][width][.precision][type].

#pragma once

namespace com::rsm::logging::detail {

// ---------------------------------------------------------------------------------------------
// Type traits. The standard library's <type_traits> is not available to the module's interface.
// ---------------------------------------------------------------------------------------------

template <typename T> struct true_type {
  static constexpr bool value = true;
};

template <typename T> struct false_type {
  static constexpr bool value = false;
};

template <typename A, typename B> struct is_same : false_type<A> {};
template <typename A> struct is_same<A, A> : true_type<A> {};

template <typename T> struct remove_cv {
  using type = T;
};
template <typename T> struct remove_cv<T const> {
  using type = T;
};
template <typename T> struct remove_cv<T volatile> {
  using type = T;
};
template <typename T> struct remove_cv<T const volatile> {
  using type = T;
};

template <typename T> struct remove_ref {
  using type = T;
};
template <typename T> struct remove_ref<T&> {
  using type = T;
};
template <typename T> struct remove_ref<T&&> {
  using type = T;
};

// The type without its references and without its top-level cv-qualifiers. The reference goes
// first: a cv-qualified reference is a cv-qualified object, not a cv-qualified reference.
template <typename T>
using remove_cvref_t = typename remove_cv<typename remove_ref<T>::type>::type;

template <typename T> struct remove_extent {
  using type = T;
};
template <typename T, unsigned long N> struct remove_extent<T[N]> {
  using type = T;
};
template <typename T> struct remove_extent<T[]> {
  using type = T;
};

template <typename T>
using remove_extent_t = typename remove_extent<T>::type;

template <typename T> struct is_array : false_type<T> {};
template <typename T> struct is_array<T[]> : true_type<T> {};
template <typename T, unsigned long N> struct is_array<T[N]> : true_type<T> {};

// A type that hides a template parameter from deduction. A parameter of the form
// format_string<type_identity_t<Args>...> is not used to deduce Args, so the arguments of a
// log call are deduced from the values that are logged, not from the format string.
template <typename T> struct type_identity {
  using type = T;
};

template <typename T> using type_identity_t = typename type_identity<T>::type;

template <typename T> struct is_integral : false_type<T> {};
template <> struct is_integral<bool> : true_type<bool> {};
template <> struct is_integral<char> : true_type<char> {};
template <> struct is_integral<signed char> : true_type<signed char> {};
template <> struct is_integral<unsigned char> : true_type<unsigned char> {};
template <> struct is_integral<wchar_t> : true_type<wchar_t> {};
template <> struct is_integral<char16_t> : true_type<char16_t> {};
template <> struct is_integral<char32_t> : true_type<char32_t> {};
template <> struct is_integral<short> : true_type<short> {};
template <> struct is_integral<unsigned short> : true_type<unsigned short> {};
template <> struct is_integral<int> : true_type<int> {};
template <> struct is_integral<unsigned int> : true_type<unsigned int> {};
template <> struct is_integral<long> : true_type<long> {};
template <> struct is_integral<unsigned long> : true_type<unsigned long> {};
template <> struct is_integral<long long> : true_type<long long> {};
template <> struct is_integral<unsigned long long> : true_type<unsigned long long> {};

template <typename T> struct is_floating_point : false_type<T> {};
template <> struct is_floating_point<float> : true_type<float> {};
template <> struct is_floating_point<double> : true_type<double> {};
template <> struct is_floating_point<long double> : true_type<long double> {};

template <typename T> constexpr bool is_signed_v = T(-1) < T(0);

// The detection of the members that the formatter uses.
template <typename From, typename To>
concept convertible_to = requires(From &&from) {
  static_cast<To>(static_cast<From &&>(from));
};

// A type that behaves like a string: it has a c_str() and a size(). This covers std::string and
// std::string_view without the module's interface having to name them.
template <typename T>
concept string_like = requires(T const &t) {
  { t.c_str() } -> convertible_to<char const *>;
  { t.size() } -> convertible_to<unsigned long>;
};

// A type that formats itself: it has a format_to(buffer, capacity) member.
template <typename T>
concept self_formatting = requires(T const &t, char *out, unsigned long capacity) {
  { t.format_to(out, capacity) } -> convertible_to<unsigned long>;
};

// std::forward, without <utility>.
template <typename T> [[nodiscard]] auto forward(T &t) noexcept -> T && {
  return static_cast<T &&>(t);
}

template <typename T> [[nodiscard]] auto forward(T &&t) noexcept -> T && {
  return static_cast<T &&>(t);
}

// ---------------------------------------------------------------------------------------------
// The format specification of a replacement field.
// ---------------------------------------------------------------------------------------------

struct field_spec {
  char fill = ' ';
  char align = '\0';      // '<', '>', '^' or '\0' for the default
  char sign = '\0';       // '+', '-' or '\0'
  bool alternate = false; // '#'
  bool zero_pad = false;  // '0'
  unsigned long width = 0U;
  int precision = -1; // the digits after the decimal point, -1 if not given
  char type = '\0';   // the type character, '\0' if not given
  char default_align = '<'; // the alignment to use when the specification does not give one
};

// ---------------------------------------------------------------------------------------------
// The output buffer: a fixed-capacity buffer on the stack of the caller.
// ---------------------------------------------------------------------------------------------

class message_buffer {
public:
  static constexpr unsigned long capacity = 2048U;

  auto append(char c) -> void {
    if (used < capacity) {
      chars[used++] = c;
    }
  }

  auto append(char const *data, unsigned long length) -> void {
    for (unsigned long i = 0U; i < length && used < capacity; ++i) {
      chars[used++] = data[i];
    }
  }

  // Appends the text, padded to the width of the specification.
  auto append_padded(char const *data, unsigned long length, field_spec const &spec) -> void {
    if (length >= spec.width) {
      append(data, length);
      return;
    }
    auto const padding = spec.width - length;
    auto const align = spec.align != '\0' ? spec.align : spec.default_align;
    if (align == '>') {
      for (unsigned long i = 0U; i < padding; ++i) {
        append(spec.fill);
      }
      append(data, length);
    } else if (align == '^') {
      auto const left = padding / 2U;
      for (unsigned long i = 0U; i < left; ++i) {
        append(spec.fill);
      }
      append(data, length);
      for (unsigned long i = left; i < padding; ++i) {
        append(spec.fill);
      }
    } else {
      append(data, length);
      for (unsigned long i = 0U; i < padding; ++i) {
        append(spec.fill);
      }
    }
  }

  [[nodiscard]] auto data() const -> char const * { return chars; }
  [[nodiscard]] auto size() const -> unsigned long { return used; }

private:
  char chars[capacity]{};
  unsigned long used = 0U;
};

// ---------------------------------------------------------------------------------------------
// The format string scanner. It runs at compile time, to check the format string and to count
// the replacement fields.
// ---------------------------------------------------------------------------------------------

struct scan_result {
  unsigned long fields = 0U;
  unsigned long max_index = 0U;
  bool valid = true;
  bool manual_index = false;
};

[[nodiscard]] consteval auto scan_format(char const *text, unsigned long length) -> scan_result {
  scan_result result{};
  auto automatic = false;
  auto i = 0UL;
  while (i < length) {
    auto const c = text[i];
    if (c == '{') {
      if (i + 1U < length && text[i + 1U] == '{') {
        i += 2U;
        continue;
      }
      auto j = i + 1U;
      auto index = 0UL;
      auto has_index = false;
      while (j < length && text[j] != '}' && text[j] != ':') {
        auto const d = text[j];
        if (d >= '0' && d <= '9') {
          index = index * 10UL + static_cast<unsigned long>(d - '0');
          has_index = true;
        } else {
          result.valid = false;
        }
        ++j;
      }
      if (j < length && text[j] == ':') {
        // The format specification: scan it to the closing brace.
        ++j;
        while (j < length && text[j] != '}') {
          ++j;
        }
      }
      if (j >= length) {
        result.valid = false;
        break;
      }
      if (has_index) {
        result.manual_index = true;
        if (index > result.max_index) {
          result.max_index = index;
        }
      } else {
        automatic = true;
      }
      ++result.fields;
      i = j + 1U;
    } else if (c == '}') {
      if (i + 1U < length && text[i + 1U] == '}') {
        i += 2U;
        continue;
      }
      result.valid = false;
      ++i;
    } else {
      ++i;
    }
  }
  if (automatic && result.manual_index) {
    // The arguments cannot be indexed and counted at the same time.
    result.valid = false;
  }
  return result;
}

// Checks that the format string matches the number of arguments.
template <unsigned long arg_count>
[[nodiscard]] consteval auto format_matches(char const *text, unsigned long length) -> bool {
  auto const result = scan_format(text, length);
  if (!result.valid) {
    return false;
  }
  if (result.manual_index) {
    return result.max_index < arg_count && result.fields <= arg_count;
  }
  return result.fields == arg_count;
}

// ---------------------------------------------------------------------------------------------
// The value formatters.
// ---------------------------------------------------------------------------------------------

[[nodiscard]] auto copy_text(char const *text, unsigned long length, int precision, char *out,
                             unsigned long capacity) noexcept -> unsigned long {
  if (precision >= 0 && static_cast<unsigned long>(precision) < length) {
    length = static_cast<unsigned long>(precision);
  }
  if (length > capacity) {
    length = capacity;
  }
  for (unsigned long i = 0U; i < length; ++i) {
    out[i] = text[i];
  }
  return length;
}

// The length of a null-terminated string.
[[nodiscard]] auto string_length(char const *text) noexcept -> unsigned long {
  auto length = 0UL;
  while (text[length] != '\0') {
    ++length;
  }
  return length;
}

[[nodiscard]] auto digit_char(unsigned long long value, bool upper) noexcept -> char {
  constexpr char lower_digits[] = "0123456789abcdef";
  constexpr char upper_digits[] = "0123456789ABCDEF";
  return upper ? upper_digits[value] : lower_digits[value];
}

template <typename T>
auto format_integer(T value, field_spec &spec, char *out, unsigned long capacity) noexcept
    -> unsigned long {
  auto base = 10U;
  auto upper = false;
  switch (spec.type) {
  case 'x':
    base = 16U;
    break;
  case 'X':
    base = 16U;
    upper = true;
    break;
  case 'o':
    base = 8U;
    break;
  case 'b':
    base = 2U;
    break;
  case 'd':
  case '\0':
  default:
    base = 10U;
    break;
  }

  auto negative = false;
  if constexpr (is_signed_v<T>) {
    negative = value < T(0);
  }
  auto magnitude = static_cast<unsigned long long>(value);
  if (negative) {
    // The unsigned negation is well defined, even for the smallest value.
    magnitude = 0ULL - magnitude;
  }

  char prefix[4]{};
  auto prefix_length = 0UL;
  if (negative) {
    prefix[prefix_length++] = '-';
  } else if (spec.sign == '+') {
    prefix[prefix_length++] = '+';
  } else if (spec.sign == ' ') {
    prefix[prefix_length++] = ' ';
  }
  if (spec.alternate) {
    if (base == 16U) {
      prefix[prefix_length++] = '0';
      prefix[prefix_length++] = upper ? 'X' : 'x';
    } else if (base == 8U) {
      prefix[prefix_length++] = '0';
    } else if (base == 2U) {
      prefix[prefix_length++] = '0';
      prefix[prefix_length++] = 'b';
    }
  }

  char digits[72]{};
  auto digit_count = 0UL;
  do {
    digits[digit_count++] = digit_char(magnitude % base, upper);
    magnitude /= base;
  } while (magnitude != 0U);

  // The zero padding goes between the prefix and the digits.
  auto total = prefix_length + digit_count;
  auto zeros = 0UL;
  if (spec.zero_pad && spec.width > total) {
    zeros = spec.width - total;
    total = spec.width;
  }
  if (total >= capacity) {
    total = capacity - 1U;
  }

  auto at = 0UL;
  for (auto i = 0UL; i < prefix_length && at < capacity; ++i) {
    out[at++] = prefix[i];
  }
  for (auto i = 0UL; i < zeros && at < capacity; ++i) {
    out[at++] = '0';
  }
  for (auto i = digit_count; i > 0U && at < capacity; --i) {
    out[at++] = digits[i - 1U];
  }

  // The zero padding is done here, so the caller does not pad again. Any other padding is left
  // to the caller, which knows the alignment.
  if (zeros > 0U) {
    spec.width = 0U;
  }
  spec.default_align = '>';
  return at;
}

// The formatter of one argument. The type of the argument decides how it is formatted.
template <typename T>
auto format_value(void const *value, field_spec &spec, char *out,
                  unsigned long capacity) noexcept -> unsigned long {
  auto const &v = *static_cast<T const *>(value);
  if constexpr (is_same<T, bool>::value) {
    spec.default_align = '<';
    auto const *text = v ? "true" : "false";
    return copy_text(text, v ? 4U : 5U, spec.precision, out, capacity);
  } else if constexpr (is_same<T, char>::value) {
    spec.default_align = '<';
    return copy_text(&v, 1U, spec.precision, out, capacity);
  } else if constexpr (is_same<T, char const *>::value || is_same<T, char *>::value) {
    spec.default_align = '<';
    return copy_text(v, string_length(v), spec.precision, out, capacity);
  } else if constexpr (is_array<T>::value) {
    // An array - a string literal, for example - is formatted as the string it holds.
    using element = remove_cvref_t<remove_extent_t<T>>;
    static_assert(is_same<element, char>::value || is_same<element, signed char>::value ||
                      is_same<element, unsigned char>::value,
                  "only an array of characters can be formatted");
    spec.default_align = '<';
    auto const *text = static_cast<char const *>(static_cast<void const *>(v));
    return copy_text(text, string_length(text), spec.precision, out, capacity);
  } else if constexpr (is_integral<T>::value) {
    return format_integer(v, spec, out, capacity);
  } else if constexpr (is_floating_point<T>::value) {
    spec.default_align = '>';
    return format_double(static_cast<double>(v), spec.type, spec.precision, out, capacity);
  } else if constexpr (string_like<T>) {
    spec.default_align = '<';
    return copy_text(v.c_str(), static_cast<unsigned long>(v.size()), spec.precision, out, capacity);
  } else if constexpr (self_formatting<T>) {
    spec.default_align = '<';
    return v.format_to(out, capacity);
  } else {
    static_assert(sizeof(T) == 0U,
                  "the type cannot be formatted: give it a format_to(buffer, capacity) member");
    return 0U;
  }
}

// ---------------------------------------------------------------------------------------------
// The value of an argument, as the formatter sees it: the address of the argument itself. The
// formatter knows the type of the argument, so it reads the object at that address - an array is
// read as an array, not as a pointer.
template <typename T> auto argument_value(T &value) -> void const * {
  return static_cast<void const *>(&value);
}

// The formatter of a whole message.
// ---------------------------------------------------------------------------------------------

// Parses a format specification.
auto parse_spec(char const *text, unsigned long length, field_spec &spec) -> void {
  auto i = 0UL;
  if (length >= 2U && (text[1] == '<' || text[1] == '>' || text[1] == '^')) {
    spec.fill = text[0];
    spec.align = text[1];
    i = 2U;
  } else if (length >= 1U && (text[0] == '<' || text[0] == '>' || text[0] == '^')) {
    spec.align = text[0];
    i = 1U;
  }
  if (i < length && (text[i] == '+' || text[i] == '-')) {
    spec.sign = text[i];
    ++i;
  }
  if (i < length && text[i] == '#') {
    spec.alternate = true;
    ++i;
  }
  if (i < length && text[i] == '0') {
    spec.zero_pad = true;
    ++i;
  }
  while (i < length && text[i] >= '0' && text[i] <= '9') {
    spec.width = spec.width * 10UL + static_cast<unsigned long>(text[i] - '0');
    ++i;
  }
  if (i < length && text[i] == '.') {
    ++i;
    spec.precision = 0;
    while (i < length && text[i] >= '0' && text[i] <= '9') {
      spec.precision = spec.precision * 10 + static_cast<int>(text[i] - '0');
      ++i;
    }
  }
  if (i < length) {
    spec.type = text[i];
  }
}

// Appends the text of a format string, with the escaped braces ("{{" and "}}") unescaped.
auto append_escaped(message_buffer &out, char const *text, unsigned long length) -> void {
  auto i = 0UL;
  while (i < length) {
    auto const c = text[i];
    if ((c == '{' || c == '}') && i + 1U < length && text[i + 1U] == c) {
      out.append(c);
      i += 2U;
      continue;
    }
    out.append(c);
    ++i;
  }
}

// Formats the message into the buffer.
template <typename... Args>
auto format_message(message_buffer &out, char const *text, unsigned long length, Args &&...args)
    -> void {
  if constexpr (sizeof...(Args) == 0U) {
    append_escaped(out, text, length);
  } else {
    using formatter_fn = unsigned long (*)(void const *, field_spec &, char *, unsigned long) noexcept;
    formatter_fn const formatters[] = {&format_value<remove_cvref_t<Args>>...};
    void const *const values[] = {argument_value(args)...};

    auto next_index = 0UL;
    auto i = 0UL;
    while (i < length) {
      auto const c = text[i];
      if (c == '{') {
        if (i + 1U < length && text[i + 1U] == '{') {
          out.append('{');
          i += 2U;
          continue;
        }
        auto j = i + 1U;
        auto index = 0UL;
        auto has_index = false;
        while (j < length && text[j] != '}' && text[j] != ':') {
          if (text[j] >= '0' && text[j] <= '9') {
            index = index * 10UL + static_cast<unsigned long>(text[j] - '0');
            has_index = true;
          }
          ++j;
        }
        field_spec spec{};
        if (j < length && text[j] == ':') {
          auto k = j + 1U;
          while (k < length && text[k] != '}') {
            ++k;
          }
          parse_spec(text + j + 1U, k - j - 1U, spec);
          j = k;
        }
        if (j >= length) {
          out.append(text + i, length - i);
          break;
        }
        auto const arg_index = has_index ? index : next_index;
        if (!has_index) {
          ++next_index;
        }
        if (arg_index < static_cast<unsigned long>(sizeof...(Args))) {
          char value[1024]{};
          auto const value_length =
              formatters[arg_index](values[arg_index], spec, value, sizeof(value));
          out.append_padded(value, value_length, spec);
        }
        i = j + 1U;
      } else if (c == '}') {
        if (i + 1U < length && text[i + 1U] == '}') {
          out.append('}');
          i += 2U;
          continue;
        }
        out.append('}');
        ++i;
      } else {
        out.append(c);
        ++i;
      }
    }
  }
}

} // namespace com::rsm::logging::detail
