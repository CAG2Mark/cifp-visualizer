import math
import logging
from downloaders import *

logger = logging.getLogger("cifp-viewer")

def clamp(x: float, a: float, b: float) -> float:
  return min(max(x, a), b)

# https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#ECMAScript_.28JavaScript.2FActionScript.2C_etc..29
def wgsTo3857(lat: float, lon: float, zoom_level: int) -> tuple[int, int]:
  lat *= pi / 180
  lon *= pi / 180
  
  x = 1 / (2 * pi) * (1 << zoom_level) * (pi + lon)
  y = 1 / (2 * pi) * (1 << zoom_level) * (pi - log(tan(pi / 4 + lat / 2)))
  
  low = 0
  high = (1 << zoom_level) - 1
  
  return int(clamp(floor(x), low, high)), int(clamp(floor(y), low, high))

def required3757Tiles(tile: Tile, zoom_level: int) -> list[Tile3587]:
  low_x, low_y = wgsTo3857(tile.lat + 1, tile.lon, zoom_level)
  high_x, high_y = wgsTo3857(tile.lat, tile.lon + 1, zoom_level)
  
  print(low_x, low_y)
  print(high_x, high_y)
  
  tiles = []
  for x in range(low_x, high_x + 1):
    for y in range(low_y, high_y + 1):
      tiles.append(Tile3587(x, y, zoom_level))
  return tiles

def make_downloader(tile: Tile, zoom_level: int):
  reqd = required3757Tiles(tile, zoom_level)
  return (EoxDownloader(32), reqd)

# the website is kind of messy and has lots of inconsistent names
# and some newer names have "v2" at the end
def get_vfp_file(tile: Tile):
  lat = tile.lat
  lon = tile.lon
  
  # special cases, by inspecting the files themselves
  if -90 <= lat <= -66 and 90 <= lon <= 179:
    return "ANTDEM3/46-60"
  if 61 <= lat <= 62 and -8 <= lon <= -7:
    return "dem3/FAR"
  if 59 <= lat <= 63 and -52 <= lon <= -41:
    return "dem3/GL-South"
  if 75 <= lat <= 83 and -78 <= lon <= -12:
    return "dem3/GL-North"
  if 70 <= lat <= 71 and -10 <= lon <= -8:
    return "dem3/JANMAYEN"
  if 63 <= lat <= 66 and -25 <= lon <= -14:
    return "dem3/ISL"
  if -90 <= lat <= -66 and 0 <= lon <= 89:
    return "ANTDEM3/31-45"
  if 64 <= lat <= 75 and -42 <= lon <= -18:
    return "dem3/GL-East"
  if -90 <= lat <= -62 and -90 <= lon <= -1:
    return "ANTDEM3/16-30"
  if 64 <= lat <= 75 and -68 <= lon <= -43:
    return "dem3/GL-West"
  if -90 <= lat <= -72 and -180 <= lon <= -91:
    return "ANTDEM3/01-15"
  if 74 <= lat <= 74 and 18 <= lon <= 19:
    return "dem3/BEAR"
  if 60 <= lat <= 60 and -3 <= lon <= -1:
    return "dem3/SHL"
  if 76 <= lat <= 80 and 10 <= lon <= 33:
    return "dem3/SVALBARD"
  
  horizontal = (lon + 180) // 6 + 1
  vertical = abs(math.floor(lat // 4))
  south = lat < 0
  if south:
    vertical -= 1
  
  letter = chr(vertical + 65)
  
  v2 = False
  if not south:
    # v2 special casing
    if "P" <= letter <= "Q" and 32 <= horizontal <= 40: v2 = True
    if letter == "R" and 33 <= horizontal <= 38: v2 = True
  
  return "dem3/" + ("S" if south else "") + letter + str(horizontal) + ("v2" if v2 else "")



if __name__ == "__main__":
  # testing
 print(get_vfp_file(Tile(69, 50)))
  
# ImageDownloader().download_images([Tile3587(1, 2, 5)], 1, 0)
