import os
from secrets import randbelow
from threading import Thread
import tiler
import subprocess
from os import pipe

def make_uuid():
  ret = [""] * 32
  for i in range(32):
    ret[i] = hex(randbelow(16))[2:]
  return "".join(ret)

class Job:
  def __init__(self, callback) -> None:
    self.uuid = make_uuid()
    self.callback = callback
    
  def done(self):
    self.callback(self)
    
  def __eq__(self, __value) -> bool:
    return __value.uuid == self.uuid;

  def __hash__(self) -> int:
    return hash(self.uuid)
  
class DownloadImagesJob(Job):
  def __init__(self, callback, tile: tiler.Tile, zl, path) -> None:
    super().__init__(callback)
    self.tile = tile
    self.zl = zl
    self.path = path;
    self.status = 0;
  
  def task(self):
    t = self.tile
    dl, reqd = tiler.make_downloader(self.tile, self.zl)
    self.dl = dl
    dl.download_images(reqd)
    self.status = 1
    if not os.path.exists("cache"):
      os.mkdir("cache")
    if not os.path.exists("cache/tileimg"):
      os.mkdir("cache/tileimg")
    subprocess.run(["sticher/build/main", str(t.lat), str(t.lon), str(self.zl)])
    self.done()
    
  def progress(self):
    if self.status == 0:
      cur, total = self.dl.get_progress()
      return f"Downloading images for tile {self.tile.lat}, {self.tile.lon} at zoom level {self.zl} ({cur}/{total})..."
    else:
      return f"Stiching tile image {self.tile.lat}, {self.tile.lon} at zoom level {self.zl}..."
  
  def perform(self):
    t = Thread(target = self.task)
    t.start()
