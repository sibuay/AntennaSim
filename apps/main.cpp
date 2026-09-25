#include "antennasim/build_info.hpp"
#include "closed.hpp"
#include "reference.hpp"

#include <iostream>
#include <string_view>
#include <map>

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view{argv[1]} == "--version") {
        std::cout << "AntennaSim " << antennasim::version() << '\n';
        return 0;
    }
    if (argc == 1 || (argc == 2 && std::string_view{argv[1]} == "--help")) {
        std::cout << "AntennaSim reference CPU solver\n"
                     "Usage: antennasim [--help | --version]\n"
                     "       antennasim --benchmark reference-v1 --suite propagation|stability|smoke --output PATH [--steps N]\n"
                     "       antennasim --benchmark closed-v1 --suite cavity|cavity-spectrum|pec|dielectric|interface|slab-cavity|lossy|dissipation|smoke\n"
                     "              --output PATH [--steps N]\n"
                     "--steps is permitted only for smoke (default 2); fixed suites retain their version-1 parameters.\n"
                     "Writes native solver samples to a fresh directory; physical acceptance is not evaluated.\n";
        return 0;
    }
    try {
        std::map<std::string_view,std::string_view> options;
        for (int i = 1; i < argc; i += 2) {
            const std::string_view key{argv[i]};
            if ((key != "--benchmark" && key != "--suite" && key != "--output" && key != "--steps") ||
                i+1 == argc || !options.emplace(key,argv[i+1]).second)
                throw std::invalid_argument("Unsupported arguments. Use --help.");
        }
        if (!options.contains("--benchmark") || !options.contains("--suite") || !options.contains("--output"))
            throw std::invalid_argument("Unsupported arguments. Require --benchmark, --suite, and --output.");
        const auto benchmark = options.at("--benchmark");
        if (benchmark != "reference-v1" && benchmark != "closed-v1")
            throw std::invalid_argument("Unsupported arguments. --benchmark must be reference-v1 or closed-v1.");
        const auto suite = options.at("--suite");
        if (options.contains("--steps") && suite != "smoke")
            throw std::invalid_argument("Step overrides apply only to smoke.");
        const auto steps = options.contains("--steps") ? antennasim::parse_steps(options.at("--steps")) : 2;
        const std::filesystem::path output{options.at("--output")};
        if (benchmark == "reference-v1") antennasim::benchmark::run_suite(suite,output,steps);
        else antennasim::benchmark::closed::run_suite(suite,output,steps);
        std::cout << "Raw solver output complete; physical acceptance not evaluated.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
