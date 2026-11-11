# The variants that were measured

Every directory is a complete, minimal program: a module interface, the module's implementation
and a translation unit that imports the module. `../run.sh` builds and runs all of them with
clang-p2996 and GCC 16.

| directory | what it shows | result |
|---|---|---|
| `v1_gmf_macro/` | a macro in the module's global module fragment | the macro does not reach the importer: `use of undeclared identifier 'GMF_MACRO'` |
| `v2_header_macro/` | a macro in a header that the global module fragment includes | the macro does not reach the importer either |
| `v3_variadic_trailing_defaults/` | the location as defaulted parameters after a variadic pack | the runtime arguments are consumed by the location parameters: `no matching function for call to 'info'` |
| `v4_format_string/` | the location in `format_string`'s constructor's default arguments | **the chosen design**: `file=use.cpp line=4 function=run` |

Each program prints the file, the line and the function that it was called from, so the output can
be compared directly.
