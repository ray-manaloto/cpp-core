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

## Why these four

- **`ut/CMakeLists.txt` and `ut/modules/ut.ixx`** - the answer to "does the test framework's module
  variant work here?" is in upstream's own build file: the `import std` gate table, the
  `UT_ENABLE_MODULES` option, and the module itself. See
  [remaining-research.md](../remaining-research.md) section 3.
- **`stdx/ct_format.hpp` and `stdx/detail/fmt.hpp`** - the evidence for "Intel's compile-time
  formatter is fmt's compile-time API", which is the independent corroboration of the project's fmt
  decision. See [remaining-research.md](../remaining-research.md) section 1.

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

The other vendored sources in this repository - quill's headers in
`docs/asan-leak-check/upstream/` and `docs/module-source-location/upstream/`, and the sanitizer
sources in `docs/asan-leak-check/upstream/` - follow the same convention.
