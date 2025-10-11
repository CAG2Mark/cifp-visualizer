#include <cimg_wrapper.h>
#include <algorithm>
#include <array>
#include <string>
#include <cmath>
#include <iostream>

using namespace std;

constexpr double PI = 3.141592653589793;
constexpr double PI4 = PI / 4;
constexpr double INVTAU = 1 / (PI * 2);
constexpr double TO_RAD = PI / 180;

template<unsigned int N>
array<double, N> gaussian(double width) {
    double total = 0;
    double step = width / N;
    array<double, N> ret;
    for (unsigned int i = 0; i < N; ++i) {
        double x2 = (i * step) * (i * step);
        double val = exp(-x2);
        ret[i] = val;
        total += val;
        if (i > 0) total += val;
    }
    total = 1 / total;
    for (unsigned int i = 0; i < N; ++i) {
        ret[i] *= total;
    }
    return ret;
}

struct Vec2i {
    int x;
    int y;
};
struct Vec2f {
    double x;
    double y;
};

struct Vec3c {
    unsigned char x;
    unsigned char y;
    unsigned char z;
    
    void print() {
        cout << "Vec3c(" << (int) x << " " << (int) y << " " << (int) z << ")\n";
    }
};

class ImageTile {
public:
    int x;
    int y;
    int zoom_level;
    bool inited = false;
    
    Vec3c data[65536];
    ImageTile(const string fileName) {
        CImgUC img(fileName.c_str());
        int width = img.width();
        int height = img.height();
        
        if (width != 256 || height != 256) {
            cout << "ERROR: Image is not of size 256x256." << "\n";
            return;
        }
        
        // see https://cimg.eu/CImg_reference.pdf Chapter 9
        for (int i = 0; i < width; ++i) {
            for (int j = 0; j < height; ++j) {
                unsigned char *r = img.data(j, i, 0, 0);
                unsigned char *g = img.data(j, i, 0, 1);
                unsigned char *b = img.data(j, i, 0, 2);
                data[i * 256 + j] = Vec3c { *r, *g, *b };
            }
        }
        
        inited = true;
    }
    
    Vec3c get(unsigned char x, unsigned char y) const {
        return data[(int) x * 256 + y];
    }
};

double dy(double lat, char zoom_level) {
    // y = 1 / (2 * pi) * (1 << zoom_level) * (pi - log(tan(pi / 4 + lat / 2)))    
    // derivative - log(tan(pi / 4 + lat / 2))) is:
    // -1/2 csc((2x + pi)/4) sec((2x+pi)/4)
    double param = (2 * lat + PI) / 4;
    double coeff = -INVTAU * (1 << zoom_level) * 0.5;
    return coeff * (1 / sin(param)) * (1 / cos(param));
}

Vec2i wgsTo3857(Vec2f latlon, char zoom_level) {
    double lat = latlon.x;
    double lon = latlon.y;
    lat *= TO_RAD;
    lon *= TO_RAD;
     
    double x = INVTAU * (1 << zoom_level) * (PI + lon);
    double y = INVTAU * (1 << zoom_level) * (PI - log(tan(PI4 + lat * 0.5)));
    
    double low = 0;
    double high = (1 << zoom_level) - 1;
    
    return Vec2i { (int) clamp(x, low, high), (int) clamp(y, low, high) };
}



void stich_img(string images_path, int lat, int lon) {
    
}

int main() {
    ImageTile tile("../cache/images/Z13-6692-3575.png");
    for (int i = 0; i < 10; ++i) {
        tile.data[i].print();
    }
}
