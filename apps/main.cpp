#include "antennasim/build_info.hpp"

#include <iostream>
#include <string_view>

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view{argv[1]} == "--version") {
        std::cout << "AntennaSim " << antennasim::version() << '\n';
        return 0;
    }
    if (argc == 1 || (argc == 2 && std::string_view{argv[1]} == "--help")) {
        std::cout << "AntennaSim foundation\n"
                     "Usage: antennasim [--help | --version]\n"
                     "Simulation commands are not available yet.\n";
        return 0;
    }
    std::cerr << "Unsupported arguments. Use --help.\n";
    return 2;
}
