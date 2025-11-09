# Python 3 server example
import logging
import re
from server.navdata.defns import AircraftConfig
from server.navdata.loader import NavDatabase
from server.navdata.builder import build_3d
import server.navdata.point_builder as point_builder
from server.navdata.mathhelpers import solve_matrix
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
  logger.error("Could not open config file.")
  exit(1)

navdata_dir = cfg["data_dir"]
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
  ac_cfg = AircraftConfig(1, 0.1, tan(3 * pi / 180))
  # airport_, sid = ("VHHH", "PECA2E")
  # airport_, sid = ("LPMA", "DEMZ1Z")
  # airport_, sid = ("LPMA", "DEMZ1Y")
  # airport_, sid = ("LPMA", "MARC1W")
  # airport_, sid = ("LPMA", "NIDU1E")
  # airport_, sid = ("LGSK", "IBID1B")
  # airport_, sid = ("LGSK", "EVIK1B")
  # airport_, sid = ("EKVG", "ODEV2W")
  # airport_, sid = ("NZWD", "BLANE2") # TODO
  # airport, appch_nme, trans_nme = ("VHHH", "I07L", "LIMES")
  # airport, appch_nme, trans_nme = ("EGPB", "D27", "SUM2")
  # airport, appch_nme, trans_nme = ("EGPB", "D27", "SUM3")
  # airport, appch_nme, trans_nme = ("EGPB", "D27", "D063L")
  # airport, appch_nme, trans_nme = ("EGPB", "D27", "D355L")
  # airport, appch_nme, trans_nme = ("LGSK", "Q01", "SKP")
  # airport, appch_nme, trans_nme = ("VNKT", "R20", "IGRIS")
  # airport, appch_nme, trans_nme = ("VNKT", "R20", "DANFE")
  # airport, appch_nme, trans_nme = ("VQPR", "R33-X", "PR888")
  # airport, appch_nme, trans_nme = ("BGBW", "N06-X", "NA")
  # airport, appch_nme, trans_nme = ("BGBW", "Q06-Y", "D078D")
  # airport, appch_nme, trans_nme = ("RCQC", "I02", "MASON")
  # airport, appch_nme, trans_nme = ("EKVG", "I30-Z", "MY1")
  # airport, appch_nme, trans_nme = ("ENSB", "L27", "ADV1")
  # airport, appch_nme, trans_nme = ("NZFX", "T15T", "FAVGU") # TODO
  # airport, appch_nme, trans_nme = ("NZQN", "R23-Y", "ATKIL")
  airport, appch_nme, trans_nme = ("SPZO", "R28", "SDARK")
  
  SID = False
  
  dir = "/home/mark/gamedrive/xplane-12/Custom Data/"
  #starts = set()
  res = navdata.get_airport_data(airport_) if SID else navdata.get_airport_data(airport)
  #for a in os.listdir(dir + "/CIFP"):
  #  res = data.get_airport_data(a[:-4])
  #  if res:
  #    _, _, _, s = res
  #    for e in s: starts.add(e)
  #print(starts)

  if SID and res:
    sids, stars, appches = res
    sid = sids[sid]
    legs = sid.legs
    
    rwy = sid.rwys[0]
    print(sid.rwys)
    start = data.get_runway_waypoint(airport_, "RW" + rwy, True)
    
    # leg_points, all_points = point_builder.build_points(legs, ac_cfg, start.to_rad(), -1, 28, True)
    
    def plot_points():
      import pylab as pl
      for (_, points) in leg_points:
        for p in points:
          # print(p.lat * 180 / pi, p.lon * 180 / pi)
          pl.plot(p.lon * 180 / pi, p.lat * 180 / pi, "bo")
      pl.show()
        
    #plot_points()
    #print()
    #for (_, points) in leg_points:
    #  for p in points: pass
        # print(p.altitude)
    
    exit()
  if not SID and res:
    sids, stars, appches = res
    appch = appches[appch_nme]
    trans = list(filter(lambda x: x[0] == trans_nme, appch.transitions))[0]
    legs = trans[1] + appch.legs

    map_legs = None
    for i, leg in enumerate(legs):
      if leg.info.fmap:
        map_legs = legs[i:]
        legs = legs[:i]
        break
    
    assert not map_legs is None
    
    leg_points, all_points = point_builder.build_points(legs, ac_cfg, None, -1, 11000, False)
    
    def plot_points():
      import pylab as pl
      for (_, points) in leg_points:
        for p in points:
          print(p.lat * 180 / pi, p.lon * 180 / pi)
          pl.plot(p.lon * 180 / pi, p.lat * 180 / pi, "bo")
      pl.show()
        
    plot_points()
    print()
    for (_, points) in leg_points:
      for p in points:
        print(p.altitude)
    exit()
    
    tro10 = point_builder.PathPoint(69.8691 * pi / 180, 18.9680 * pi / 180, 348 * pi / 180, -1)
    baxas_wpt = data.get_waypoint("BAXAS", "EN")
    kv_wpt = data.get_waypoint("KV", "EN")
    tro_wpt = data.get_waypoint("TRO", "EN")
    baxas = (baxas_wpt.lat * pi / 180, baxas_wpt.lon * pi / 180)
    kv = kv_wpt.to_rad()
    tro = tro_wpt.to_rad()
    
    print("DME test")
    ans = point_builder.go_to_dme(kv, 348.2 * pi / 180, tro, 0, 0)
    print(ans[0] * 180 / pi, ans[1] * 180 / pi)
    print("----------")
    
    #res = builder.turn_to_course_towards(tro10, 348.2 * pi / 180, baxas, 194.2 * pi / 180, 1, 5, True)
    #for r in res:
    #  print(r.lat * 180 / pi, r.lon * 180 / pi)
    
    points, all_points = point_builder.build_points(legs, -1, 4000, False)
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
    
    res = point_builder.turn_from(
      point_builder.PathPoint(0, 0, pi/2, 0),
      pi / 2,
      45 * pi / 180,
      100,
      6, True
    )
    
    for p in res:
      p.print_deg()
    
    exit()
    res = point_builder.get_arc_between_points(
      (center.lat * pi / 180, center.lon * pi / 180),
      (start.lat * pi / 180, start.lon * pi / 180),
      (end.lat * pi / 180, end.lon * pi / 180), 2, True
    )
    print(res[0][1])
    print(res[1])
    