from server.navdata.defns import *
from pygeomag import GeoMag
from math import cos, sin, asin, acos, atan2, sqrt, pi
from typing import Self

# For calculating magnetic declination
geo_mag = GeoMag(coefficients_file="wmm/WMMHR.COF", high_resolution=True)

@dataclass
class PathPoint:
  lat: float
  lon: float
  prog: float
  course: float # trueI

EARTH_RAD = 3443.9184665
# EARTH_RAD = 1

@dataclass
class Vec3:
  x: float
  y: float
  z: float
  
  def normalize(self) -> Self:
    x = self.x
    y = self.y
    z = self.z
    coef = 1 / sqrt(self.dot(self))
    return Vec3(x * coef, y * coef, z * coef)
  
  def cross(self, other: Self) -> Self:
    return Vec3(
      self.y * other.z - self.z * other.y,
      self.z * other.x - self.x * other.z,
      self.x * other.y - self.y * other.x
    )
  
  def __add__(self, other: Self) -> Self:
    return Vec3(
      self.x + other.x,
      self.y + other.y,
      self.z + other.z
    )

  def __sub__(self, other: Self) -> Self:
    return Vec3(
      self.x - other.x,
      self.y - other.y,
      self.z - other.z
    )
  
  def __mul__(self, other: float)-> Self:
    return Vec3(
      self.x * other,
      self.y * other,
      self.z * other
    )
  
  def __neg__(self) -> Self:
    return Vec3(
      -self.x,
      -self.y,
      -self.z
    )
  
  def dot(self, other: Self):
    return self.x * other.x + self.y * other.y + self.z * other.z
  
  def mag2(self):
    return self.dot(self)

EPS = 0.000001
# turndir = True => turn RIGHT
# does NOT return the start point, but returns the end point
# returns: (points, true outbound course)
def get_arc_points(latlon: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
    num_points: int,
    turn_right: bool = False) -> tuple[list[tuple[float, float]], float]:
  # observation: any circle on a sphere is a circle in euclidian space
  # we try to create an equation for this circle
  # suppose latlon and start are converted into xyz coordinates
  # we first bring latlon closer to the origin so that latlon
  # lies within the circle formed
  
  center = to_xyz(*latlon)
  s = to_xyz(*start)
  e = to_xyz(*end)
  
  print(center, s, e)
  
  if not abs((center - s).mag2() - (center - e).mag2()) < EPS:
    raise ValueError("`start` and `end` do not lie on a circle centered at `latlon`.")
  
  # calculate angle between
  # angle is cos of the angle between l and s
  angle = center.dot(s) / (EARTH_RAD * EARTH_RAD)
  # depresss latlon
  l = center * angle
  
  dist = sqrt((s - l).mag2())

  # create orthonormal frame with v1 = l and v2 = (s - l) as the first two vectors,
  # then cross v1 and v2 to get another vector v3
  # then by the right hand rule, v3 is rotated counterclockwise 90deg from v2
  
  v1 = l.normalize() # from center to latlon
  v2 = (s - l).normalize() # from latlon to start
  v3 = v1.cross(v2)
  
  print(v1, v2, v3)
  
  if turn_right: v3 = -v3
  
  assert(abs(v1.dot(v2)) < EPS)
  assert(abs(v1.dot(v3)) < EPS)
  assert(abs(v2.dot(v3)) < EPS)
  
  e = (e - l).normalize()
  
  e_v2cmp = e.dot(v2) # cosine component
  e_v3cmp = e.dot(v3) # sine component
  e_ang = atan2(e_v3cmp, e_v2cmp)
  if e_ang < 0: e_ang += 2 * pi
  
  # calculate the outbound course while v1, v2, v3 are still normal vectors
  # create a line going from south to north on the endpoint's longitude
  south = Vec3(0, 0, -1)
  eq_pt = to_xyz(0, end[1]).normalize()
  # the line is given by south * sin(theta) + eq_pt * cos(theta), where -pi <= theta <= pi, i.e. theta is latitude
  # tangent line is given by south * cos(theta) - eq_pt * sin(theta)
  tangent1 = south * cos(end[0]) - eq_pt * sin(end[0])
  # calculate the outbound tangent line (after flying the arc)
  # note that e_v2cmp = cos(e_ang) and e_v3cmp = sin(e_ang)
  # tangent line at the point is v2 * -sin(e_ang) + v3 * cos(e_ang) 
  tangent2 = -v2 * e_v3cmp + v3 * e_v2cmp
  crs = acos(tangent1.dot(tangent2))
  if crs < 0: crs += 2 * pi
  crs *= 180 / pi
  
  v1 = v1 * dist
  v2 = v2 * dist
  v3 = v3 * dist
  
  # now generate the points
  points_xyz: list[tuple[float, float]] = []
  
  step = e_ang / num_points
  for i in range(num_points):
    ang = step * (i + 1)
    point = to_latlon(v2 * cos(ang) + v3 * sin(ang) + l)
    points_xyz.append(point)
  
  return (points_xyz, crs)

def turn_from(start: tuple[float, float], inbd_crs: float, outbd_crs: float, turn_radius: float, turn_right: bool):
  
  pass

def to_xyz(lat: float, lon: float) -> Vec3:
  return Vec3(
    EARTH_RAD * cos(lat) * cos(lon),
    EARTH_RAD * cos(lat) * sin(lon),
    EARTH_RAD * sin(lat)
  )

def to_latlon(v: Vec3) -> tuple[float, float]:
  return (
    asin(v.z / EARTH_RAD),
    atan2(v.y, v.x)
  )

def build_2d(legs: list[Leg]):
  points: list[PathPoint] = []
  
  cur_course = -1

  for i, leg in enumerate(legs):
    match leg:
      case InitialFix(info, fix):
        pass
      case TrackToFix(info, fix):
        pass
      case CourseToFix(info, fix, course, rcmd):
        pass
      case DirectToFix(info, rcmd):
        pass
      case FixToAltitude(info, fix, rcmd):
        pass
      case FixToDistance(info, start, course, alt, rcmd):
        pass
      case FixToDistance(info, start, dist):
        pass
      case FixToDME(info, start, to, dist):
        pass
      case FixToManual(info, start, course, rcmd):
        pass
      case CourseToAlt(info, course, alt):
        pass
      case CourseToDME(info, course, to, dist):
        pass
      case CourseToIntercept(info, course, rcmd):
        pass
      case CourseToRadial(info, course, radial):
        pass
      case RadiusArc(info, waypoint, center, dist):
        pass
      case ArcToFix(info, fix, radial):
        pass
      case HeadingToAlt(info, heading, alt):
        pass
      case HeadingToDME(info, heading, rcmd, radial):
        pass
      case HeadingToIntercept(info, heading, rcmd):
        pass
      case HeadingToManual(info, fix, heading):
        pass
      case HeadingToRadial(info, heading, radial):
        pass
      case ProcTurn(info, fix, alt, course, max_dist):
        pass
      case HoldAlt(info, fix, alt, disttime, course):
        pass
      case HoldFix(info, fix, disttime, course):
        pass
      case HoldToManual(info, fix, disttime, course):
        pass

      case _: raise ValueError("Invalid leg")

res = get_arc_points((pi/2, 0), (pi/2 - 0.1, 0), (pi/2 - 0.1, pi), 2)
print(res)
print()
