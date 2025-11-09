from dataclasses import dataclass, field
from enum import Enum
from math import pi
from collections import OrderedDict

@dataclass
class AircraftConfig:
  min_turn_tadius: float = 1
  climb_grad: float = 0.1
  descent_grad: float = 0.05240778 # tan(3 * pi / 180)

@dataclass
class PathPoint:
  lat: float # radians
  lon: float # radians
  course: float # **inbound** course, true, and in radians
  altitude: float = float('-inf')
  
  def latlon(self):
    return (self.lat, self.lon)
  
  def print_deg(self):
    print(f"PathPoint(lat={self.lat * 180 / pi}, lon={self.lon * 180 / pi}, course={self.course * 180 / pi}, altitude={self.altitude})")

class ProcKind(Enum):
  SID = 0
  STAR = 1
  APPCH = 2

@dataclass
class Course:
  val: float
  truenorth: bool
  def as_rad(self): return self.val * pi / 180
  
  def pretty_print(self):
    suffix = "°T" if self.truenorth else "°"
    return str(round(self.val)) + suffix
  
@dataclass
class DistOrTime:
  val: float
  is_dist: float

@dataclass
class Waypoint:
  name: str
  lat: float # decimal degrees
  lon: float # decimal degrees
  region: str
  airport: str
  
  def to_rad(self):
    return (self.lat * pi / 180, self.lon * pi / 180)
  
class AltRestr:
  def pretty_print(self) -> str: raise NotImplementedError

class SpeedRestr:
  def pretty_print(self) -> str: raise NotImplementedError

# @
@dataclass
class AtSpeed(SpeedRestr):
  speed: int
  def pretty_print(self) -> str:
    return f"At {self.speed}kt"

# =+, -
@dataclass
class SpeedRange(SpeedRestr):
  speed: int
  above: bool
  def pretty_print(self) -> str:
    qual = "A" if self.above else "B"
    return f"{qual}{self.speed}kt"

# @
@dataclass
class AtAlt(AltRestr):
  at: int
  def pretty_print(self) -> str: return "At " + str(self.at)

# +, -, B, C
@dataclass
class AltRange(AltRestr):
  above: int | None
  below: int | None
  def pretty_print(self) -> str:
    above = self.above
    below = self.below
    
    if above == below and not (above is None):
      return "At " + str(above)
    
    ret = ""
    if not (self.above is None):
      ret += "A" + str(self.above)
    if not (self.below is None):
      ret += "B" + str(self.below)
    return ret
      
# G, H
@dataclass
class GlideslopeAlt(AltRestr):
  msl: int
  alt: int
  above: bool # true = above, false = at
  
  def pretty_print(self) -> str:
    qual = "A" if self.above else "At "
    return f"{qual}{self.alt}, GS{self.msl}" 

# I, J
@dataclass
class GlideslopeIntc(AltRestr):
  intc: int
  alt: int
  above: bool # true = above, false = at

  def pretty_print(self) -> str:
    qual = "A" if self.above else "At "
    return f"{qual}{self.alt}, GS Intercept {self.intc}" 
# V, Y
@dataclass
class StepDownAboveBelow(AltRestr):
  alt: int
  valt: int
  above_below: bool # true = above, false = below
  
  def pretty_print(self) -> str:
    qual = "A" if self.above_below else "B"
    return f"{qual}{self.alt}, Glide {self.valt}" 
# X
@dataclass
class StepDownAt(AltRestr):
  alt: int
  valt: int

  def pretty_print(self) -> str:
    return f"At {self.alt}, Glide {self.valt}" 

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
  kind: ProcKind
  qual: str
  proc: str
  trans: str
  
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
  def type_str(self) -> str:
    raise NotImplementedError("Not implemented")
  def title(self) -> str:
    raise NotImplementedError("Not implemented")    
  def fix_name(self) -> str:
    raise NotImplementedError
  info: LegInfo

