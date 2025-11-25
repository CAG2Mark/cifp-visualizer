#include <Cimg.h>
#include <string>
#include <cimg_wrapper.h>

using namespace cimg_library;
using namespace std;

// this file speeds up compilation by a lot

CImgUC::CImgUC(string nme) {
    cimg = CImg(nme.c_str());
}

CImgUC::CImgUC(unsigned int width, unsigned int height) {
    cimg = CImg(width, height, 1, 3);
}

CImgUC::CImgUC(CImg<unsigned char> &&img) {
    cimg= img;
}

int CImgUC::width() const {
    return cimg.width();
}

int CImgUC::height() const {
    return cimg.height();
}

unsigned char *CImgUC::data(unsigned int x, unsigned int y, unsigned int z, unsigned int c) {
    return cimg.data(x, y, z, c);
}

CImgUC CImgUC::crop(int a, int b) {
    return CImgUC(std::move(cimg.crop(a, b)));
}

CImgUC CImgUC::resize(int a, int b, int c, int d, int e) {
    return CImgUC(std::move(cimg.resize(a, b, c, d, e)));
}

CImgUC CImgUC::fill(int r, int g, int b) {
    for (int x = 0; x < cimg.width(); ++x) {
        for (int y = 0; y < cimg.height(); ++y) {
            *data(x, y, 0, 0) = r;
            *data(x, y, 0, 1) = g;
            *data(x, y, 0, 2) = b;
        }
    }
    return *this;
}

void CImgUC::save_jpeg(const char *file) {
    cimg.save_jpeg(file);
}

unsigned int CImgUC::dimensions() {
    return cimg.spectrum();
}
