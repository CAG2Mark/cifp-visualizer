#include <cimg_wrapper.h>
#include <algorithm>
#include <cstdint>
#include <string>
#include <cmath>
#include <iostream>
#include <vector>
#include <format>

using namespace std;

constexpr double PI = 3.141592653589793;
constexpr double PI4 = PI / 4;
constexpr double INVTAU = 1 / (PI * 2);
constexpr double TO_RAD = PI / 180;
constexpr double TO_DEG = 180 / PI;

using u32 = uint32_t;
using u8 = uint8_t;

// NOTE: not normalized
// take till 2sd
// width: at (center + width), will be 2sd away from the center
double gaussian(double center, double width, double x) {
    double inp = 2 * (x - center) / width;
    return exp(-inp * inp);
}

struct Vec2i {
    int x;
    int y;
    
    void print() {
        cout << "Vec2i(" << x << " " << y << ")\n";
    }
};
struct Vec2f {
    double x;
    double y;
    void print() {
        cout << "Vec2f(" << x << " " << y << ")\n";
    }
};

struct Vec3c {
    u8 x;
    u8 y;
    u8 z;
    
    void print() {
        cout << "Vec3c(" << (int) x << " " << (int) y << " " << (int) z << ")\n";
    }
};

struct Vec3f {
    double x;
    double y;
    double z;
    
    void print() {
        cout << "Vec3c(" << x << " " << y << " " << z << ")\n";
    }
};


class ImageTile {
public:
    int x;
    int y;
    int zoom_level;
    bool inited = false;
    bool failed = false;
    CImgUC img;
    
    ImageTile() : img(CImgUC(256, 256)) {
        
    }
    
    ImageTile(const string fileName) : img(CImgUC(fileName.c_str())) {
        int width = img.width();
        int height = img.height();
        
        if (width != 256 || height != 256) {
            cout << "ERROR: Image is not of size 256x256." << "\n";
            exit(1);
            return;
        }
        
        inited = true;
    }
    
    Vec3c get(u8 x, u8 y) {
        if (img.dimensions() == 3) {
            u8 *r = img.data(x, y, 0, 0);
            u8 *g = img.data(x, y, 0, 1);
            u8 *b = img.data(x, y, 0, 2);
            return Vec3c { *r, *g, *b };
        }
        u8 v = *img.data(x, y, 0, 0);
        return Vec3c { v, v, v };
    }
    
    void fill_white() {
        img.fill(255, 255, 255);
    }
};

// derivative of log(tan(pi / 4 + lat / 2))), i.e. how much the y direction is stretched
// by the mercator projection
double dy(double lat, char zoom_level) {
    double param = (2 * lat + PI) / 4;
    return 0.5 * (1 / sin(param)) * (1 / cos(param));
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
    
    return Vec2i { (int) clamp(floor(x), low, high), (int) clamp(floor(y), low, high) };
}

Vec2f e3857ToWgs(Vec2f xy, char zoom_level) {
    double x = xy.x;
    double y = xy.y;
    
    double tauoverz = pow((double) 2, (double) 1 - zoom_level) * PI; 
    
    double lat = 2 * atan(exp(PI - tauoverz * y)) - PI * 0.5;
    double lon = tauoverz * x - PI;
    
    return Vec2f(TO_DEG * lat, TO_DEG * lon);
}

Vec2f wgsTo3857f(Vec2f latlon, char zoom_level) {
    double lat = latlon.x;
    double lon = latlon.y;
    lat *= TO_RAD;
    lon *= TO_RAD;
     
    double x = INVTAU * (1 << zoom_level) * (PI + lon);
    double y = INVTAU * (1 << zoom_level) * (PI - log(tan(PI4 + lat * 0.5)));
    
    double low = 0;
    double high = 1 << zoom_level;
    
    return Vec2f { clamp(x, low, high), clamp(y, low, high) };
}

class TileSticher {
    int min_x;
    int min_y;
    u32 rows;
    u32 cols;
    int lat;
    int lon;
    char zoom_level;
    
    Vec2f wgs_low;
    Vec2f wgs_high;
    
    Vec2i low;
    Vec2i high;
    
