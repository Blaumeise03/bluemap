#include "Image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#include <cstdint>
#include <stdexcept>

Color Color::with_alpha(uint8_t alpha) const {
    return {red, green, blue, alpha};
}

Image::Image(const unsigned int width, const unsigned int height) {
    this->width = width;
    this->height = height;
    this->data = new uint8_t[width * height * 4]; // Allocate memory for RGBA
    std::fill_n(data, width * height * 4, 0);
}

Image::~Image() {
    delete[] data;
}

void Image::set_pixel(const unsigned int x, const unsigned int y, const uint8_t r, const uint8_t g,
                      const uint8_t b) const {
    this->set_pixel(x, y, r, g, b, 255);
}

void Image::set_pixel(const unsigned int x, const unsigned int y, const uint8_t r, const uint8_t g, const uint8_t b,
                      const uint8_t a) const {
    if (x >= width || y >= height) {
        throw std::out_of_range("Pixel out of bounds");
    }
    data[(y * width + x) * 4 + 0] = r;
    data[(y * width + x) * 4 + 1] = g;
    data[(y * width + x) * 4 + 2] = b;
    data[(y * width + x) * 4 + 3] = a;
}

void Image::set_pixel(const unsigned int x, const unsigned int y, const Color &color) const {
    if (x >= width || y >= height) {
        throw std::out_of_range("Pixel out of bounds");
    }
    data[(y * width + x) * 4 + 0] = color.red;
    data[(y * width + x) * 4 + 1] = color.green;
    data[(y * width + x) * 4 + 2] = color.blue;
    data[(y * width + x) * 4 + 3] = color.alpha;
}

void Image::set_pixel_unsafe(const unsigned int x, const unsigned int y, const uint8_t *pixel) const {
    data[(y * width + x) * 4 + 0] = pixel[0];
    data[(y * width + x) * 4 + 1] = pixel[1];
    data[(y * width + x) * 4 + 2] = pixel[2];
    data[(y * width + x) * 4 + 3] = pixel[3];
}

void Image::reset() const {
    std::fill_n(data, width * height * 4, 0);
}

Color Image::get_pixel(const unsigned int x, const unsigned int y) const {
    if (x >= width || y >= height) {
        throw std::out_of_range("Pixel out of bounds");
    }
    return {
        data[(y * width + x) * 4 + 0],
        data[(y * width + x) * 4 + 1],
        data[(y * width + x) * 4 + 2],
        data[(y * width + x) * 4 + 3]
    };
}

const uint8_t *Image::get_pixel_unsafe(const unsigned int x, const unsigned int y) const {
    return &data[(y * width + x) * 4];
}

void Image::write(const char *filename) const {
    if (!stbi_write_png(filename, width, height, 4, data, width * 4)) {
        throw std::runtime_error("Unable to write image");
    }
}

unsigned int Image::get_width() const {
    return width;
}

unsigned int Image::get_height() const {
    return height;
}
