import os
from secrets import randbelow
from threading import Thread
import server.tiler as tiler
import subprocess
from os import pipe
from server.downloaders import *
import zipfile

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
  
class CreateImageJob(Job):
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

class DownloadDemJob(Job):
  def __init__(self, callback, tile: tiler.Tile, path) -> None:
    super().__init__(callback)
    self.tile = tile
    self.webpath = tiler.get_vfp_file(tile)
    self.path = path
  
  def task(self):
    t = self.tile
    
    if not os.path.exists("cache"):
      os.mkdir("cache")
    if not os.path.exists("cache/demzip"):
      os.mkdir("cache/demzip")
    
    dl = VFPDownloader(1)
    # download
    self.dl = dl
    dl.download_file(self.webpath)
    
    self.done()
  
  def progress(self):
    return f"Downloading DEM for tile {self.tile.lat}, {self.tile.lon}..."
  
  def perform(self):
    t = Thread(target = self.task)
    t.start()

class MakeMeshJob(Job):
  def __init__(self, callback, tile: tiler.Tile, lod, path) -> None:
    super().__init__(callback)
    self.tile = tile
    self.lod = lod
    self.filename = tiler.get_vfp_file(tile).split("/")[-1] # zip file name
    self.path = path # .obj.gz name
    self.status = 0
  
  def task(self):
    t = self.tile
    
    # extract zip
    if not os.path.exists("cache"):
      os.mkdir("cache")
    if not os.path.exists("cache/dem"):
      os.mkdir("cache/dem")
    if not os.path.exists("cache/tilemesh"):
      os.mkdir("cache/tilemesh")
      
    success = False
    with zipfile.ZipFile(f"cache/demzip/{self.filename}.zip") as f:
      for file in f.namelist():
        if not file.endswith(".hgt"): continue
        nme = file.split("/")[-1]
        lat_s = -1 if nme[0].upper() == "S" else 1
        lat = lat_s * int(nme[1:3])
        lon_s = -1 if nme[3].upper() == "W" else 1
        lon = lon_s * int(nme[4:7])
        
        if lat == t.lat and lon == t.lon:
          success = True
          with f.open(file, mode='r') as r, open(f"cache/dem/{nme}", 'bw') as w:
            w.write(r.read())
          break
      
      if not success:
        pass # TODO
      
    self.status = 1
    
    subprocess.run(["mesh-builder/build/main", str(t.lat), str(t.lon)])
    
    self.done()
    
  def progress(self):
    if self.status == 0:
      return f"Extracting DEM for tile {self.tile.lat}, {self.tile.lon}..."
    elif self.status == 1:
      return f"Making mesh for tile {self.tile.lat}, {self.tile.lon} at LOD {self.lod}..."
  
  def perform(self):
    t = Thread(target = self.task)
    t.start()
