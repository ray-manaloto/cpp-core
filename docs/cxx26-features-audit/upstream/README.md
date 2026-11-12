# The upstream sources this audit quotes

**Date:** 2026-11-12

The files here are **verbatim copies** of upstream sources, so that the audit's claims can be
reviewed without a network connection and without a populated `build/` tree. Nothing here is
compiled, included or used by the project - these are reading copies, not dependencies.

| file | origin | version / ref | licence |
| --- | --- | --- | --- |
| `ut/CMakeLists.txt` | [`stephenberry/ut`](https://github.com/stephenberry/ut), `CMakeLists.txt` | REF `dc65567be78febd265ca36c324e1c504512d4d74` (the REF the project's overlay port pins) | Boost Software License 1.0 - see the header of the file |
| `ut/modules/ut.ixx` | [`stephenberry/ut`](https://github.com/stephenberry/ut), `modules/ut.ixx` | REF `dc65567be78febd265ca36c324e1c504512d4d74` | Boost Software License 1.0 - see the header of the file |
| `stdx/ct_format.hpp` | Intel's [`intel-cpp-std-extensions`](https://github.com/intel/cpp-std-extensions), `include/stdx/ct_format.hpp` | the version installed by the project's overlay port (`version-date` 2026-11-09) | Boost Software License 1.0 - see `stdx/COPYRIGHT` |
| `stdx/detail/fmt.hpp` | as above, `include/stdx/detail/fmt.hpp` | as above | Boost Software License 1.0 - see `stdx/COPYRIGHT` |
| `fmt/base.h` | [`fmtlib/fmt`](https://github.com/fmtlib/fmt), `include/fmt/base.h` | tag `12.2.1` (commit `208219daff58f2a7438f6931cc2ddc358acf33ef`) - **byte-identical to upstream** | MIT - see `fmt/LICENSE` |
| `fmt/format.h` | as above, `include/fmt/format.h` | tag `12.2.1` **+ vcpkg's backport of upstream PR #4813** - see below | MIT - see `fmt/LICENSE` |
| `fmt/compile.h` | as above, `include/fmt/compile.h` | tag `12.2.1` - **byte-identical to upstream** | MIT - see `fmt/LICENSE` |
| `fmt/LICENSE` | as above, `LICENSE` | tag `12.2.1` - **byte-identical to upstream** | the MIT licence text itself |
| `fmt/backport-4813.patch` | vcpkg's own patch, from the vcpkg root's `downloads/fmt-backport-4813.patch` | the patch the vcpkg `fmt` port applies to the 12.2.1 release tarball | MIT - it is part of the fmt sources it patches |

## Why these nine

- **`ut/CMakeLists.txt` and `ut/modules/ut.ixx`** - the answer to "does the test framework's module
  variant work here?" is in upstream's own build file: the `import std` gate table, the
  `UT_ENABLE_MODULES` option, and the module itself. See
  [remaining-research.md](../remaining-research.md) section 3.
- **`stdx/ct_format.hpp` and `stdx/detail/fmt.hpp`** - the evidence for "Intel's compile-time
  formatter is fmt's compile-time API", which is the independent corroboration of the project's fmt
  decision. See [remaining-research.md](../remaining-research.md) section 1.
- **`fmt/base.h`, `fmt/format.h` and `fmt/compile.h`** - the audit quotes fmt's headers more than
  any other third-party source, and they were the last major dependency left unvendored. These are
  the headers the citations point at; see [readme-check.md](../readme-check.md) for the line-by-line
  verification.

## How to check them

The `ut` files were fetched from `raw.githubusercontent.com` at the pinned REF and are byte-identical
to upstream: their git blob hashes are the ones upstream's tree reports for that REF.

```sh
git hash-object docs/cxx26-features-audit/upstream/ut/modules/ut.ixx
# 9b68004c4b480ad414a8b1f84d06bdcb2541c51f
git hash-object docs/cxx26-features-audit/upstream/ut/CMakeLists.txt
# 81a3e3e95f8dc627d942504f997820e3f9a84c23
```

The two `stdx` files were copied from the installed tree
(`build/p2996-debug/vcpkg_installed/arm64-osx-p2996/include/stdx/`), and `stdx/COPYRIGHT` is the
port's own `share/intel-cpp-std-extensions/copyright` file - the Boost Software License 1.0 text.
The Boost Software License requires that the copyright notices and the licence text travel with
copies of the software, so the licence is beside the files it covers.

## The fmt files are **not** pristine upstream 12.2.1

vcpkg downloads the fmt **12.2.1 release tarball** and applies a patch of its own to it. The patch
is vendored here, so the vendored `format.h` can be reconstructed from pristine upstream:

```sh
# 1. fetch the pristine upstream header
curl -sSfL -o format.h \
  https://raw.githubusercontent.com/fmtlib/fmt/12.2.1/include/fmt/format.h

# 2. apply vcpkg's patch (it also touches test/format-test.cc)
git apply docs/cxx26-features-audit/upstream/fmt/backport-4813.patch

# 3. the result is byte-identical to the vendored file
git hash-object format.h
# 0bff24a6bfec476daa63976db457b439431e58ac
git hash-object docs/cxx26-features-audit/upstream/fmt/format.h
# 0bff24a6bfec476daa63976db457b439431e58ac
```

The patch backports upstream PR **#4813** ("Fix fallback uint128 bitwise not") - three lines in
`include/fmt/format.h`:

```diff
+  friend constexpr auto operator~(const uint128& n) -> uint128 {
+    return {~n.hi_, ~n.lo_};
+  }
```

**This changes the line numbers.** The insertion is at `include/fmt/format.h:329-331`, so **every
`format.h` line number after 328 is three higher in the installed file than in pristine upstream**.
The audit's citations are to the *installed* file - `fmt/format.h:2991-3005` for the
shortest-representation code, where pristine upstream has it at 2988-3002:

```console
$ grep -n 'Generate the shortest representation' pristine-upstream-format.h
3002:    // Generate the shortest representation.
$ grep -n 'Generate the shortest representation' installed-format.h
3005:    // Generate the shortest representation.
```

`base.h` and `compile.h` are unaffected, so their citations are the same in both. A reviewer
checking a citation against pristine upstream would have been three lines out on every `format.h`
reference; the vendored copy is the one the citations point at, and the patch is beside it.

The other vendored sources in this repository - quill's headers in
`docs/asan-leak-check/upstream/` and `docs/module-source-location/upstream/`, and the sanitizer
sources in `docs/asan-leak-check/upstream/` - follow the same convention.
