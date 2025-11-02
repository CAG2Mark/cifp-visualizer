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
  airport, appch, trans = ("EGPB", "D27", "SUM2")
  # airport, appch, trans = ("EGPB", "D27", "SUM3")
  # airport, appch, trans = ("EGPB", "D27", "D063L")
  # airport, appch, trans = ("EGPB", "D27", "D355L")
  # airport, appch, trans = ("LGSK", "Q01", "SKP")
  # airport, appch, trans = ("VNKT", "R20", "IGRIS")
  # airport, appch, trans = ("VNKT", "R20", "DANFE")
  # airport, appch, trans = ("VQPR", "R33-X", "PR888")
  # airport, appch, trans = ("BGBW", "N06-X", "NA")
  # airport, appch, trans = ("BGBW", "Q06-Y", "D078D")
  # airport, appch, trans = ("RCQC", "I02", "MASON")
  
  dir = "/home/mark/gamedrive/xplane-12/Custom Data/"
  #starts = set()
  res = data.get_airport_data(airport)
  #for a in os.listdir(dir + "/CIFP"):
  #  res = data.get_airport_data(a[:-4])
  #  if res:
  #    _, _, _, s = res
  #    for e in s: starts.add(e)
  #print(starts)
  if res:
    sids, stars, appches = res
    appch = appches[appch]
    trans = list(filter(lambda x: x[0] == trans, appch.transitions))[0]
    legs = trans[1] + appch.legs

    map_legs = None
    for i, leg in enumerate(legs):
      if leg.info.fmap:
        map_legs = legs[i:]
        legs = legs[:i]
        break
    
    assert not map_legs is None
    
    points = builder.build_points(legs, -1, 4000, False)
    
    def plot_points():
      import pylab as pl
      for p in points:
        # print(p.lat * 180 / pi, p.lon * 180 / pi)
        pl.plot(p.lon * 180 / pi, p.lat * 180 / pi, "bo")
      pl.show()
        
    plot_points()
    exit()
    
    tro10 = builder.PathPoint(69.8691 * pi / 180, 18.9680 * pi / 180, 348 * pi / 180, -1)
    baxas_wpt = data.get_waypoint("BAXAS", "EN")
    kv_wpt = data.get_waypoint("KV", "EN")
    tro_wpt = data.get_waypoint("TRO", "EN")
    baxas = (baxas_wpt.lat * pi / 180, baxas_wpt.lon * pi / 180)
    kv = kv_wpt.to_rad()
    tro = tro_wpt.to_rad()
    
    print("DME test")
    ans = builder.go_to_dme(kv, 348.2 * pi / 180, tro, 0, 0)
    print(ans[0] * 180 / pi, ans[1] * 180 / pi)
    print("----------")
    
    #res = builder.turn_to_course_towards(tro10, 348.2 * pi / 180, baxas, 194.2 * pi / 180, 1, 5, True)
    #for r in res:
    #  print(r.lat * 180 / pi, r.lon * 180 / pi)
    
    points = builder.build_points(legs, -1, 4000, False)
    for p in points:
      p.print_deg()
    
    # builder.build_points(map_legs, -1, 73, True)
    
    exit()
    
    center = data.get_waypoint("MAC04", "LP")
    start = data.get_waypoint("MA522", "LP")
    end = data.get_waypoint("MA520", "LP")
    
    print(center)
    print(start)
    print(end)
    
    res = builder.turn_from(
      builder.PathPoint(0, 0, pi/2, 0),
      pi / 2,
      45 * pi / 180,
      100,
      6, True
    )
    
    for p in res:
      p.print_deg()
    
    exit()
    res = builder.get_arc_between_points(
      (center.lat * pi / 180, center.lon * pi / 180),
      (start.lat * pi / 180, start.lon * pi / 180),
      (end.lat * pi / 180, end.lon * pi / 180), 2, True
    )
    print(res[0][1])
    print(res[1])
    