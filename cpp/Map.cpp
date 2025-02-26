#include "Map.h"

#include <cassert>
#include <cmath>
#include <iostream>
#include <filesystem>
#include <thread>

namespace bluemap {
    Owner::Owner(const id_t id, std::string name, const int color_red, const int color_green, const int color_blue,
                 const bool is_npc): id(id),
                                     name(std::move(name)),
                                     color(color_red, color_green, color_blue),
                                     npc(is_npc) {
    }

    id_t Owner::get_id() const {
        return id;
    }

    std::string Owner::get_name() const {
        return name;
    }

    Color Owner::get_color() const {
        return color;
    }

    bool Owner::is_npc() const {
        return npc;
    }

    SolarSystem::SolarSystem(const id_t id, const id_t constellation_id, const id_t region_id, id_t x, id_t y): id(id),
        constellation_id(constellation_id),
        region_id(region_id), x(x), y(y) {
    }

    SolarSystem::SolarSystem(id_t id, id_t constellation_id, id_t region_id, unsigned int x, unsigned int y,
                             bool has_station, double sov_power, Owner *owner): id(id),
        constellation_id(constellation_id),
        region_id(region_id),
        x(x),
        y(y),
        has_station(has_station),
        sov_power(sov_power),
        owner(owner) {
    }

    void SolarSystem::add_influence(Owner *owner, double value) {
        assert(owner != nullptr);
        // Try and find the owner in the influences vector
        for (auto &influence: influences) {
            if (std::get<0>(influence) == owner) {
                // If the owner is found, update the influence value
                std::get<1>(influence) += value;
                return;
            }
        }
        // If the owner is not found, add a new influence
        influences.emplace_back(owner, value);
    }

    void SolarSystem::set_sov_power(double sov_power) {
        assert(sov_power >= 0.0);
        this->sov_power = sov_power;
    }

    id_t SolarSystem::get_id() const {
        return id;
    }

    id_t SolarSystem::get_constellation_id() const {
        return constellation_id;
    }

    id_t SolarSystem::get_region_id() const {
        return region_id;
    }

    bool SolarSystem::is_has_station() const {
        return has_station;
    }

    double SolarSystem::get_sov_power() const {
        return sov_power;
    }

    Owner *SolarSystem::get_owner() const {
        return owner;
    }

    unsigned int SolarSystem::get_x() const {
        return x;
    }

    unsigned int SolarSystem::get_y() const {
        return y;
    }

    std::vector<std::tuple<Owner *, double> > SolarSystem::get_influences() {
        return influences;
    }

    void Map::add_influence(
        SolarSystem *solar_system,
        Owner *owner,
        const double value,
        const int distance,
        std::vector<id_t> &set
    ) {
        assert(owner != nullptr);
        assert(solar_system != nullptr);
        solar_system->add_influence(owner, value);
        bool found = false;
        for (const auto &sys: sov_solar_systems) {
            if (sys == solar_system) {
                found = true;
                break;
            }
        }
        if (!found) {
            sov_solar_systems.push_back(solar_system);
        }
        if (distance >= 4) return;
        if (connections.find(solar_system->get_id()) == connections.end()) return;
        for (const auto &neighbor: connections[solar_system->get_id()]) {
            if (std::find(set.begin(), set.end(), neighbor->get_id()) != set.end()) {
                continue;
            }
            assert(neighbor != nullptr);
            set.push_back(neighbor->get_id());
            add_influence(neighbor, owner, value * power_falloff, distance + 1, set);
        }
    }

    Map::ColumnWorker::ColumnWorker(Map *map, const unsigned int start_x,
                                    const unsigned int end_x): map(map),
                                                               start_x(start_x),
                                                               end_x(end_x), cache(end_x - start_x, 16) {
        assert(map != nullptr);
        assert(start_x < end_x);
        this->sov_solar_systems = map->sov_solar_systems;
    }

