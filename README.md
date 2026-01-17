# cifp-visualizer
Visualizes real-world flight procedures in 3D with the surrounding terrain!

The code is quite messy because I made this for a 2.5 month long course project. PRs welcome if you wish to improve it.

# Features
- Reads navigation data in X-Plane 12's format
- Default navigation data included! (X-Plane 12's default navdata is GNU GPL v2 licensed)
- 3D visualization of flight procedures
- Respects altitude constraints
- Takes into account turn radii, climb rate, and descent rate

# Using
On Linux x86, simply run ./start.sh. You will need Python 3.10 or later.

On Mac (untested) or any other Unix-like environment, make sure you have `gcc` or `clang`, Python >= 3.10, and `pip` installed, then run `recompile.sh`. Then run `./start.sh`.

On Windows, you are out of luck. Use WSL or try to hack your way around it using cygwin and MinGW.
