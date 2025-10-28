# Python 3 server example
import logging
import re
from server.navdata.loader import NavDatabase
import server.navdata.builder as builder
from server.server import *

logger = logging.getLogger("cifp-viewer")
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
  print("Could not open config file.")
  exit(1)

navdata_dir = cfg["data_dir"]
if navdata_dir.endswith("/"): navdata_dir = navdata_dir[:-1]
logger.info("Loading navdata from " + navdata_dir + ".")
data = NavDatabase(navdata_dir)
logger.info("Navdata loaded.")


DEBUG = True
if not DEBUG:
  webServer = HTTPServer((hostName, serverPort), CIFPServer)
  logger.info("Server started http://%s:%s" % (hostName, serverPort))

  try:
    webServer.serve_forever()
  except KeyboardInterrupt:
    pass

  webServer.server_close()
  logger.info("Server stopped.")
else:
  dir = "/home/mark/gamedrive/xplane-12/Custom Data/"
  res = data.get_airport_data("VHHH")
  #for a in os.listdir(dir + "/CIFP"):
  #  data.get_airport_data(a[:-4])
  if res:
    sids, stars, appches = res
    builder.build_2d(appches["I07C"].legs)
