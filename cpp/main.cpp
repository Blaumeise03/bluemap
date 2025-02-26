
#include <functions.h>
#include <iostream>
#include <Map.h>

int main() {
    const auto map = std::make_shared<bluemap::Map>();
    map->load_data("../dump.dat");
    std::cout << "Loaded data, calculating influence" << std::endl;
    map->calculate_influence();
    std::cout << "Rendering" << std::endl;
    map->render_multithreaded();
    std::cout << "Writing image" << std::endl;
    map->save("influence.png");
    return 0;
}