    std::tuple<Owner *, double> Map::ColumnWorker::calculate_influence(unsigned int x, unsigned int y) const {
        std::map<Owner *, double> total_influence = {};
        for (auto &solar_system: map->sov_solar_systems) {
            assert(solar_system != nullptr);
            const int dx = static_cast<int>(x) - static_cast<int>(solar_system->get_x());
            const int dy = static_cast<int>(y) - static_cast<int>(solar_system->get_y());
            const double dist_sq = dx * dx + dy * dy;
            if (dist_sq > 160000) continue;
            for (auto &[owner, power]: solar_system->get_influences()) {
                assert(owner != nullptr);
                //const auto res = total_influence.try_emplace(owner, 0.0);
                const double old = total_influence[owner];
                total_influence[owner] = old + power / (500 + dist_sq);
            }
        }
        double best_influence = 0.0;
        Owner *best_owner = nullptr;
        for (const auto &[owner, influence]: total_influence) {
            if (influence > best_influence) {
                best_owner = owner;
                best_influence = influence;
            }
        }
        if (best_influence < 0.023) best_owner = nullptr;
        return {best_owner, best_influence};
    }

    void Map::ColumnWorker::process_pixel(
        const unsigned int width,
        const unsigned int i,
        const unsigned int y,
        std::vector<Owner *> &this_row,
        const std::vector<Owner *> &prev_row,
        std::vector<double> &prev_influence,
        std::vector<bool> &border
    ) const {
        const unsigned int x = start_x + i;
        auto [owner, influence] = calculate_influence(x, y);

        this_row[i] = owner;

        // Draw image
        const bool owner_changed = prev_row[i] == nullptr && owner != nullptr ||
                                   prev_row[i] != nullptr && owner == nullptr ||
                                   prev_row[i] != nullptr && prev_row[i] != owner;
        if (y > 0) {
            if (
                const auto prev_owner = prev_row[i];
                prev_owner != nullptr && !prev_owner->is_npc()
            ) {
                const bool draw_border = border[i] || owner_changed ||
                                         i > 0 && prev_row[i - 1] != prev_row[i] ||
                                         i < width - 1 && prev_row[i + 1] != prev_row[i];
                const int alpha = std::min(
                    190, static_cast<int>(std::log(std::log(prev_influence[i] + 1.0) + 1.0) * 700));

                const auto color = prev_owner->get_color().with_alpha(
                    draw_border ? std::max(0x48, alpha) : alpha
                );
                cache.set_pixel(i, y - row_offset, color);
            }
        }

        prev_influence[i] = influence;
        border[i] = y == 0 || owner_changed;
    }

    void Map::ColumnWorker::render() {
        const unsigned int width = end_x - start_x;
        const unsigned int height = map->get_height();
        std::vector<Owner *> this_row(width);
        std::vector<Owner *> prev_row(width);
        std::vector<bool> border(width);
        std::vector<double> prev_influence(width);

        for (unsigned int y = 0; y < height; ++y) {
            for (unsigned int i = 0; i < width; ++i) {
                process_pixel(width, i, y, this_row, prev_row, prev_influence, border);
            }

            const auto t = prev_row;
            prev_row = this_row;
            this_row = t;
            if (y > row_offset && y - row_offset == 15) {
                map->paste_cache(start_x, y - 15, cache);
                row_offset = y + 1;
                cache.reset();
                // Fuck C why the hell did this line cause so much trouble: cache = Image(width, 16);
            }
        }
        // Paste the remaining cache
        map->paste_cache(start_x, row_offset, cache, height - row_offset);
    }

    Map::Map() = default;

    Map::~Map() {
        for (auto &[_, owner]: owners) {
            delete owner;
        }
        for (auto &[_, solar_system]: solar_systems) {
            delete solar_system;
        }
    }