    // NOTE: this is COLUMN major
    // this is for better cache locality
    vector<Vec3c> data;
    
public:
    TileSticher(string images_path, int lat, int lon, char zoom_level)
        : lat(lat), lon(lon), zoom_level(zoom_level) {
        low = wgsTo3857(Vec2f { (double) lat + 1, (double) lon }, zoom_level);
        high = wgsTo3857(Vec2f { (double) lat, (double) lon + 1 }, zoom_level);
        min_x = low.x;
        min_y = low.y;
        
        Vec2f low_f = wgsTo3857f(Vec2f { (double) lat, (double) lon }, zoom_level);
        Vec2f high_f = wgsTo3857f(Vec2f { (double) lat + 1, (double) lon + 1 }, zoom_level);
        
        low_f.x = floor(low_f.x);
        low_f.y = floor(low_f.y);
        high_f.x = ceil(high_f.x);
        high_f.y = ceil(high_f.y);
        wgs_low = e3857ToWgs(low_f, zoom_level);
        wgs_high = e3857ToWgs(high_f, zoom_level);
        
        rows = high.y - low.y + 1;
        cols = high.x - low.x + 1;
        
        data = vector<Vec3c>(65536 * rows * cols);
        
        CImgUC img(256 * rows, 256 * cols);
        
        for (u32 i = 0; i < rows; ++i) {
            for (u32 j = 0; j < cols; ++j) {
                u32 tile_x = j + min_x;
                u32 tile_y = i + min_y;
                
                ImageTile tile;
                try {
                    string filename = std::format("{}/Z{}-{}-{}.jpg", images_path, (int) zoom_level, tile_x, tile_y);
                    tile = ImageTile(filename);
                } catch (CImgException& e) {
                    // just use a white image (which is what the web services return if there is a failure)
                    tile.fill_white();
                }
                
                u32 start_row = i * 256;
                u32 start_col = j * 256;
                
                // ImageTile is small enough that it's probably all cached immediately
                for (int xx = 0; xx < 256; ++xx) {
                    for (int yy = 0; yy < 256; ++yy) {
                        u32 row = start_row + yy;
                        u32 col = start_col + xx;
                        
                        // transpose: switch to column major
                        data[col * rows * 256 + row] = tile.get(xx, yy);
                        auto tmp = get_at(col, row);
                        *img.data(row, col, 0, 0) = tmp.x;
                        *img.data(row, col, 0, 1) = tmp.y;
                        *img.data(row, col, 0, 2) = tmp.z;
                    }
                }
            }
        }
    }
    
    Vec3c get_at(u32 x, u32 y) {
        return data[x * rows * 256 + y];
    }
    
    
    CImgUC stitch(u32 size) {
        // the images are uniform in the x direction, but not the y direction
        // we minify the y-direction first
     
        u32 width = cols * 256;
        u32 height = 1 << (zoom_level - 1);
        
        u32 num_rows = rows * 256;
        
        double x_step = (wgs_high.y - wgs_low.y) / width;
        double y_step = (double) 1 / height;
        
        double lat_start = lat;
        double lon_start = wgs_low.y;
        
        CImgUC out_img(width, height);
        
        // process column by column
        for (u32 x = 0; x < width; ++x) {
            for (u32 y = 0; y < height; ++y) {
                // fills the pixel at position (x, y)
                Vec2f latlon { lat_start + (height - y - 1) * y_step, lon_start + x * x_step };
                // we only care about the y coord here, x can be gotten directly here
                Vec2f tile_c = wgsTo3857f(latlon, zoom_level);
                
                double y_c = 256 * (tile_c.y - low.y);
                
                // Get nearest y
                int y_idx = clamp((int) std::round(y_c), 0, (int) num_rows - 1);
                
                // >= 0
                double deriv = dy(TO_RAD * latlon.x, zoom_level) * num_rows / height;
                
                Vec3c pixel;
                Vec3f pixel_f {0, 0, 0};
                
                if (deriv < 1.05f) {
                    // just directly take the pixel
                    pixel = get_at(x, y_idx);
                } else {
                    int deriv_ceil = ceil(deriv); // sample around y_idx by deriv_ceil using gaussian function
                    // for normalization
                    double total_weight = 0;
                    for (int i = -deriv_ceil + 1; i < deriv_ceil; ++i) {
                        int idx = y_idx + i;
                        if (idx < 0 || idx >= (int) num_rows) continue;
                        double weight = gaussian(y_c, deriv / 2, idx);
                        total_weight += weight;
                        Vec3c pix = get_at(x, idx);
                        pixel_f.x += weight * pix.x;
                        pixel_f.y += weight * pix.y;
                        pixel_f.z += weight * pix.z;
                    }
                    pixel = {
                        (u8) clamp(pixel_f.x / total_weight, (double) 0, (double) 255),
                        (u8) clamp(pixel_f.y / total_weight, (double) 0, (double) 255),
                        (u8) clamp(pixel_f.z / total_weight, (double) 0, (double) 255)
                    };
                }

                *out_img.data(x, y, 0, 0) = pixel.x;
                *out_img.data(x, y, 0, 1) = pixel.y;
                *out_img.data(x, y, 0, 2) = pixel.z;
            }
        }
        
        double lon_s = lon - lon_start;
        double lon_e = lon_s + 1;
        
        if (lon_e > wgs_high.y) {
            cout << "ERROR!" << "\n";
            exit(1);
        }
        
        double lon_width = wgs_high.y - wgs_low.y;
        
        int x_start = (int) (lon_s / lon_width * width);
        int x_end = (int) (lon_e / lon_width * width) - 1;
        
        int x_size = (int) (cos(TO_RAD * clamp((double) max(lat, lat + 1), -85.05, 85.05)) * size);
        // now eveything is in lat/long coordinates, and we can just resize linearly
        // note that the x-y direction is not correct. we need to crop it first

        return out_img
            .crop(x_start, x_end)
            .resize(x_size, size, 1, 3, 5);
    }
};

int main(int argc, char *argv[]) {
    int lat, lon, zl;
    
    if (argc != 4) {
        cout << "Incorrect number of arguments\n";
        return 1;
    }
    
    lat = stoi(argv[1]);
    lon = stoi(argv[2]);
    zl = stoi(argv[3]);
    
    CImgUC img = TileSticher("cache/images", lat, lon, zl).stitch(1 << (zl - 1));
    string out_file = format("cache/tileimg/Z{}-{}-{}.jpg", zl, lat, lon);
    img.save_jpeg(out_file.c_str());
}
