import os
import logging
from downloaders import *

logging.basicConfig(format='[%(asctime)s] %(name)s (%(levelname)s): %(message)s')
logger = logging.getLogger("cifp-viewer")
logger.setLevel(logging.WARN)

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

def prepare_tiles(tiles: list[Tile], zoom_level: int):
  if not os.path.exists("cache"):
    os.mkdir("cache")
  if not os.path.exists("cache/images"):
    os.mkdir("cache/images")
  if not os.path.exists("cache/dem"):
    os.mkdir("cache/dem")
    
  for tile in tiles:
    ans = required3757Tiles(tile, zoom_level)
    EoxDownloader(32).download_images(ans)

prepare_tiles([Tile(78, 15)], 12)

# ImageDownloader().download_images([Tile3587(1, 2, 5)], 1, 0)
