from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import os
from secrets import randbelow
from threading import Lock
from server.jobs import *
import re
from server.navdata.defns import AircraftConfig
from server.navdata.loader import NavDatabase
import server.navdata.builder as builder
import json

hostName = "0.0.0.0"
serverPort = 8080

logger = logging.getLogger("cifp-viewer")

navdata: NavDatabase

def get_navdata(): return navdata

def set_navdata(data: NavDatabase):
  global navdata
  navdata = data
  
def validate_tile(lat: int, lon: int):
  return (-85 <= lat < 85) and (-180 <= lon < 180)

def get_file_bytes(filename: str):
  if os.path.exists(filename):
    with open(filename, "br") as f:
      return f.read()

class CIFPServer(BaseHTTPRequestHandler):
  
  img_jobs_lock = Lock()
  img_jobs: dict[str, Job] = {}

  zip_jobs_lock = Lock()
  zip_jobs: dict[str, Job] = {}

  terr_jobs_lock = Lock()
  terr_jobs: dict[str, Job] = {}
  
  
  def send_malformed(self, msg: str | None = None):
    self.send_response(400)
    if msg:
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes(msg + "\n", "UTF-8"))
    else:
      self.end_headers()
  
  def send_404(self):
    self.send_response(404)
    self.end_headers()
      
  def img_job_done(self, job: Job):
    with self.img_jobs_lock:
      if job.path in self.img_jobs:
       del self.img_jobs[job.path]
       
  def zip_job_done(self, job: Job):
    with self.zip_jobs_lock:
      if job.path in self.zip_jobs:
       del self.zip_jobs[job.path]

  def terr_job_done(self, job: Job):
    with self.terr_jobs_lock:
      if job.path in self.terr_jobs:
       del self.terr_jobs[job.path]
  
  def handle_viewer(self, values: list[str]):
    if len(values) == 0 or (len(values) == 1 and not values[-1]):
      self.redirect_to_index(True)
      return

    path = "viewer/" + "/".join(values)
    if os.path.exists(path):
      if values[-1].endswith(".html"):
        ct = "text/html"
      elif values[-1].endswith(".css"):
        ct = "text/css"
      elif values[-1].endswith(".js"):
        ct = "text/javascript"
      elif values[-1].endswith(".mtl"):
        ct = "model/mtl"
      elif values[-1].endswith(".obj"):
        ct = "model/obj"
      else:
        self.send_404()
        return
          
      with open(path) as f:
        content = bytes(f.read(), encoding="UTF-8")
      self.send_response(200)
      self.send_header("Content-type", ct)
      self.end_headers()
      self.wfile.write(content)
    else:
      self.send_404()
      return
  
  def handle_photos(self, values: list[str]):
    if len(values) != 3 or not values[-1].endswith(".png"):
      self.send_malformed("Incorrect format. Expected: photo/lat/lon/zl.png")
      return
    lat, lon, zl = values
    zl = zl[:-4]
    try:
      lat = int(lat)
      lon = int(lon)
      zl = int(zl)
    except:
      self.send_malformed("Incorrect format. Expected: photo/lat/lon/zl.png")
      return
    if not validate_tile(lat, lon):
      self.send_malformed("Latitude and longitude out of range.")
      return
    if not 10 <= zl <= 19:
      self.send_malformed("Zoom level must be between 10 and 19.")
      return
    
    # NOTE: we MUST check if the job exists first
    # the file could exist but the job could still be running!
    
    path = f"cache/tileimg/Z{zl}-{lat}-{lon}.png"
    with self.img_jobs_lock:
      working = path in self.img_jobs
      if working: cur_job = self.img_jobs[path]
    
    if working:
      self.send_response(202)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes(cur_job.progress(), "UTF-8"))
    elif not os.path.exists(path):
      logger.info(f"Dispatching job to create image {lat}/{lon}/{zl}.png.")
      # create job
      job = CreateImageJobNew(self.img_job_done, tiler.Tile(lat, lon), zl, path)
      self.img_jobs[path] = job
      job.perform()
      
      self.send_response(202)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes("Initializing...", "UTF-8"))
    else:
      content = get_file_bytes(path)
      self.send_response(200)
      self.send_header("Content-type", "image/png")
      self.end_headers()
      self.wfile.write(content)
  
  def handle_terrain(self, values: list[str]):
    if len(values) != 3 or not values[-1].endswith(".obj"):
      self.send_malformed("Incorrect format. Expected: terain/lat/lon/lod.obj")
      return
    lat, lon, lod = values
    lod = lod[:-4]
    try:
      lat = int(lat)
      lon = int(lon)
      lod = int(lod)
    except:
      self.send_malformed("Incorrect format. Expected: terain/lat/lon/lod.zip")
      return
    if not validate_tile(lat, lon):
      self.send_malformed("Latitude and longitude out of range.")
      return
    if not 0 <= lod <= 1:
      self.send_malformed("LOD must be between 0 and 1.")
      return
    
    # NOTE: we MUST check if the job exists first
    # the file could exist but the job could still be running!
    
    # 1. download zip job
    tile = tiler.Tile(lat, lon)
    filename = tiler.get_vfp_file(tile).split("/")[-1]
    path = f"cache/demzip/{filename}.zip"
    with self.zip_jobs_lock:
      working = path in self.zip_jobs
      if working: cur_job = self.zip_jobs[path]
    
    if working:
      self.send_response(202)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes(cur_job.progress(), "UTF-8"))
      return
    elif not os.path.exists(path):
      logger.info(f"Dispatching job to download {path}.zip")
      # create job
      job = DownloadDemJob(self.zip_job_done, tiler.Tile(lat, lon), path)
      self.zip_jobs[path] = job
      job.perform()
      
      self.send_response(202)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes("Initializing...", "UTF-8"))
      return
    
    # 2. create mesh
    path = f"cache/tilemesh/DEM_{lat}_{lon}.obj"
    with self.terr_jobs_lock:
      working = path in self.terr_jobs
      if working: cur_job = self.terr_jobs[path]
    
    if working:
      self.send_response(202)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes(cur_job.progress(), "UTF-8"))
      return
    elif not os.path.exists(path):
      logger.info(f"Dispatching job to create {path}.obj")
      # create job
      job = MakeMeshJob(self.terr_job_done, tiler.Tile(lat, lon), lod,  path)
      self.terr_jobs[path] = job
      job.perform()
      
      self.send_response(202)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(bytes(job.progress(), "UTF-8"))
      return
    else:
      content = get_file_bytes(path)
      self.send_response(200)
      self.send_header("Content-type", "model/obj")
      # self.send_header("Content-Encoding", "gzip")
      self.end_headers()
      self.wfile.write(content)
  
  def handle_airport(self, values: list[str]):
    global navdata
    
    if len(values) != 1:
      self.send_malformed("Usage: airport/ICAO")
      return
    data = navdata.get_airport_data(values[0])
    if data is None:
      self.send_404()
      return
    
    sids, stars, appches = data
    
    ret = {}
    sids_dict = {}
    stars_dict = {}
    appches_dict = {}
    
    ret["sids"] = sids_dict
    for ident, sid in sids.items():
      data = {}
      data["id"] = ident
      data["runways"] = sid.rwys
      data["transitions"] = [x[0] for x in sid.transitions]
      sids_dict[ident] = data
    
    ret["stars"] = stars_dict
    for ident, star in stars.items():
      data = {}
      data["id"] = ident
      data["runways"] = star.rwys
      data["transitions"] = [x[0] for x in star.transitions]
      stars_dict[ident] = data
    
    ret["approaches"] = appches_dict
    for ident, appch in appches.items():
      data = {}
      data["id"] = ident
      data["runway"] = appch.rwy
      data["transitions"] = [x[0] for x in appch.transitions]
      appches_dict[ident] = data
    
    payload = json.dumps(ret)
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(bytes(payload, "UTF-8"))
  
  # proc sig -> altitude
  proc_cache_info: dict[str, int] = {}
  proc_cache_lock = Lock()
  
  def handle_proc(self, values: list[str]):
    if len(values) != 4 and len(values) != 6:
      return self.send_malformed(
        "Usage: proc/ICAO/<sid,star,approach>/ident/<transition,\"none\"> or proc/ICAO/<sid,star,approach>/ident/<transition,\"none\">/<runway,\"none\">/legId.obj")
    
    if len(values) == 4:
      airport_nme, proc_type, ident, transition = values
      runway = None
      seq = None
    else:
      airport_nme, proc_type, ident, transition, runway, seq = values
    
    airport = navdata.get_airport_data(airport_nme)
    if airport is None:
      self.send_404()
      return
    
    sids, stars, appches = airport
    
    if not proc_type in ["sid", "star", "approach"]:
      self.send_malformed("Procedure type must be sid, star or approach")
      return
    
    if proc_type == "sid": data = sids
    elif proc_type == "star": data = stars
    else: data = appches
    
    if not ident in data:
      self.send_404()
      return
    
    proc = data[ident]

    if seq is None:
      legs = proc.legs
      if transition != "none":
        legs_ = None
        for id, t_legs in proc.transitions:
          if id == transition:
            legs_ = t_legs
            break
        if legs_ is None:
          self.send_404()
          return
        
        if proc_type == "sid":
          legs = legs + legs_
        else:
          legs = legs_ + legs
      ret = []
      for l in legs:
        data = {}
        data["kind"] = l.human_name()
        data["fix"] = l.fix_name()
        data["legId"] = l.info.qual + str(l.info.seq)
        alt_restr = l.info.alt.pretty_print() if l.info.alt else None
        if alt_restr:
          data["altitude"] = alt_restr
        spd_restr = l.info.speed.pretty_print() if l.info.speed else None
        if spd_restr:
          data["speed"] = spd_restr
        ret.append(data)
      payload = json.dumps(ret)
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(bytes(payload, "UTF-8"))
      
    else:
      with self.proc_cache_lock:
        # build the data
        assert runway
        
        if runway == "none": runway = None
        if transition == "none": transition = None
        
        proc_sig = builder.make_proc_sig(airport_nme, ident, runway, transition)
          
        altitude = 10000 # todo
        
        filepath = f"cache/flightpaths/{proc_sig}_{seq}"
        
        def serve_file():
          content = get_file_bytes(filepath)
          self.send_response(200)
          self.send_header("Content-type", "model/obj")
          # self.send_header("Content-Encoding", "gzip")
          self.end_headers()
          self.wfile.write(content)
          return
        
        if proc_sig in self.proc_cache_info \
            and self.proc_cache_info[proc_sig] == altitude \
            and os.path.exists(filepath):
          serve_file()
          return
        
        try:
          objs = builder.build_proc(proc, AircraftConfig(), runway, transition, altitude)
        except ValueError as e:
          self.send_malformed(e.args[0])
          return
        except KeyError as e:
          self.send_404()
          return
        
        if not os.path.exists("cache"):
          os.mkdir("cache")
        if not os.path.exists("cache/flightpaths"):
          os.mkdir("flightpaths")
        for l, obj in objs:
          filename = f"cache/flightpaths/{proc_sig}_{l.info.qual}{l.info.seq}.obj"
          obj.export_obj(filename)
        
        self.proc_cache_info[proc_sig] = altitude
      
        serve_file()
      
  def redirect_to_index(self, from_viewer: bool = False):
    self.send_response(301)
    if from_viewer:
      self.send_header('Location','index.html')
    else:
      self.send_header('Location','viewer/index.html')
    self.end_headers()
  
  def log_message(self, format, *args):
    return
  
  def do_GET(self):
    values = self.path.split("/")[1:]
    
    if ".." in values:
      self.send_malformed()
      return

    if len(values) == 0 or not values[0] or values[0] == "index.html":
      self.redirect_to_index()
      return
    
    head = values[0]
    values = values[1:]
    
    if head == "viewer":
      self.handle_viewer(values)
    elif head == "photo":
      self.handle_photos(values)
    elif head == "terrain":
      self.handle_terrain(values)
    elif head == "airport":
      self.handle_airport(values)
    elif head == "proc":
      self.handle_proc(values)
    else:
       self.send_404()

if __name__ == "__main__":
  logging.basicConfig(format='[%(asctime)s] %(name)s (%(levelname)s): %(message)s')
  logger.setLevel(logging.INFO)

  # load config
  try:
    with open("config.txt") as f:
      data = f.read()
      data = re.sub(r"#[^\n]*\n", "\n", data)
      cfg: dict[str, str] = {}
      for ln in data.split("\n"):
        if not ln: continue
        key, val = ln.split("=")
        cfg[key.strip()] = val.strip()
  except OSError:
    logger.error("Could not open config file.")
    exit(1)
  
  navdata_dir = cfg["data_dir"]
  if navdata_dir.endswith("/"): navdata_dir = navdata_dir[:-1]
  logger.info("Loading navdata from " + navdata_dir + ".")
  navdata = NavDatabase(navdata_dir)
  logger.info("Navdata loaded.")

  webServer = HTTPServer((hostName, serverPort), CIFPServer)
  logger.info("Server started http://%s:%s" % (hostName, serverPort))

  try:
    webServer.serve_forever()
  except KeyboardInterrupt:
    pass

  webServer.server_close()
  logger.info("Server stopped.")