@dataclass
class InitialFix(Leg):
  def type_str(self): return "IF"
  fix: Waypoint
  def fix_name(self) -> str:
    return self.fix.name
  
  def title(self) -> str:
    return "Initial Fix"
    

@dataclass
class TrackToFix(Leg):
  def type_str(self): return "TF"
  fix: Waypoint
  def fix_name(self) -> str:
    return self.fix.name
  def title(self) -> str:
    return "Track to Fix"

@dataclass
class CourseToFix(Leg):
  def type_str(self): return "CF"
  
  fix: Waypoint
  course: Course
  rcmd: RadialDME | None
  
  def fix_name(self) -> str:
    return self.fix.name
  def title(self) -> str:
    return f"Course {self.course.pretty_print()} to Fix"

@dataclass
class DirectToFix(Leg):
  def type_str(self): return "DF"
  
  fix: Waypoint
  rcmd: RadialDME | None
  
  def fix_name(self) -> str:
    return self.fix.name
  
  def title(self) -> str:
    return "Direct to Fix"

@dataclass
class FixToAltitude(Leg):
  def type_str(self): return "FA"
  
  start: Waypoint
  course: Course
  alt: int
  
  rcmd: RadialDME
  
  def fix_name(self) -> str:
    return f"({self.alt}ft)"
  
  def title(self) -> str:
    return "Fix to Altitude"

@dataclass
class FixToDistance(Leg):
  def type_str(self): return "FC"
  
  start: Waypoint
  course: Course
  dist: float
  
  def title(self) -> str:
    return "Fix to Distance"
  
  def fix_name(self) -> str:
    return f"{self.start.name}/{self.dist}NM/{self.course.pretty_print()}"

@dataclass
class FixToDME(Leg):
  def type_str(self): return "FD"
  
  start: Waypoint
  course: Course
  ref: Waypoint
  dist: float
  
  def fix_name(self) -> str:
    return f"D{self.dist}{self.ref.name}"
  
  def title(self) -> str:
    return "Fix to DME"
  
@dataclass
class FixToManual(Leg):
  def type_str(self): return "FM"
  
  start: Waypoint
  course: Course
  rcmd: RadialDME
  
  def fix_name(self) -> str:
    return ""
  
  def title(self) -> str:
    return "Fix to Manual"

@dataclass
class CourseToAlt(Leg):
  def type_str(self): return "CA"
  
  course: Course
  alt: int
  
  def fix_name(self) -> str:
    return f"({self.alt}ft)"
  
  def title(self) -> str:
    return f"Course {self.course.pretty_print()} to Altitude" 

@dataclass
class CourseToDME(Leg):
  def type_str(self): return "CD"
  
  course: Course
  ref: Waypoint
  dist: float
  
  def fix_name(self) -> str:
    return f"{self.ref.name}/{self.dist}DME"

  def title(self) -> str:
    return f"Course {self.course.pretty_print()} to DME"
  
  
@dataclass
class CourseToIntercept(Leg):
  def type_str(self): return "CI"
  
  course: Course
  rcmd: Waypoint | None
  
  def fix_name(self) -> str:
    return "(Intercept)"
  
  def title(self) -> str:
    return f"Course {self.course.pretty_print()} to Intercept"

@dataclass
class CourseToRadial(Leg):
  def type_str(self): return "CR"
  
  course: Course
  radial: Radial
  
  def fix_name(self) -> str:
    return f"{self.radial.fix.name}/{self.radial.rad.pretty_print()}"
  
  def title(self) -> str:
    return f"Course {self.course.pretty_print()} to Radial"
  
@dataclass
class RadiusArc(Leg):
  def type_str(self): return "RF"

  fix: Waypoint
  center: Waypoint
  dist: float # track distance, not radius!
  
  def fix_name(self) -> str:
    return self.fix.name
  
  def title(self) -> str:
    return "Constant Radius Arc"
  
@dataclass
class ArcToFix(Leg):
  def type_str(self): return "AF"
  
  fix: Waypoint
  radial: RadialDME # note: the radial is redundant but is always provided
  
  def fix_name(self) -> str:
    return self.fix.name
  
  def title(self) -> str:
    return "Arc to Fix"
  
