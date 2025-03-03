#include "Image.h"

#if defined(EVE_MAPPER_LINK_STB) && EVE_MAPPER_LINK_STB
#ifndef STB_IMAGE_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#endif
#include "stb_image_write.h"
#endif

#include <cstdint>
#include <stdexcept>

Color Color::with_alpha(uint8_t alpha) const {
    return {red, green, blue, alpha};
}

void Image::alloc() {
    if (data != nullptr) return;
    this->data = new uint8_t[width * height * 4]; // Allocate memory for RGBA
    std::fill_n(data, width * height * 4, 0);
}

Image::Image(const unsigned int width, const unsigned int height) : data(nullptr) {
    this->width = width;
    this->height = height;
    alloc();
}

Image::~Image() {
    delete[] data;
    data = nullptr;
}

void Image::resize(const unsigned int width, const unsigned int height) {
    delete[] data;
    data = nullptr;
    this->width = width;
    this->height = height;
    alloc();
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
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");

    data[(y * width + x) * 4 + 0] = r;
    data[(y * width + x) * 4 + 1] = g;
    data[(y * width + x) * 4 + 2] = b;
    data[(y * width + x) * 4 + 3] = a;
}

void Image::set_pixel(const unsigned int x, const unsigned int y, const Color &color) const {
    if (x >= width || y >= height) {
        throw std::out_of_range("Pixel out of bounds");
    }
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");

    data[(y * width + x) * 4 + 0] = color.red;
    data[(y * width + x) * 4 + 1] = color.green;
    data[(y * width + x) * 4 + 2] = color.blue;
    data[(y * width + x) * 4 + 3] = color.alpha;
}

void Image::set_pixel_unsafe(const unsigned int x, const unsigned int y, const uint8_t *pixel) const {
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");

    data[(y * width + x) * 4 + 0] = pixel[0];
    data[(y * width + x) * 4 + 1] = pixel[1];
    data[(y * width + x) * 4 + 2] = pixel[2];
    data[(y * width + x) * 4 + 3] = pixel[3];
}

void Image::reset() const {
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");
    std::fill_n(data, width * height * 4, 0);
}

uint8_t * Image::retrieve_data() {
    const auto d = data;
    this->data = nullptr;
    return d;
}

Color Image::get_pixel(const unsigned int x, const unsigned int y) const {
    if (x >= width || y >= height) {
        throw std::out_of_range("Pixel out of bounds");
    }
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");
    return {
        data[(y * width + x) * 4 + 0],
        data[(y * width + x) * 4 + 1],
        data[(y * width + x) * 4 + 2],
        data[(y * width + x) * 4 + 3]
    };
}

const uint8_t *Image::get_pixel_unsafe(const unsigned int x, const unsigned int y) const {
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");
    return &data[(y * width + x) * 4];
}

void Image::write(const char *filename) const {
    if (data == nullptr)  throw std::runtime_error("Image has not been allocated");
#if defined(EVE_MAPPER_LINK_STB) && EVE_MAPPER_LINK_STB
    if (!stbi_write_png(filename, width, height, 4, data, width * 4)) {
        throw std::runtime_error("Unable to write image");
    }
#else
    throw std::runtime_error("STB image write is not linked");
#endif
}

unsigned int Image::get_width() const {
    return width;
}

unsigned int Image::get_height() const {
    return height;
}