    void Map::load_data(const std::string &filename) {
        std::ifstream file(filename, std::ios::binary);
        if (!file) {
            throw std::runtime_error("Unable to open file");
        }

        int owner_size = read_big_endian<int32_t>(file);
        std::cout << "Loading " << owner_size << " owners" << std::endl;
        for (int i = 0; i < owner_size; ++i) {
            int id = read_big_endian<int32_t>(file);
            int name_length = read_big_endian<uint16_t>(file);
            std::string name(name_length, '\0');
            file.read(&name[0], name_length);
            int color_red = read_big_endian<int32_t>(file);
            int color_green = read_big_endian<int32_t>(file);
            int color_blue = read_big_endian<int32_t>(file);
            int is_npc = read_big_endian<uint8_t>(file);

            owners[id] = new Owner(id, name, color_red, color_green, color_blue, is_npc);
        }

        int systems_size = read_big_endian<int32_t>(file);
        std::cout << "Loading " << systems_size << " solar systems" << std::endl;
        for (int i = 0; i < systems_size; ++i) {
            int id = read_big_endian<int32_t>(file);
            int x = read_big_endian<int32_t>(file);
            int y = read_big_endian<int32_t>(file);
            int region_id = read_big_endian<int32_t>(file);
            int constellation_id = read_big_endian<int32_t>(file);
            int has_station = read_big_endian<uint8_t>(file);
            auto adm = read_big_endian<double>(file);
            int sovereignty_id = read_big_endian<int32_t>(file);

            Owner *sovereignty = (sovereignty_id == 0) ? nullptr : owners[sovereignty_id];
            auto sys = new SolarSystem(id, constellation_id, region_id, x, y, has_station, adm, sovereignty);
            solar_systems[id] = sys;
        }

        int jumps_table_size = read_big_endian<int32_t>(file);
        std::cout << "Loading " << jumps_table_size << " connections" << std::endl;
        for (int i = 0; i < jumps_table_size; ++i) {
            int key_id = read_big_endian<int32_t>(file);
            int value_size = read_big_endian<int32_t>(file);

            std::vector<SolarSystem *> value;
            value.reserve(value_size);
            for (int j = 0; j < value_size; ++j) {
                int ss_id = read_big_endian<int32_t>(file);
                value.push_back(solar_systems[ss_id]);
            }
            connections[key_id] = value;
        }
        std::cout << "Loaded " << owners.size() << " owners, " << solar_systems.size() << " solar systems, and "
                << connections.size() << " connections" << std::endl;
    }

    void Map::calculate_influence() {
        if (sov_solar_systems.empty()) {
            for (const auto &sys: solar_systems) {
                if (sys.second->get_owner() != nullptr) {
                    sov_solar_systems.push_back(sys.second);
                }
            }
        }
        std::cout << "Calculating influence for " << sov_solar_systems.size() << " solar systems" << std::endl;
        auto sov_orig = sov_solar_systems;
        for (const auto &solar_system: sov_orig) {
            double influence = 10.0;
            int level = 2;
            if (solar_system->get_sov_power() >= 6.0) {
                influence *= 6;
                level = 1;
            } else {
                influence *= solar_system->get_sov_power() / 2.0;
            }
            std::vector<id_t> set;
            add_influence(solar_system, solar_system->get_owner(), influence, level, set);
        }
    }

    void Map::render_multithreaded() {
        const unsigned int thread_count = std::thread::hardware_concurrency();
        std::vector<std::thread> threads;
        std::vector<ColumnWorker *> workers;
        std::cout << "Starting " << thread_count << " threads" << std::endl;
        for (int i = 0; i < thread_count; ++i) {
            const unsigned int start_x = i * width / thread_count;
            const unsigned int end_x = (i + 1) * width / thread_count;
            workers.emplace_back(create_worker(start_x, end_x));
            std::cout << "Starting thread " << i << " with x range " << start_x << " to " << end_x << std::endl;
            threads.emplace_back(&ColumnWorker::render, workers.back());
        }
        std::cout << "Waiting for threads to finish" << std::endl;
        for (auto &thread: threads) {
            if (thread.joinable())
                thread.join();
        }
        std::cout << "Threads finished" << std::endl;
        for (const auto worker: workers) {
            delete worker;
        }
        std::cout << "Rendering completed" << std::endl;
    }

    Map::ColumnWorker * Map::create_worker(unsigned int start_x, unsigned int end_x) {
        return new ColumnWorker(this, start_x, end_x);
    }

    void Map::paste_cache(const unsigned int start_x, const unsigned int start_y, const Image &cache, int height) {
        std::lock_guard lock(image_mutex);
        if (height == -1) {
            height = cache.get_height();
        }
        for (unsigned int y = 0; y < height; ++y) {
            for (unsigned int x = 0; x < cache.get_width(); ++x) {
                auto [r, g, b, a] = cache.get_pixel(x, y);
                image.set_pixel(start_x + x, start_y + y, r, g, b, a);
            }
        }
    }

    void Map::save(const std::string &filename) const {
        image.write(filename.c_str());
    }

    unsigned int Map::get_width() const {
        return width;
    }

    unsigned int Map::get_height() const {
        return height;
    }

    unsigned int Map::get_offset_x() const {
        return offset_x;
    }

    unsigned int Map::get_offset_y() const {
        return offset_y;
    }

    double Map::get_scale() const {
        return scale;
    }
} // EveMap
