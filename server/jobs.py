import os
from secrets import randbelow
from threading import Thread

import requests
import server.tiler as tiler
import subprocess
from os import pipe
from server.downloaders import *
import zipfile
from threading import Lock

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

class CreateImageJobNew(Job):
  def __init__(self, callback, tile: tiler.Tile, zl: int, path: str) -> None:
    super().__init__(callback)
    self.tile = tile
    self.zl = zl
    self.path = path;
    self.status = 0;
  
  def copy_default(self):
    shutil.copyfile("assets/white.jpg", self.path)
  
  dl_progress = 0
  prog_lock = Lock()
  
  def task(self):
    x1 = self.tile.lon
    y1 = self.tile.lat
    x2 = x1 + 1
    y2 = y1 + 1
    height = min(4096, 1 << (self.zl - 1))
    width = int(height * cos(self.tile.lat * pi / 180))
    
    url = f"https://tiles.maps.eox.at/wms?service=wms&request=getmap&layers=s2cloudless-2024&srs=EPSG:4326&bbox={x1},{y1},{x2},{y2}&width={width}&height={height}&format=image/jpeg"
    print(url)
    r = requests.get(url, stream=True)
    contenttype = r.headers.get("content-type")
    print(contenttype)
    if contenttype is None or contenttype != "image/jpeg":
      logger.warn(f"Did not get the expected image type when downloading tile {self.tile}. Replacing with a white image.")
      self.copy_default()
    elif r.status_code != 200 and r.status_code != 304:
      logger.warn(f"Error {r.status_code} when downloading {self.tile}. Replacing with a white image.")
      self.copy_default()
    else:
      with open(self.path, "wb") as f:
        if 'content-length' in r.headers:
          total_length = int(r.headers.get('content-length'))
        else:
          total_length = None
        
        try:
          recv = 0
          for data in r.iter_content(chunk_size=4096):
            recv += len(data)
            f.write(data)
            if total_length:
              with self.prog_lock:
                self.dl_progress = recv / total_length
        except requests.exceptions.ChunkedEncodingError:
          logger.error("Connection error when downloading {self.tile}.")
          self.done()
          
    self.done()
    
  def progress(self):
    with self.prog_lock:
      prog = int(self.dl_progress * 100)
    return f"Downloading images for tile {self.tile.lat}, {self.tile.lon} at zoom level {self.zl}... ({prog}%)"
  
  def perform(self):
    t = Thread(target = self.task)
    t.start()

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
