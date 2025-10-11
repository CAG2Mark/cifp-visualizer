#include <Cimg.h>
#include <string>

using namespace cimg_library;
using namespace std;

// this file speeds up compilation by a lot

class CImgUC {
public:
    CImg<unsigned char> cimg;
    CImgUC(string nme);
    CImgUC(unsigned int width, unsigned int height);
    int width() const;
    int height() const;
    unsigned char *data(unsigned int x, unsigned int y, unsigned int z, unsigned int c);
};
