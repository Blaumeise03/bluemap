#ifndef MAP_H
#define MAP_H
#include <algorithm>
#include <fstream>
#include <functional>
#include <Image.h>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <utility>
#include <vector>

#if defined(EVE_MAPPER_PYTHON) && EVE_MAPPER_PYTHON
#include <Python.h>
#include "PyWrapper.h"
#endif

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

    template<typename T>
    void write_big_endian(std::ofstream &file, T value) {
        if constexpr (sizeof(T) > 1) {
            if (!is_big_endian()) {
                std::reverse(reinterpret_cast<char *>(&value), reinterpret_cast<char *>(&value) + sizeof(T));
            }
        }
        file.write(reinterpret_cast<const char *>(&value), sizeof(T));
    }

    struct OwnerData {
        id_t id = 0;
        Color color;
        bool npc = false;
    };

    struct SolarSystemData {
        id_t id = 0;
        id_t constellation_id = 0;
        id_t region_id = 0;
        unsigned int x = 0;
        unsigned int y = 0;
        bool has_station = false;
        double sov_power = 1.0;
        id_t owner = 0;
    };

    struct JumpData {
        id_t sys_from = 0;
        id_t sys_to = 0;
    };

    class Owner {
        id_t id;
        std::string name;
        Color color;
        bool npc;
        std::mutex guard{};
        unsigned long long count = 0;

    public:
        Owner(id_t id, std::string name, int color_red, int color_green, int color_blue, bool is_npc);

        void increment_counter();

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
        unsigned int sample_rate = 8;

        /// How fast the influence falls off with distance, 0.3 = reduced to 30% per jump
        double power_falloff = 0.3;

        std::map<id_t, Owner *> owners = {};
        std::map<id_t, SolarSystem *> solar_systems = {};
        std::vector<SolarSystem *> sov_solar_systems = {};
        std::map<id_t, std::vector<SolarSystem *> > connections = {};
        mutable std::shared_mutex map_mutex;

        std::mutex image_mutex;
        Image image = Image(width, height);
        std::unique_ptr<Owner *[]> owner_image = nullptr;
        std::unique_ptr<id_t[]> old_owners_image = nullptr;

        // Functional interfaces
        std::function<double(double, bool, id_t)> sov_power_function;

#if defined(EVE_MAPPER_PYTHON) && EVE_MAPPER_PYTHON
        std::unique_ptr<PyClosure<double, double, bool, id_t> > sov_power_closure = nullptr;
#endif

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
            bool render_old_owners = false;

            // The current start offset for the cache
            unsigned int row_offset = 0;

            Image cache;

            std::mutex render_mutex;

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

        struct MapOwnerLabel {
            id_t owner_id = 0;
            unsigned long long x = 0;
            unsigned long long y = 0;
            size_t count = 0;

            MapOwnerLabel();

            explicit MapOwnerLabel(id_t owner_id);
        };

    private:
        /**
         *
         * Performs a flood fill on the owner_image to detect connected regions of the same owner
         * As a result, all entries in the owner_image will be set to nullptr
         *
         * @param x the x coordinate to start the flood fill
         * @param y the y coordinate
         * @param label the label to detect the region
         */
        void owner_flood_fill(unsigned int x, unsigned int y, MapOwnerLabel &label);

    public:
        Map();

        ~Map();

        void update_size(unsigned int width, unsigned int height, unsigned int sample_rate);

        void load_data(const std::string &filename);

        void load_data(const std::vector<OwnerData> &owners,
                       const std::vector<SolarSystemData> &solar_systems,
                       const std::vector<JumpData> &jumps);

        void set_sov_power_function(std::function<double(double, bool, id_t)> sov_power_function);

        void calculate_influence();

        void render();

        void render_multithreaded();

        std::vector<MapOwnerLabel> calculate_labels();

        ColumnWorker *create_worker(unsigned int start_x, unsigned int end_x);

        void paste_cache(unsigned int start_x, unsigned int start_y, const Image &cache, int height = -1);

        void save_owner_image(const std::string &filename) const;

        void load_old_owners(const std::string &filename);

        void debug_save_old_owners(const std::string &filename) const;

        void save(const std::string &filename) const;

        /// Returns and clears the rendered image, the caller is responsible for deleting the data
        [[nodiscard]] uint8_t *retrieve_image();

        /// Returns the owner image, the caller is responsible for deleting the data
        [[nodiscard]] id_t *create_owner_image() const;

        /// Sets the old owner image, this will transfer ownership of the data to the map
        /// Must have a size of width * height
        void set_old_owner_image(id_t *old_owner_image, unsigned int width, unsigned int height);

        [[nodiscard]] unsigned int get_width() const;

        [[nodiscard]] unsigned int get_height() const;

        [[nodiscard]] bool has_old_owner_image() const;

        // Python only API

#if defined(EVE_MAPPER_PYTHON) && EVE_MAPPER_PYTHON
        /**
         * Define the function to calculate the influence of a solar system. For every solar system, this function will
         * be called with the sov_power, has_station and owner_id as arguments. The function must return a double value
         * which will be used as the influence value.
         *
         * The influence then is spread to neighboring solar systems with a reduced value based on the power_falloff.
         *
         * @param closure a python function with the signature (double, bool, int) -> double
         */
        void set_sov_power_function(PyObject *closure);
#endif
    };
} // bluemap

#endif //MAP_H
