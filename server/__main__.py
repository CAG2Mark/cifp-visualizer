# Python 3 server example
import logging
import re
from server.navdata.loader import NavDatabase
from server.navdata.builder import build_3d
import server.navdata.point_builder as point_builder
from server.server import *

logger = logging.getLogger("cifp-viewer")
logging.basicConfig(format='[%(asctime)s] %(name)s (%(levelname)s): %(message)s')
logger.setLevel(logging.INFO)

if not os.path.exists("config.txt"):
  shutil.copyfile("sample_config.txt", "config.txt")
  logger.info("Creating config file from the sample config.")

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

hostName = "0.0.0.0"
serverPort = 8080

navdata_dir = cfg["data_dir"]
hostName = cfg["hostname"]
serverPort = int(cfg["port"])

set_config(cfg)
if navdata_dir.endswith("/"): navdata_dir = navdata_dir[:-1]
logger.info("Loading navdata from " + navdata_dir + ".")
navdata = NavDatabase(navdata_dir)
set_navdata(navdata)
logger.info("Navdata loaded.")

def start_server():
  webServer = HTTPServer((hostName, serverPort), CIFPServer)
  logger.info("Server started http://%s:%s" % (hostName, serverPort))

  try:
    webServer.serve_forever()
  except KeyboardInterrupt:
    pass

  webServer.server_close()
  logger.info("Server stopped.")

DEBUG = False
if not DEBUG:
  start_server()
else:
  # Code for debugging
  pass
