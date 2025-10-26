from dataclasses import dataclass

@dataclass
class Course:
  val: float
  truenorth: bool
  
@dataclass
class DistOrTime:
  val: float
  is_dist: float

@dataclass
class Waypoint:
  name: str
  lat: float
  lon: float
  region: str
  
class AltRestr: pass

class SpeedRestr: pass

# @
@dataclass
class AtSpeed(SpeedRestr):
  speed: int

# =+, -
@dataclass
class SpeedRange(SpeedRestr):
  speed: int
  above: bool

# @
@dataclass
class AtAlt(AltRestr):
  at: int

# +, -, B, C
@dataclass
class AltRange(AltRestr):
  above: int | None
  below: int | None

# G, H
@dataclass
class GlideslopeAlt(AltRestr):
  msl: int
  alt: int
  above: bool

# I, J
@dataclass
class GlideslopeIntc(AltRestr):
  intc: int
  alt: int
  above: bool

@dataclass
class RadialDME:
  fix: Waypoint
  rad: Course
  dist: float
  
@dataclass
class Radial:
  fix: Waypoint
  rad: Course
  
@dataclass
class LegInfo:
  seq: int
  
  # false = left
  # important: this specifies the direction you turn into the next leg,
  # not the direction you turn off the previous leg
  turndir: bool | None
  overfly: bool
  fmap: bool # first missed approach fix
  mapt: bool # missed approach point
  iaf: bool # initial approach fix
  faf: bool # final approach fix
  alt: AltRestr | None
  speed: SpeedRestr | None
  glide_angle: float | None

@dataclass
class Leg:
  def type_str(self):
    raise NotImplementedError("Not implemented")
  info: LegInfo

@dataclass
class InitialFix(Leg):
  def type_str(self): return "IF"
  fix: Waypoint

@dataclass
class TrackToFix(Leg):
  def type_str(self): return "TF"
  fix: Waypoint

@dataclass
class CourseToFix(Leg):
  def type_str(self): return "CF"
  
  fix: Waypoint
  course: Course
  rcmd: RadialDME | None

@dataclass
class DirectToFix(Leg):
  def type_str(self): return "DF"
  
  fix: Waypoint
  rcmd: RadialDME | None

@dataclass
class FixToAltitude(Leg):
  def type_str(self): return "FA"
  
  start: Waypoint
  course: Course
  alt: int
  
  rcmd: RadialDME

@dataclass
class FixToDistance(Leg):
  def type_str(self): return "FC"
  
  start: Waypoint
  dist: float

@dataclass
class FixToDME(Leg):
  def type_str(self): return "FD"
  
  start: Waypoint
  to: Waypoint
  dist: float

@dataclass
class FixToManual(Leg):
  def type_str(self): return "FM"
  
  start: Waypoint
  course: Course
  rcmd: RadialDME

@dataclass
class CourseToAlt(Leg):
  def type_str(self): return "CA"
  
  course: Course
  alt: int

@dataclass
class CourseToDME(Leg):
  def type_str(self): return "CD"
  
  course: Course
  to: Waypoint
  dist: float

@dataclass
class CourseToIntercept(Leg):
  def type_str(self): return "CI"
  
  course: Course
  rcmd: Waypoint | None

@dataclass
class CourseToRadial(Leg):
  def type_str(self): return "CR"
  
  course: Course
  radial: Radial

@dataclass
class RadiusArc(Leg):
  def type_str(self): return "RF"

  fix: Waypoint
  center: Waypoint
  dist: float # track distance, not radius!

@dataclass
class ArcToFix(Leg):
  def type_str(self): return "AF"
  
  fix: Waypoint
  radial: RadialDME # note: the radial is redundant but is always provided
  
@dataclass
class HeadingToAlt(Leg):
  def type_str(self): return "VA"

  heading: Course
  alt: int
  
@dataclass
class HeadingToDME(Leg):
  def type_str(self): return "VD"
  
  heading: Course
  rcmd: Waypoint
  radial: RadialDME

@dataclass
class HeadingToIntercept(Leg):
  def type_str(self): return "VI"

  heading: Course
  rcmd: Waypoint | None
  
@dataclass
class HeadingToManual(Leg):
  def type_str(self): return "VM"
  
  fix: Waypoint | None
  heading: Course

@dataclass
class HeadingToRadial(Leg):
  def type_str(self): return "VR"
  
  heading: Course
  radial: Radial

# Course reversal
@dataclass
class ProcTurn(Leg):
  def type_str(self): return "PI"
  
  fix: Waypoint
  alt: int
  course: Course
  max_dist: float # must remain within this distance of the fix

# terminates at an altitude
@dataclass
class HoldAlt(Leg):
  def type_str(self): return "HA"
  
  fix: Waypoint
  alt: int
  disttime: DistOrTime
  course: Course

# terminates after one orbit
@dataclass
class HoldFix(Leg):
  def type_str(self): return "HF"
  
  fix: Waypoint
  disttime: DistOrTime
  course: Course

@dataclass
class HoldToManual(Leg):
  def type_str(self): return "HM"
  fix: Waypoint
  disttime: DistOrTime
  course: Course

@dataclass
class AirportInfo:
  icao: str
  lat: float
  lon: float
  region: str
  elevation: int
  ta: int
  tl: int