@dataclass
class HeadingToAlt(Leg):
  def type_str(self): return "VA"

  heading: Course
  alt: int
  
  def fix_name(self) -> str:
    return f"({self.alt}ft)"
  
  def title(self) -> str:
    return f"Heading {self.heading.pretty_print()} to Altitude"
  
@dataclass
class HeadingToDME(Leg):
  def type_str(self): return "VD"
  
  heading: Course
  ref: Waypoint
  dist: float

  def fix_name(self) -> str:
    return f"{self.ref.name}/{self.dist}DME"
  
  def title(self) -> str:
    return f"Heading {self.heading.pretty_print()} to DME"
  
@dataclass
class HeadingToIntercept(Leg):
  def type_str(self): return "VI"

  heading: Course
  rcmd: Waypoint | None
  
  def fix_name(self) -> str:
    return "(Intercept)"
  
  def title(self) -> str:
    return f"Heading {self.heading.pretty_print()} to Intercept"
  
@dataclass
class HeadingToManual(Leg):
  def type_str(self): return "VM"
  
  # Note (ARINC 424): "If a STAR route ends with a vector heading, the airport ident is entered in the waypoint ident field."
  fix: Waypoint | None
  heading: Course
  
  def fix_name(self) -> str:
    return ""

  def title(self) -> str:
    return f"Heading {self.heading.pretty_print()} to Manual"
  
@dataclass
class HeadingToRadial(Leg):
  def type_str(self): return "VR"
  
  heading: Course
  radial: Radial

  def fix_name(self) -> str:
    return f"{self.radial.fix.name}/{self.radial.rad.pretty_print()}"
  
  def title(self) -> str:
    return "Heading to Radial"
# Course reversal
@dataclass
class ProcTurn(Leg):
  def type_str(self): return "PI"
  
  fix: Waypoint
  alt: int
  course: Course
  max_dist: float # must remain within this distance of the fix
  
  def fix_name(self) -> str:
    return f"(Proc turn)"

  def title(self) -> str:
    return "Procedure Turn"

# terminates at an altitude
@dataclass
class HoldAlt(Leg):
  def type_str(self): return "HA"
  
  fix: Waypoint
  alt: int
  disttime: DistOrTime
  course: Course
  
  def fix_name(self) -> str:
    return self.fix.name

  def title(self) -> str:
    return "Hold to altitude"
  
# terminates after one orbit
@dataclass
class HoldFix(Leg):
  def type_str(self): return "HF"
  
  fix: Waypoint
  disttime: DistOrTime
  course: Course

  def fix_name(self) -> str:
    return self.fix.name

  def title(self) -> str:
    return "Hold once"
  
@dataclass
class HoldToManual(Leg):
  def type_str(self): return "HM"

  fix: Waypoint
  disttime: DistOrTime
  course: Course
  
  def fix_name(self) -> str:
    return self.fix.name

  def title(self) -> str:
    return "Hold"
  
@dataclass
class AirportInfo:
  icao: str
  lat: float
  lon: float
  region: str
  elevation: int
  ta: int
  tl: int
  runways: list[str] = field(default_factory=list)

@dataclass
class SID:
  ident: str
  airport: str
  rwys: dict[str, list[Leg]] = field(default_factory=OrderedDict)
  is_all_rwys: bool = False
  transitions: dict[str, list[Leg]] = field(default_factory=OrderedDict)

@dataclass
class STAR:
  ident: str
  airport: str
  rwys: dict[str, list[Leg]] = field(default_factory=OrderedDict)
  is_all_rwys: bool = False
  transitions: dict[str, list[Leg]] = field(default_factory=OrderedDict)

@dataclass
class Approach:
  ident: str
  airport: str
  rwy: str | None = None
  transitions: dict[str, list[Leg]] = field(default_factory=OrderedDict)
  legs: list[Leg] = field(default_factory=list)
