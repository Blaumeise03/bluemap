#ifndef IMAGE_H
#define IMAGE_H
#include <cstdint>

struct Color {
    uint8_t red = 0;
    uint8_t green = 0;
    uint8_t blue = 0;
    uint8_t alpha = 255;

    Color() = default;

    Color(const uint_fast8_t red, const uint_fast8_t green, const uint_fast8_t blue)
        : red(red),
          green(green),
          blue(blue) {
    }

    Color(const uint_fast8_t red, const uint_fast8_t green, const uint_fast8_t blue, const uint_fast8_t alpha)
        : red(red),
          green(green),
          blue(blue),
          alpha(alpha) {
    }

    [[nodiscard]] Color with_alpha(uint8_t alpha) const;
};

class Image {
    unsigned int width;
    unsigned int height;

    uint8_t *data;


public:
    Image(unsigned int width, unsigned int height);

    ~Image();

    void resize(unsigned int width, unsigned int height);

    void alloc();

    void set_pixel(unsigned int x, unsigned int y, uint8_t r, uint8_t g, uint8_t b) const;

    void set_pixel(unsigned int x, unsigned int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a) const;

    void set_pixel(unsigned int x, unsigned int y, const Color &color) const;

    /// Set pixel without bounds checking
    void set_pixel_unsafe(unsigned int x, unsigned int y, const uint8_t *pixel) const;

    void reset() const;

    /// Returns the raw data, THE CALLER IS RESPONSIBLE FOR DELETING IT
    [[nodiscard]] uint8_t *retrieve_data();

    [[nodiscard]] Color get_pixel(unsigned int x, unsigned int y) const;

    /// Get pixel without bounds checking
    [[nodiscard]] const uint8_t *get_pixel_unsafe(unsigned int x, unsigned int y) const;

    void write(const char *filename) const;

    [[nodiscard]] unsigned int get_width() const;

    [[nodiscard]] unsigned int get_height() const;
};


#endif //IMAGE_H
