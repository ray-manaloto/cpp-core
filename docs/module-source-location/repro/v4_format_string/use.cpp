import demo;

namespace demo {
auto helper() -> void { com::rsm::logging::info("from helper", 1); }
auto run() -> void { com::rsm::logging::info("the answer is {}", 42); }
} // namespace demo

int main() {
  demo::run();
  demo::helper();
}
