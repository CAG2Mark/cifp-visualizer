from server.navdata.defns import *
from collections import defaultdict
from server.util import querydict
import os

def parse_alt(data: str) -> int:
  if data.startswith("FL"): return int(data[2:]) * 100
  else: return int(data)

def parse_course(crs: str) -> Course:
  truenorth = False
  if crs[-1] == "T":
    truenorth = True
    crs = crs[:-1] 
  return Course(int(crs) / 10, truenorth)
  
  
class NavDatabase:
  
  waypoints: dict[str, dict[str, Waypoint]] = defaultdict(lambda: {})
  runway_waypoints: dict[str, dict[str, Waypoint]] = defaultdict(lambda: {})
  airports: dict[str, AirportInfo] = {}
  
  def __init__(self, dir: str):
    
    self.dir = dir
    
    # load fixes
    with open(dir + "/earth_fix.dat") as f:
      data = f.read().split("\n")[3:]
    for d in data:
      if d == "99": break
      d = d.strip()
      lat, lon, name, _, region = d.split()[:5]
      lat = float(lat)
      lon = float(lon)
      
      if not region in self.waypoints:
        self.waypoints[region] = {}
      
      self.waypoints[region][name] = Waypoint(name, lat, lon, region)
      
    # load other navaids (NBD, VOR, DME)
    with open(dir + "/earth_nav.dat") as f:
      data = f.read().split("\n")[3:]
    for d in data:
      if d == "99": break
      d = d.strip()
      d = d.split()
      
      lat = float(d[1])
      lon = float(d[2])
      name = d[7]
      airport = d[8]
      region = d[9]
      
      if not d[0] in ["2", "3", "4", "5", "12", "13"]: continue
      
      if d[0] == "4":
        self.runway_waypoints[airport][name] = Waypoint(name, lat, lon, region)
      
      self.waypoints[region][name] = Waypoint(name, lat, lon, region)
      
    # load airports
    with open(dir + "/earth_aptmeta.dat") as f:
      data = f.read().split("\n")[3:]
    for d in data:
      if d == "99": break
      d = d.strip()
      d = d.split()
      
      ident, region, lat, lon, elev, _, _, _, ta, tl = d 
      lat = float(lat)
      lon = float(lon)
      elev = int(elev)
      ta = int(ta)
      tl = parse_alt(tl)
      self.airports[ident] = AirportInfo(ident, lat, lon, region, elev, ta, tl)
      
  
  def get_waypoint(self, name: str, region: str) -> Waypoint:
    if not region in self.waypoints:
      raise KeyError("Region `" + region + "` not found.")
    r = self.waypoints[region]
    if not name in r:
      raise KeyError("Waypoint `" + name + "` in region `" + region + "` not found.")
    return self.waypoints[region][name]
    
  def process_alt_desc(self, data: list[str]) -> AltRestr | None:
    kind = data[22]
    alt1 = data[23]
    alt2 = data[24]
    
    if not alt1 and not alt2: return None
    
    alt1 = parse_alt(alt1) if alt1 else -1
    alt2 = parse_alt(alt2) if alt2 else -1
    if not kind:
      return AtAlt(alt1)
    if kind == "+" or kind == "=+":
      assert alt1 != -1
      return AltRange(alt1, None)
    if kind == "-":
      assert alt1 != -1
      return AltRange(None, alt1)
    if kind == "B":
      assert alt1 != -1, alt2 != -1
      return AltRange(alt1, alt2)
    if kind == "C":
      assert alt2 != -1
      return AltRange(None, alt2)
    if kind == "G":
      assert alt1 != -1, alt2 != -1
      return GlideslopeAlt(alt2, alt1, False)
    if kind == "H":
      assert alt1 != -1, alt2 != -1
      return GlideslopeAlt(alt2, alt1, True)
    if kind == "I":
      assert alt1 != -1, alt2 != -1
      return GlideslopeIntc(alt2, alt1, False)
    if kind == "J":
      assert alt1 != -1, alt2 != -1
      return GlideslopeIntc(alt2, alt1, True)
    if kind == "V":
      assert alt1 != -1, alt2 != -1
      return StepDownAboveBelow(alt1, alt2, True)
    if kind == "X":
      assert alt1 != -1, alt2 != -1
      return StepDownAt(alt1, alt2)
    if kind == "Y":
      assert alt1 != -1, alt2 != -1
      return StepDownAboveBelow(alt1, alt2, False)
    
    raise ValueError("Altitude description " + kind + " not recognized.")
    
  def process_speed_desc(self, data: list[str]) -> SpeedRestr | None:
    kind = data[26]
    speed = data[27]
    if not speed: return None
    speed = int(speed) if speed else -1
    if not kind:
      return AtSpeed(speed)
    if kind == "+": return SpeedRange(speed, True)
    if kind == "-": return SpeedRange(speed, False)
    
    raise ValueError("Speed description " + kind + " not recognized.")
  
  def process_waypoint(self, data: list[str], airport: str, start_idx = 4) -> Waypoint:
    """
      4 = normal fix\n
      13 = recommended navaid\n
      30 = center fix or taa proc turn ind
    """
    fix = data[start_idx]
    icao = data[start_idx + 1]
    
    desc = data[8].ljust(4, " ")
    
    if start_idx == 4:
      if desc[0] == "A" or desc[0] == "H":
        # airport or heliport waypoint
        if not fix in self.airports:
          raise KeyError(f"Airport `{fix}` not found." )
        airport = self.airports[fix]
        return Waypoint(airport.icao, airport.lat, airport.lon, airport.region)
      if desc[0] == "G":
        # runway or helipad waypoint
        if fix in self.runway_waypoints[airport]:
          return self.runway_waypoints[airport][fix]
        # just recover by returning the airport coordaintes
        airport = self.airports[airport]
        return Waypoint(airport.icao, airport.lat, airport.lon, airport.region)
    
    return self.get_waypoint(fix, icao)
  
  def process_course(self, data: list[str]) -> Course:
    return parse_course(data[20])
  
  def process_dist(self, data: list[str]) -> float:
    return int(data[21]) / 10
  
  def process_disttime(self, data: list[str]) -> DistOrTime: # minutes
    t = data[21]
    if t[0] == "T":
      return DistOrTime(int(t[1:]) / 10, False)
    else:
      return DistOrTime(int(t) / 10, True)
  
  def process_raddme(self, data: list[str], airport: str, waypoint_idx: int) -> RadialDME:
    """
      4 = normal fix\n
      13 = recommended navaid\n
      30 = center fix or taa proc turn ind
    """
    if not data[waypoint_idx]: return None
    
    waypoint = self.process_waypoint(data, airport, waypoint_idx)
    
    if not data[18] or not data[19]: return None
    
    theta = parse_course(data[18])
    rho = int(data[19]) / 10
    return RadialDME(waypoint, theta, rho)
  
  def process_rad(self, data: list[str], airport: str, waypoint_idx: int) -> Radial:
    """
      4 = normal fix\n
      13 = recommended navaid\n
      30 = center fix or taa proc turn ind
    """
    if not data[waypoint_idx]: return None
    
    waypoint = self.process_waypoint(data, airport, waypoint_idx)
    
    if not data[18]: return None
    
    theta = parse_course(data[18])
    return Radial(waypoint, theta)
  
  def process_line(self, proc_kind: ProcKind, data: list[str], airport: str) -> Leg:
    desc = data[8]
    data = [x.strip() for x in data]
    data[8] = desc # padding is important for this field
    
    seq = int(data[0])
    qual = data[1]
    ident = data[2]
    trans = data[3]
    
    desc = data[8]
    overfly = desc[1] == "Y"
    fmap = desc[2] == "M"
    iaf = desc[3] == "C" or desc[3] == "A" or desc[3] == "D"
    faf = desc[3] == "D" or desc[3] == "I" or desc[3] == "F"
    mapt = desc[3] == "M"
    
    alt = self.process_alt_desc(data)
    speed = self.process_speed_desc(data)
    
    turn_dir = data[9]
    turn_dir = turn_dir == "R" if turn_dir else None
    
    angle = int(data[28]) / 100 if data[28] else None
    
    info = LegInfo(seq, proc_kind, qual, ident, trans, turn_dir, overfly, fmap, mapt, iaf, faf, alt, speed, angle)
    kind = data[11]
    
    if kind == "IF":
      fix = self.process_waypoint(data, airport)
      return InitialFix(info, fix)
    
    if kind == "TF":
      fix = self.process_waypoint(data, airport)
      return TrackToFix(info, fix)
    
    if kind == "CF":
      fix = self.process_waypoint(data, airport)
      course = self.process_course(data)
      rcmd = self.process_raddme(data, airport, 13)
      return CourseToFix(info, fix, course, rcmd)
    
    if kind == "DF":
      fix = self.process_waypoint(data, airport)
      rcmd = self.process_raddme(data, airport, 13)
      return DirectToFix(info, fix, rcmd)
    
    if kind == "FA":
      start = self.process_waypoint(data, airport)
      course = self.process_course(data)
      alt = parse_alt(data[23])
      rcmd = self.process_raddme(data, airport, 13)
      return FixToAltitude(info, start, course, alt, rcmd)
    
    if kind == "FC":
      start = self.process_waypoint(data, airport)
      dist = self.process_dist(data)
      return FixToDistance(info, start, dist)
  
    if kind == "FD":
      start = self.process_waypoint(data, airport)
      to = self.process_waypoint(data, airport, 13)
      dme = self.process_dist(data)
      return FixToDME(info, start, to, dme)

    if kind == "FM":
      start = self.process_waypoint(data, airport)
      course = self.process_course(data)
      rcmd = self.process_raddme(data, airport, 13)
      return FixToManual(info, start, course, rcmd)
    
    if kind == "CA":
      course = self.process_course(data)
      alt = parse_alt(data[23])
      return CourseToAlt(info, course, alt)
    
    if kind == "CD":
      course = self.process_course(data)
      to = self.process_waypoint(data, airport, 13)
      dme = self.process_dist(data)
      return CourseToDME(info, course, to, dme)
    
    if kind == "CI":
      course = self.process_course(data)
      rcmd = self.process_waypoint(data, airport, 13) if data[13] else None
      return CourseToIntercept(info, course, rcmd)

    if kind == "CR":
      course = self.process_course(data)
      radial = self.process_rad(data, airport, 13)
      return CourseToRadial(info, course, radial)
    
    if kind == "RF":
      fix = self.process_waypoint(data, airport)
      center = self.process_waypoint(data, airport, 30)
      dist = self.process_dist(data)
      return RadiusArc(info, fix, center, dist)
    
    if kind == "AF":
      fix = self.process_waypoint(data, airport)
      rcmd = self.process_raddme(data, airport, 13)
      return ArcToFix(info, fix, rcmd)
    
    if kind == "VA":
      heading = self.process_course(data)
      alt = parse_alt(data[23])
      return HeadingToAlt(info, heading, alt)
    
    if kind == "VD":
      heading = self.process_course(data)
      to = self.process_waypoint(data, airport, 13)
      dme = self.process_dist(data)
      return HeadingToDME(info, heading, to, dme)
    
    if kind == "VI":
      heading = self.process_course(data)
      rcmd = self.process_waypoint(data, airport, 13) if data[13] else None
      return HeadingToIntercept(info, heading, rcmd)

    if kind == "VR":
      heading = self.process_course(data)
      radial = self.process_rad(data, airport, 13)
      return HeadingToRadial(info, heading, radial)
    
    if kind == "VM":
      fix = self.process_waypoint(data, airport) if data[4] else None
      heading = self.process_course(data)
      return HeadingToManual(info, fix, heading)
    
    if kind == "PI":
      fix = self.process_waypoint(data, airport)
      alt = parse_alt(data[23])
      course = self.process_course(data)
      max_dist = self.process_dist(data)
      return ProcTurn(info, fix, alt, course, max_dist)
    
    if kind == "HA":
      fix = self.process_waypoint(data, airport)
      alt = parse_alt(data[23])
      course = self.process_course(data)
      disttime = self.process_disttime(data)
      return HoldAlt(info, fix, alt, disttime, course)
    
    if kind == "HF":
      fix = self.process_waypoint(data, airport)
      course = self.process_course(data)
      disttime = self.process_disttime(data)
      return HoldFix(info, fix, disttime, course)
    
    if kind == "HM":
      fix = self.process_waypoint(data, airport)
      course = self.process_course(data)
      disttime = self.process_disttime(data)
      return HoldToManual(info, fix, disttime, course)
    
    raise ValueError("Leg type " + kind + " not recognized.")
    
  def get_airport_data(self, airport: str):
    path = self.dir + "/CIFP/" + airport + ".dat"
    with open(path) as f:
      data = f.read().split(";\n")
      
    if not airport in self.airports: return None
    
    # scan runway waypoints
    for ln in data:
      ln = ln.strip()
      if not ln: continue
      kind, ln = ln.split(":")
      if kind != "RWY":
        continue
      
      spl = ln.split(";")
      parts = spl[0]
      parts = parts.split(",")
      
      rwy = parts[0].strip()
      
      self.airports[airport].runways.append(rwy)
      
      if len(spl) == 1: # missing lat lon
        # try to recover by finding the associated ils waypoint
        ils_ident = parts[5].strip()
        if ils_ident in self.runway_waypoints[airport]:
          self.runway_waypoints[airport][rwy] = self.runway_waypoints[airport][ils_ident]
        continue
      
      opt = spl[1]
      opt = opt.split(",")
      
      lat = opt[0]
      lon = opt[1]
      
      lats = 1 if lat[0] == "N" else -1
      lons = 1 if lon[0] == "E" else -1
      
      lat = lats * int(lat[1:]) / 1000000
      lon = lons * int(lon[1:]) / 1000000
      
      region = self.airports[airport].region if airport in self.airports else ""
      self.runway_waypoints[airport][rwy] = Waypoint(rwy, lat, lon, region)
  
    # type, qual, proc ident, trans ident
    procedures: dict[tuple[ProcKind, str, str, str], list[Leg]] = defaultdict(lambda: [])
    
    try:
      for ln in data:
        ln = ln.strip()
        if not ln: continue
        kind, ln = ln.split(":")
        if kind == "RWY":
          continue
        elif kind == "PRDAT":
          continue
        else:
          ln = ln.split(",")
          kind_enum: ProcKind
          if kind == "SID": kind_enum = ProcKind.SID
          elif kind == "STAR": kind_enum = ProcKind.STAR
          else: kind_enum = ProcKind.APPCH
          
          leg = self.process_line(kind_enum, ln, airport)
          procedures[(leg.info.kind, leg.info.qual, leg.info.proc, leg.info.trans)].append(leg)
          
    except KeyError as e:
      print(f"Error loading data for airport `{airport}`:")
      print(e.args[0])
    
    return self.sort_data(procedures, airport)
  
  def parse_rwy(self, rwy: str, airport: str) -> list[str]:
    if rwy == "ALL": return self.airports[airport].runways
    if rwy[0:2] != "RW": return []
    rwy = rwy[2:]
    if rwy[-1] == "B":
      return list(filter(lambda x: x.startswith("RW" + rwy[:-1]), self.airports[airport].runways))
    return [rwy]
  
  def extract_rwy(self, proc: str) -> str | None:
    if not proc[1:3].isnumeric(): return None
    if len(proc) <= 3 or proc[3] == "-": return proc[1:3]
    else: return proc[1:3].replace("0", "") + proc[3]
  
  def sort_data(self, procedures: dict[tuple[ProcKind, str, str, str], list[Leg]], airport: str):
    sids: dict[str, SID] = querydict.QueryDict(lambda x: SID(x, airport))
    stars: dict[str, STAR] = querydict.QueryDict(lambda x: STAR(x, airport))
    appches: dict[str, Approach] = querydict.QueryDict(lambda x: Approach(x, airport))
    
    for (kind, qual, proc_id, trans_id), legs in procedures.items():
      legs.sort(key=lambda k: k.info.seq)
            
      if kind == ProcKind.SID:
        proc = sids[proc_id]
        if qual in ["0", "1", "2", "4", "F", "M", "T", "V"]:
          if trans_id:
            proc.rwys = self.parse_rwy(trans_id, airport)
          proc.legs = legs
        elif qual in ["3", "6", "S", "V"]:
          proc.transitions.append((trans_id, legs))
        else:
          proc.legs = legs
      elif kind == ProcKind.STAR:
        proc = stars[proc_id]
        if qual in ["2", "5", "3", "6", "8", "9", "M", "S"]:
          if trans_id:
            proc.rwys = self.parse_rwy(trans_id, airport)
          proc.legs = legs
        elif qual in ["1", "4", "7", "F"]:
          proc.transitions.append((trans_id, legs))
        else:
          proc.legs = legs
      else: # kind = approach
        proc = appches[proc_id]
        proc.rwy = self.extract_rwy(proc_id)
        if qual == "A": proc.transitions.append((trans_id, legs))
        else: proc.legs = legs
    return (sids, stars, appches)

if __name__ == "__main__":
  # testing
  dir = "/home/mark/gamedrive/xplane-12/Custom Data/"
  data = NavDatabase(dir)
  for a in os.listdir(dir + "/CIFP"):
    data.get_airport_data(a[:-4])
