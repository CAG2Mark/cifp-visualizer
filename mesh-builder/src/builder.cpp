#include <cstdint>
#include <fstream>
#include <string>
#include <iostream>
#include <cmath>
#include <format>

using namespace std;

// for my own reference:
// earth circumference = 21600 nautical miles (approx)
// 1 nautical mile = 1 arc minute at the equator (approx)
//
// all distances in the mesh are in nautical miles,
// i.e. 1 unit of distance = 1nm
//
// x = cos(lat) cos(lat)
// y = sin(lat)
// z = cos(lat) sin(lat)

constexpr double PI = 3.141592653589793;
constexpr double TO_RAD = PI / 180;
constexpr double to_rad(double degs) {
    return degs * TO_RAD;
}
constexpr double EARTH_RAD = 3443.9184665; // at sea level, in nautical miles
constexpr double TO_NM = (double) 1 / 1852;
constexpr double to_nm(double metres) {
    return metres * TO_NM;
} 

int load_data(int16_t *&out, size_t &size, const string &nme) {
    ifstream is(nme, ifstream::binary);
    if (is) {
        // get length of file
        is.seekg(0, is.end);
        size_t length = is.tellg();
        is.seekg(0, is.beg);

        // init buffer, read
        char *buff = new char[length];
        is.read(buff, length);
        
        size_t len = length >> 1;
        
        // data is stored in big endian in hgt files, need to swap bytes
        // before converting to 16 bit
        for (size_t i = 0; i < len; ++i) {
            int16_t tmp = buff[i * 2];
            buff[i * 2] = buff[i * 2 + 1];
            buff[i * 2 + 1] = tmp; 
        }
        
        // convert to 16 bit signed int
        out = (int16_t *) buff;
        
        // hgt files are always either one of these two sizes
        // (3 arc seconds or 1 arc second)
        if (len == 1201 * 1201) {
            size = 1201;
        } else if (len == 3601 * 3601) {
            size = 3601;
        } else {
            return 2;
        }

        return 0;
    } else {
        return 1;
    }
}

struct IdxLatLon {
    size_t row;
    size_t col;
    double lat;
    double lon;
};

struct Vec3 {
    double x, y, z;
};

class HgtData {
    int16_t *data;
    
private:
    void load(const string &nme) {
        ok = load_data(data, size, nme) == 0;
    }
public:
    size_t size;
    bool ok;
    
    HgtData(const string &nme) {
        this->load(nme);
    }
    ~HgtData() {
        delete[] data;
    }
    
    int16_t get_data(size_t row, size_t col) const {
        if (!ok || row < 0 || col < 0 || row >= size || col >= size) {
            return -32768;
        }
        return data[row * size + col];
    }
    
    Vec3 toPoint(const IdxLatLon &idx) {
        int16_t hgt = get_data(idx.row, idx.col);
        if (hgt == -32768) hgt = 0;
        double radius = EARTH_RAD + to_nm(hgt);
        
        // NOTE: in ThreeJS, the x/z axes are different from what we expect from
        // an x/y plane, namely if x is facing right, and y faces up, z faces backwards
        // it is necessary to invert the z
        return Vec3 {
            radius * cos(idx.lat) * cos(idx.lon),
            radius * sin(idx.lat),
            - radius * cos(idx.lat) * sin(idx.lon)
        };
        
    };
    
    void fill_points(Vec3 *&points, double llat, double ulat, double llon, double ulong) {
        points = new Vec3[size * size];
        double latstep = (ulat - llat) / (size - 1);
        double lonstep = (ulong - llon) / (size - 1);
        
        for (size_t i = 0; i < size; ++i) {
            for (size_t j = 0; j < size; ++j) {
                IdxLatLon cur = { i, j, llat + latstep * (size - i - 1), llon + lonstep * j };
                Vec3 point = toPoint(cur);
                points[i * size + j] = { point.x, point.y, point.z };
            }
        }
    }
    
    // x, y are between 0 and 1, i.e. in arc minutes
    double interpolate(double y, double x) {
        // for now, just do linear interpolation
        if (x < 0 || y < 0 || x > 1 || y > 1) {
            return -32768;
        }
        // - 1, because the extra row/col at the end of the data
        // is the right/bottom endpoint data and extends past 1 arc minute
        size_t lower_row = (int) (y * (size - 1));
        size_t lower_col = (int) (y * (size - 1));
        size_t upper_row = lower_row + 1;
        size_t upper_col = lower_col + 1;
        
        int16_t l_row = get_data(lower_row, lower_col);
        return 0; // TODO
    }
};

// a -> b -> c should be counter clockwise when facing them
inline Vec3 normal(const Vec3 &a, const Vec3 &b, const Vec3 &c) {
    Vec3 v1 { b.x - a.x, b.y - a.y, b.z - a.z};
    Vec3 v2 { c.x - a.x, c.y - a.y, c.z - a.z};
    Vec3 cross = {
        v1.y * v2.z - v1.z * v2.y,
        v1.z * v2.x - v1.x * v2.z,
        v1.x * v2.y - v1.y * v2.x
    };
    double mag = 1 / sqrt(cross.x * cross.x + cross.y * cross.y + cross.z * cross.z);
    
    cross.x *= mag;
    cross.y *= mag;
    cross.z *= mag;
    
    return cross;
}

struct Array4 {
    char arr[4];
};

