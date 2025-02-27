#ifndef MAP_H
#define MAP_H
#include <algorithm>
#include <fstream>
#include <Image.h>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <utility>
#include <vector>

#if defined(EVE_MAPPER_DEBUG_LOG) && EVE_MAPPER_DEBUG_LOG
#define LOG(x) std::cout << x << std::endl;
#else
#define LOG(x)
#endif

namespace bluemap {
    typedef unsigned long long id_t;

    inline bool is_big_endian() {
        union {
            uint32_t i;
            char c[4];
        } bint = {0x01020304};

        return bint.c[0] == 1;
    }

    template<typename T>
    T read_big_endian(std::ifstream &file) {
        T value;
        file.read(reinterpret_cast<char *>(&value), sizeof(T));
        const bool need_reverse = !is_big_endian();
        if constexpr (sizeof(T) > 1) {
            if (need_reverse) {
                std::reverse(reinterpret_cast<char *>(&value), reinterpret_cast<char *>(&value) + sizeof(T));
            }
        }
        return value;
    }

    class Owner {
        id_t id;
        std::string name;
        Color color;
        bool npc;

    public:
        Owner(id_t id, std::string name, int color_red, int color_green, int color_blue, bool is_npc);

        [[nodiscard]] id_t get_id() const;

        [[nodiscard]] std::string get_name() const;

        [[nodiscard]] Color get_color() const;

        [[nodiscard]] bool is_npc() const;
    };

    class SolarSystem {
        id_t id;
        id_t constellation_id;
        id_t region_id;
        unsigned int x;
        unsigned int y;
        bool has_station = false;
        double sov_power = 1.0;
        Owner *owner = nullptr;
        std::vector<std::tuple<Owner *, double> > influences = {};

    public:
        SolarSystem(id_t id, id_t constellation_id, id_t region_id, id_t x, id_t y);

        SolarSystem(id_t id, id_t constellation_id, id_t region_id, unsigned int x, unsigned int y, bool has_station,
                    double sov_power, Owner *owner);

        void add_influence(Owner *owner, double value);

        void set_sov_power(double sov_power);

        [[nodiscard]] id_t get_id() const;

        [[nodiscard]] id_t get_constellation_id() const;

        [[nodiscard]] id_t get_region_id() const;

        [[nodiscard]] bool is_has_station() const;

        [[nodiscard]] double get_sov_power() const;

        [[nodiscard]] Owner *get_owner() const;

        [[nodiscard]] unsigned int get_x() const;

        [[nodiscard]] unsigned int get_y() const;

        [[nodiscard]] std::vector<std::tuple<Owner *, double> > get_influences();
    };

    class Map {
        unsigned int width = 928 * 2;
        unsigned int height = 1024 * 2;
        unsigned int offset_x = 208;
        unsigned int offset_y = 0;
        double scale = 4.8445284569785E17 / ((width - 20) / 2.0);

        /// How fast the influence falls off with distance, 0.3 = reduced to 30% per jump
        double power_falloff = 0.3;

        std::map<id_t, Owner *> owners = {};
        std::map<id_t, SolarSystem *> solar_systems = {};
        std::vector<SolarSystem *> sov_solar_systems = {};
        std::map<id_t, std::vector<SolarSystem *> > connections = {};

        std::mutex image_mutex;
        Image image = Image(width, height);

        void add_influence(SolarSystem *solar_system,
                           Owner *owner,
                           double value,
                           int distance,
                           std::vector<id_t> &set);

    public:
        class ColumnWorker {
            Map *map;
            unsigned int start_x;
            unsigned int end_x;

            // The current start offset for the cache
            unsigned int row_offset = 0;

            Image cache;
            std::vector<SolarSystem *> sov_solar_systems;

            void flush_cache();

        public:
            ColumnWorker(Map *map, unsigned int start_x, unsigned int end_x);

            [[nodiscard]] std::tuple<Owner *, double> calculate_influence(unsigned int x, unsigned int y) const;

            void process_pixel(
                unsigned int width,
                unsigned int i,
                unsigned int y,
                std::vector<Owner *> &this_row,
                const std::vector<Owner *> &prev_row,
                std::vector<double> &prev_influence,
                std::vector<bool> &border) const;

            void render();
        };

        Map();

        ~Map();

        void load_data(const std::string &filename);

        void calculate_influence();

        void render();

        void render_multithreaded();

        ColumnWorker* create_worker(unsigned int start_x, unsigned int end_x);

        void paste_cache(unsigned int start_x, unsigned int start_y, const Image &cache, int height = -1);

        void save(const std::string &filename) const;

        [[nodiscard]] unsigned int get_width() const;

        [[nodiscard]] unsigned int get_height() const;

        [[nodiscard]] unsigned int get_offset_x() const;

        [[nodiscard]] unsigned int get_offset_y() const;

        [[nodiscard]] double get_scale() const;
    };
} // bluemap

#endif //MAP_H
