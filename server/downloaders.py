from dataclasses import dataclass
from http.client import HTTPResponse
from math import *
from threading import Thread, Lock
from urllib.error import URLError
from urllib.request import urlopen
import os
import logging
import shutil

logger = logging.getLogger("cifp-viewer")

@dataclass(frozen=True)
class Tile:
  lat: int
  lon: int
  
@dataclass
class Tile3587:
  x: int
  y: int
  zoom: int

class ThreadedDownloader:
  def __init__(self, queue_size: int, content_type: str, default, do_log = True) -> None:
    self.fail_reasons = []
    self.queue_size = queue_size
    self.content_type = content_type
    self.do_log = do_log
    self.default = default
    
    self.download_size = 0
    self.urls = []
    
  def log_info(self, msg):
    if self.do_log: logger.info(msg)

  queue_lock = Lock()
  
  def get_progress(self):
    with self.queue_lock:
      return self.download_size - len(self.urls), self.download_size
  
  # 0 = downloaded
  # 1 = cache hit
  # 2 = failure, reason
  def download_url(self, urlfile: tuple[str, str]) -> tuple[int, str]:
    url, file = urlfile
    
    if os.path.exists(file):
      return (1, "")
    
    try:
      with urlopen(url) as response:
        response: HTTPResponse = response
        body = response.read()
        contenttype = response.getheader("content-type")
        
        if contenttype is None or contenttype != self.content_type:
          self.default(url, file)
          return (2, f"Request to `{url}` did not return the expected content type of {self.content_type}.")
        if response.status != 200 and response.status != "304":
          self.default(url, file)
          return (2, f"Error {response.status} for request `{url}`: {response.reason}")

        with open(file, "wb") as f:
          f.write(body)
        
    except URLError as e:
      self.default(url, file)
      return (2, str(e))
    
    return (0, "")
      
  def download(self, urls: list[str, str, str]):
    while True:
      with self.queue_lock:
        if len(urls) == 0: return
        url, name, file = urls.pop()
      self.log_info(f"Downloading {name}...")
      res, reason = self.download_url((url, file))
      if res == 0:
        self.log_info(f"{name} downloaded.")
      elif res == 1:
        self.log_info(f"{name} exists in the cache. Skipping.")
      elif res == 2:
        self.log_info(f"Failed to download {name} from {url}: {reason}")

  # urls: url, nickname, file
  def download_urls(self, urls: list[str, str, str]):
    self.fail_reasons = []
    
    threads = []
    urls = urls.copy()
    
    self.urls = urls
    self.download_size = len(urls)
    
    for _ in range(self.queue_size):
      thread = Thread(target=self.download, args=(urls,))
      thread.start()
      threads.append(thread)
      
      if len(urls) == 0: break
      
    for t in threads: t.join()

class EoxDownloader(ThreadedDownloader):
  def __init__(self, queue_size: int) -> None:
    ThreadedDownloader.__init__(self, queue_size, "image/jpeg", self.default_file)
    self.fail_reasons = []
    
  def default_file(self, url, file):
    shutil.copyfile("assets/white.jpg", file)

  def download_images(self, tiles: list[Tile3587]):
    if not os.path.exists("cache"):
      os.mkdir("cache")
    if not os.path.exists("cache/images"):
      os.mkdir("cache/images")
    if not os.path.exists("cache/dem"):
      os.mkdir("cache/dem")
      
    # https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml
    urls = [
      (
        f"http://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/GoogleMapsCompatible/{tile.zoom}/{tile.y}/{tile.x}.jpg",
        str(tile),
        f"cache/images/Z{tile.zoom}-{tile.x}-{tile.y}.jpg"
      )
      for tile in tiles
    ]
    
    self.download_urls(urls)
