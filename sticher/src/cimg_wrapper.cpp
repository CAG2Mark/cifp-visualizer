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
    cimg = CImg(width, height);
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
