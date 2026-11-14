// Copyright 2024 cpp-core authors
//
// cpp-core: the application's entry point.
//
// The main is a stub: the log calls live in the application library, so that the string catalog
// tooling can find them (see cmake/catalog.cmake).

import com.rsm.logging;

namespace demo {
auto run() -> void;
}

int main() {
  com::rsm::logging::setup();
  demo::run();
  com::rsm::logging::flush();
  return 0;
}
