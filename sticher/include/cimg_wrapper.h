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
    CImgUC(CImg<unsigned char> &&img);
    int width() const;
    int height() const;
    unsigned char *data(unsigned int x, unsigned int y, unsigned int z, unsigned int c);
    CImgUC crop(int a, int b);
    CImgUC resize(int a, int b, int c, int d, int e);
    CImgUC fill(int r, int g, int b);
    void save_jpeg(const char *file);
    unsigned int dimensions();
};
