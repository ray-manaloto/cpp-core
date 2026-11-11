#!/bin/sh
# Builds and runs every measured variant of the module's source-location capture, with both
# compilers.
#
#   docs/module-source-location/repro/run.sh
#
# The compilers are the ones the presets use: clang-p2996 and GCC 16. Override them with
# CLANG=... and GCC=... if they are named differently.

set -u

here=$(cd "$(dirname "$0")" && pwd)
CLANG=${CLANG:-clang++-p2996}
GCC=${GCC:-g++-16}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

variants="v1_gmf_macro v2_header_macro v3_variadic_trailing_defaults v4_format_string"

# Builds one variant with clang: the module interface is precompiled into a PCM, the implementation
# and the importer are compiled against it.
build_clang() {
  dir=$1
  name=$(basename "$dir")
  out="$work/$name-clang"
  mkdir -p "$out"
  cp "$dir"/* "$out"/ 2>/dev/null

  "$CLANG" -std=c++26 -stdlib=libc++ --precompile "$out/demo.cppm" -o "$out/demo.pcm" \
    >"$out/interface.log" 2>&1 || return 1
  "$CLANG" -std=c++26 -stdlib=libc++ -fmodule-file=demo="$out/demo.pcm" -c "$out/impl.cpp" \
    -o "$out/impl.o" >>"$out/interface.log" 2>&1 || return 1
  "$CLANG" -std=c++26 -stdlib=libc++ -fmodule-file=demo="$out/demo.pcm" "$out/use.cpp" "$out/impl.o" \
    -o "$out/use" >>"$out/interface.log" 2>&1 || return 1
  "$out/use"
}

# Builds one variant with GCC: the module interface is compiled into gcm.cache/demo.gcm. GCC looks
# the module file up relative to the working directory, so every step runs in the build directory.
build_gcc() {
  dir=$1
  name=$(basename "$dir")
  out="$work/$name-gcc"
  mkdir -p "$out"
  cp "$dir"/* "$out"/ 2>/dev/null

  (cd "$out" && "$GCC" -std=c++26 -fmodules-ts -c demo.cppm -o demo.o) \
    >"$out/interface.log" 2>&1 || return 1
  (cd "$out" && "$GCC" -std=c++26 -fmodules-ts -fmodule-file=demo=gcm.cache/demo.gcm -c impl.cpp \
    -o impl.o) >>"$out/interface.log" 2>&1 || return 1
  (cd "$out" && "$GCC" -std=c++26 -fmodules-ts -fmodule-file=demo=gcm.cache/demo.gcm use.cpp \
    impl.o -o use) >>"$out/interface.log" 2>&1 || return 1
  "$out/use"
}

report() {
  compiler=$1
  variant=$2
  log=$3
  printf '\n=== %s: %s ===\n' "$compiler" "$variant"
  if grep -q 'error:' "$log" 2>/dev/null; then
    # The first error is the interesting one.
    grep -m 3 -E 'error:' "$log"
  else
    sed -n '1,4p' "$log"
  fi
}

for variant in $variants; do
  dir="$here/$variant"
  printf '\n############################################################\n'
  printf '# %s\n' "$variant"
  printf '############################################################\n'

  if out=$(build_clang "$dir" 2>&1); then
    printf '\n--- clang-p2996 ---\n%s\n' "$out"
  else
    log="$work/$variant-clang/interface.log"
    report "clang-p2996" "$variant" "$log"
  fi

  if out=$(build_gcc "$dir" 2>&1); then
    printf '\n--- GCC 16 ---\n%s\n' "$out"
  else
    log="$work/$variant-gcc/interface.log"
    report "GCC 16" "$variant" "$log"
  fi
done

printf '\nThe variants that report a location are the ones that work: the macro (variants 1 and 2)\n'
printf 'does not reach the importing translation units, and the defaulted parameters after the\n'
printf 'variadic pack (variant 3) change the shape of the call.\n'
