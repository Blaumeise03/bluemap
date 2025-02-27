
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
    map->save_owner_image("owners.bin");
    std::cout << "Calculating labels" << std::endl;
    auto labels = map->calculate_labels();
    for (const auto &label: labels) {
        std::cout << "Owner " << label.owner_id << " at " << label.x << ", " << label.y << " with " << label.count
                  << " pixels" << std::endl;
    }

    return 0;
}
