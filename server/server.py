# Python 3 server example
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import os
from secrets import randbelow
import tiler
from threading import Lock
from jobs import *

hostName = "localhost"
serverPort = 8080

logger = logging.getLogger("cifp-viewer")
  
def validate_tile(lat, lon):
  return (-85 <= lat < 85) and (-180 <= lon < 180)

def get_file_bytes(filename):
  if os.path.exists(filename):
    with open(filename, "br") as f:
      return f.read()

class CIFPServer(BaseHTTPRequestHandler):
  
  img_jobs_lock = Lock()
  img_jobs: dict[str, Job] = {}
  
  
  def send_malformed(self, msg = None):
    self.send_response(400)
    if msg:
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes(msg + "\n", "UTF-8"))
    else:
      self.end_headers()
      
  def img_job_done(self, job: Job):
    with self.img_jobs_lock:
      if job.path in self.img_jobs:
       del self.img_jobs[job.path]
  
  def do_GET(self):
    values = self.path.split("/")[1:]
    
    if ".." in values:
      self.send_malformed()
      return

    if len(values) == 0 or not values[0] or values[0] == "index.html":
      self.send_response(301)
      self.send_header('Location','viewer/index.html')
      self.end_headers()
      return
    
    head = values[0]
    values = values[1:]
    
    if head == "viewer":
      if len(values) > 0:
        path = "viewer/" + "/".join(values)
        print(path)
        if os.path.exists(path):
          if values[-1].endswith(".html"):
            ct = "text/html"
          elif values[-1].endswith(".css"):
            ct = "text/css"
          elif values[-1].endswith(".js"):
            ct = "text/javascript"
          else:
            self.send_response(404)
            self.end_headers()
            return
              
          with open(path) as f:
            content = bytes(f.read(), encoding="UTF-8")
          print(path)
          self.send_response(200)
          self.send_header("Content-type", ct)
          self.end_headers()
          self.wfile.write(content)
    elif head == "photo":
      if len(values) != 3 or not values[-1].endswith(".jpg"):
        self.send_malformed("Incorrect format. Expected: photo/lat/lon/zl.jpg")
        return
      lat, lon, zl = values
      zl = zl[:-4]
      try:
        lat = int(lat)
        lon = int(lon)
        zl = int(zl)
      except:
        self.send_malformed("Incorrect format. Expected: photo/lat/lon/zl.jpg")
        return
      if not validate_tile(lat, lon):
        self.send_malformed("Latitude and longitude out of range.")
        return
      if not 10 <= zl <= 19:
        self.send_malformed("Zoom level must be between 10 and 19.")
        return
      
      # NOTE: we MUST check if the job exists first
      # the file could exist but the job could still be running!
      
      path = f"cache/tileimg/Z{zl}-{lat}-{lon}.jpg"
      with self.img_jobs_lock:
        working = path in self.img_jobs
        if working: cur_job = self.img_jobs[path]
      
      if working:
        self.send_response(202)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes(cur_job.progress(), "UTF-8"))
      elif not os.path.exists(path):
        logger.info(f"Dispatching job to create image {lat}/{lon}/{zl}.jpg.")
        # create job
        job = DownloadImagesJob(self.img_job_done, tiler.Tile(lat, lon), zl, path)
        self.img_jobs[path] = job
        job.perform()
        
        self.send_response(202)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("Initializing...", "UTF-8"))
      else:
        content = get_file_bytes(path)
        self.send_response(200)
        self.send_header("Content-type", "image/jpeg")
        self.end_headers()
        self.wfile.write(content)
  
    else:
       self.send_response(404)
       self.end_headers()

if __name__ == "__main__":        
  logging.basicConfig(format='[%(asctime)s] %(name)s (%(levelname)s): %(message)s')
  logger.setLevel(logging.INFO)


  webServer = HTTPServer((hostName, serverPort), CIFPServer)
  logger.info("Server started http://%s:%s" % (hostName, serverPort))

  try:
    webServer.serve_forever()
  except KeyboardInterrupt:
    pass

  webServer.server_close()
  logger.info("Server stopped.")
