from dataclasses import dataclass
from http.client import HTTPResponse
from math import *
from threading import Thread, Lock
from urllib.error import URLError
from urllib.request import urlopen
import os
import logging

logger = logging.getLogger("cifp-viewer")

@dataclass
class Tile:
  lat: int
  lon: int
  
@dataclass
class Tile3587:
  x: int
  y: int
  zoom: int

class ThreadedDownloader:
  def __init__(self, queue_size: int, content_type: str) -> None:
    self.fail_reasons = []
    self.queue_size = queue_size
    self.content_type = content_type
  
  fail_lock = Lock()
  queue_lock = Lock()
  
  def get_progress(self):
    with self.queue_lock:
      return len(self.urls, self.download_size)
  
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
        
        with self.fail_lock:
          if contenttype is None or contenttype != self.content_type:
            return (2, f"Request to `{url}` did not return an image")
          if response.status != 200 and response.status != "304":
            return (2, f"Error {response.status} for request `{url}`: {response.reason}")

        with open(file, "wb") as f:
          f.write(body)
        
    except URLError as e:
      with self.fail_lock:
        return (2, str(e))
    
    return (0, "")
      
  def download(self, urls: list[str, str, str]):
    while True:
      with self.queue_lock:
        if len(urls) == 0: return
        url, name, file = urls.pop()
      logger.info(f"Downloading {name}...")
      res, reason = self.download_url((url, file))
      if res == 0:
        logger.info(f"{name} downloaded.")
      elif res == 1:
        logger.info(f"{name} exists in the cache. Skipping.")
      elif res == 2:
        logger.info(f"Failed to download {name} from {url}: {reason}")

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
    ThreadedDownloader.__init__(self, queue_size, "image/jpeg")
    self.fail_reasons = []

  def download_images(self, tiles: list[Tile3587]):
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
