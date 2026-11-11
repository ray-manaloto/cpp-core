import demo;

namespace demo {
auto run() -> void { com::rsm::logging::info("the answer is {}", 42); }
} // namespace demo

int main() { demo::run(); }