// for ensuring little endianness as requierd by STL format
inline void make_little_endian(uint32_t val, Array4 &buf) {
    for (size_t i = 0; i < 4; ++i) {
        buf.arr[i] = (char) (val & 0xff);
        val >>= 8;
    }
}

inline void make_little_endian(double val, Array4 &buf) {
    float valf = (float) val;
    return make_little_endian(*((uint32_t *) &valf), buf);
}

inline void write_vec(const Vec3 &vec, ofstream &out) {
    Array4 buf;
    make_little_endian(vec.x, buf);
    out.write(buf.arr, 4);
    make_little_endian(vec.y, buf);
    out.write(buf.arr, 4);
    make_little_endian(vec.z, buf);
    out.write(buf.arr, 4);
}

inline void write_triangle(const Vec3 &a, const Vec3 &b, const Vec3 &c, const Vec3 &norm, ofstream &out) {
    char zeros[2] = { 0 };
    write_vec(norm, out);
    write_vec(a, out);
    write_vec(b, out);
    write_vec(c, out);
    out.write(zeros, 2);
}

void export_stl(Vec3 *points, size_t size) {
    // export STL
    /* format from wikipedia:
    UINT8[80]    – Header                 - 80 bytes
    UINT32       – Number of triangles    - 04 bytes
    foreach triangle                      - 50 bytes
        REAL32[3] – Normal vector         - 12 bytes
        REAL32[3] – Vertex 1              - 12 bytes
        REAL32[3] – Vertex 2              - 12 bytes
        REAL32[3] – Vertex 3              - 12 bytes
        UINT16    – Attribute byte count  - 02 bytes
    end
    */
    
    
    
    ofstream out("../viewer/out.stl", ofstream::binary);
    
    uint32_t num_triangles = (size - 1) * (size - 1) * 2;
    
    cout << num_triangles << "\n";
    
    char header[80] = { 0 };
    Array4 triangles;
    make_little_endian(num_triangles, triangles);
    
    out.write(header, sizeof(header));
    out.write(triangles.arr, 4);
    
    for (size_t i = 0; i < size - 1; ++i) {
        for (size_t j = 0; j < size - 1; ++j) {
            Vec3 leftT = points[i * size + j];
            Vec3 rightT = points[i * size + j + 1];
            Vec3 leftB = points[(i + 1) * size + j];
            Vec3 rightB = points[(i + 1) * size + j + 1];
            
            Vec3 norm = normal(leftT, leftB, rightT);
            
            write_triangle(leftT, leftB, rightT, norm, out);
            write_triangle(rightT, leftB, rightB, norm, out);
        }
    }

}

void export_obj(Vec3 *points, size_t size, const string &filename) {
    ofstream out(filename);
    
    // vertices
    size_t N = size * size;
    for (size_t i = 0; i < N; ++i) {
        Vec3 point = points[i];
        out << "v\t";
        out << (float) point.x << "\t" << (float) point.y << "\t" << (float) point.z << "\n";
    }

    float step = (float) 1 / (size - 1);

    // texture coordinates  
    for (size_t i = 0; i < size; ++i) {
        for (size_t j = 0; j < size; ++j) {
            out << "vt\t" << j * step << "\t" << (size - i - 1) * step << "\n";
        }
    }

    // faces
    for (size_t i = 0; i < size - 1; ++i) {
        for (size_t j = 0; j < size - 1; ++j) {
            size_t leftT = 1 + i * size + j;
            size_t rightT = 1 + i * size + j + 1;
            size_t leftB = 1 + (i + 1) * size + j;
            size_t rightB = 1 + (i + 1) * size + j + 1;
            string ln = std::format(
                "f\t{}/{}\t{}/{}\t{}/{}\t{}/{}",
                leftT, leftT,
                leftB, leftB,
                rightB, rightB,
                rightT, rightT
            );
            out << ln << "\n";
        }
    }
    out << "\n";
}

// note: the data goes from west to east, then north to south
void make_mesh(const string &nme, const string &filename, double llat, double ulat, double llon, double ulon) {
    HgtData data(nme);
    
    llat = to_rad(llat);
    ulat = to_rad(ulat);
    llon = to_rad(llon);
    ulon = to_rad(ulon);
    
    size_t size = data.size;
    Vec3 *points;
    data.fill_points(points, llat, ulat, llon, ulon);
    
    export_obj(points, size, filename);
    
    delete[] points;
}

int main(int argc, char *argv[]) {
    int lat, lon;
    if (argc != 3) {
        cout << "Incorrect number of arguments\n";
        return 1;
    }
    
    lat = stoi(argv[1]);
    lon = stoi(argv[2]);
    
    int latu = lat + 1;
    int lonu = lon + 1;
    
    char NS, WE;
    if (lat < 0) NS = 'S';
    else NS = 'N';
    if (lon < 0) WE = 'W';
    else WE = 'E';
    
    string lats = to_string(abs(lat));
    lats.insert(lats.begin(), 2 - lats.length(), '0');
    
    string lons = to_string(abs(lon));
    lons.insert(lons.begin(), 3 - lons.length(), '0');
    
    string file = std::format("cache/dem/{}{}{}{}.hgt", NS, lats, WE, lons);
    string out = std::format("cache/tilemesh/DEM_{}_{}.obj", lat, lon);
    
    make_mesh(file, out, lat, latu, lon, lonu);
}
