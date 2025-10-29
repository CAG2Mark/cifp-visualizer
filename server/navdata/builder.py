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
  course: float # true, and in radians
  def print_deg(self):
    print(f"PathPoint(lat={self.lat * 180 / pi}, lon={self.lon * 180 / pi}, prog={self.prog}, course={self.course * 180 / pi})")

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
  
# all input and output angles to math helper functions are in RADIANS

def get_sphere_tangent(latlon: tuple[float, float], course: float):
  outward = to_xyz(*latlon)
  north = Vec3(0, 0, 1)
  eq_pt = to_xyz(0, latlon[1])
  to_north = north * cos(latlon[0]) - eq_pt * sin(latlon[0])
  east = to_north.cross(outward)
  return to_north * cos(course) + east * sin(course)

# returns orthonormal basis
# (center of circle in xyz, v1, v2, v3), v1 v2 v3 orthonormal
# v1 goes from the origin to `start`
# v2 goes from `center` to start
# v3 is either clockwise or counterclockwise 90deg from v2
def get_turning_cirle(center: tuple[float, float], start: tuple[float, float], clockwise: bool = False) -> tuple[Vec3, Vec3, Vec3, Vec3]:
  # observation: any circle on a sphere is a circle in euclidian space
  # we try to create an equation for this circle
  # suppose latlon and start are converted into xyz coordinates
  # we first bring latlon closer to the origin so that latlon
  # lies within the circle's plane
  
  center_ = to_xyz(*center)
  s = to_xyz(*start)
  
  # calculate angle between
  # angle is cos of the angle between l and s
  angle = center_.dot(s)
  # depresss latlon
  l = center_ * angle

  # create orthonormal frame with v1 = l and v2 = (s - l) as the first two vectors,
  # then cross v1 and v2 to get another vector v3
  # then by the right hand rule, v3 is rotated counterclockwise 90deg from v2
  
  v1 = center_
  v2 = (s - l).normalize() # from latlon to start
  v3 = v1.cross(v2)
  if clockwise: v3 = -v3
  
  assert(abs(v1.dot(v2)) < TOLERANCE)
  assert(abs(v1.dot(v3)) < TOLERANCE)
  assert(abs(v2.dot(v3)) < TOLERANCE)
  
  return (l, v1, v2, v3)

TOLERANCE = 0.00001
# turndir = True => turn RIGHT
# does NOT return the start point, but returns the end point
# returns: (points, true outbound course)
# where points are on the arc from `start` to `end` centered at `center`
def get_arc_points(
    center: tuple[float, float],
    start: PathPoint,
    end: PathPoint,
    num_points: int,
    turn_right: bool = False,
    turning_circle: tuple[Vec3, Vec3, Vec3, Vec3] | None = None) -> list[PathPoint]:
  center_ = to_xyz(*center)
  s = to_xyz(start.lat, start.lon)
  e = to_xyz(end.lat, end.lon)

  if not abs(sqrt((center_ - s).mag2()) - sqrt((center_ - e).mag2())) < TOLERANCE:
    raise ValueError("`start` and `end` do not lie on a circle centered at `latlon`.")
  
  if turning_circle is None:
    l, v1, v2, v3 = get_turning_cirle(center, (start.lat, start.lon), turn_right)
  else:
    l, v1, v2, v3 = turning_circle

  
  e_del = (e - l).normalize()
  
  e_v2cmp = e_del.dot(v2) # cosine component
  e_v3cmp = e_del.dot(v3) # sine component
  e_ang = atan2(e_v3cmp, e_v2cmp)
  if e_ang < 0: e_ang += 2 * pi
  
  return get_arc_points_angle(
    center,
    start,
    e_ang,
    num_points,
    turn_right,
    (l, v1, v2, v3)
  )

def get_course(latlon: tuple[float, float], tangent: Vec3) -> float:
  # calculate the outbound course while v1, v2, v3 are still normal vectors
  # create a line going from south to north on the endpoint's longitude
  e = to_xyz(*latlon)
  north = Vec3(0, 0, 1)
  eq_pt = to_xyz(0, latlon[1]).normalize()
  # the line is given by north * sin(theta) + eq_pt * cos(theta), where -pi <= theta <= pi, i.e. theta is latitude
  # tangent line is given by north * cos(theta) - eq_pt * sin(theta)
  tangent1 = north * cos(latlon[0]) - eq_pt * sin(latlon[0])
  crs = acos(tangent1.dot(tangent))

  # we can check if the current tangent is clockwise or counterclockwise of the north line
  # by considering their cross product and comparing it with the x-y-z of the end coordinate
  if tangent1.cross(tangent).dot(e) > 0: crs = 2 * pi - crs

  return crs

# turn by `angle` radians
def get_arc_points_angle(
    center: tuple[float, float],
    start: PathPoint,
    angle: float,
    num_points: int,
    turn_right: bool = False,
    turning_circle: tuple[Vec3, Vec3, Vec3, Vec3] | None = None) -> list[PathPoint]:
  s = to_xyz(start.lat, start.lon)
  
  if turning_circle is None:
    l, _, v2, v3 = get_turning_cirle(center, (start.lat, start.lon), turn_right)
  else:
    l, _, v2, v3 = turning_circle
    
  dist = sqrt((s - l).mag2())

  e_ang = angle

  v2d = v2 * dist
  v3d = v3 * dist
  
  # now generate the points
  points_xyz: list[PathPoint] = []
  
  step = e_ang / num_points
  
  start_prog = start.prog
  
  for i in range(num_points):
    ang = step * (i + 1)
    lat, lon = to_latlon(v2d * cos(ang) + v3d * sin(ang) + l)
    tangent = -v2 * sin(ang) + v3 * cos(ang)
    point = PathPoint(lat, lon, start_prog + (i + 1) / num_points, get_course((lat, lon), tangent))
    points_xyz.append(point)
  
  return points_xyz

def turn_from(
    start: PathPoint,
    inbd_crs: float,
    outbd_crs: float,
    turn_radius: float,
    num_points: int,
    turn_right: bool):
  # observation: when turning at a constant rate from a point, the center of the turning circle
  # will always be at a right angle to the current course, so we can find this center easily
  # by walking perpencidular to the current course, at a distance of the turning radius
  to_point = to_xyz(start.lat, start.lon)
  tangent = get_sphere_tangent((start.lat, start.lon), inbd_crs)
  v3 = to_point.cross(tangent)
  if turn_right: v3 = -v3
  
  # the center of the turning circle lies in v3's direction
  
  # the turning circle's center can be found by moving (turn_radius / EARTH_RAD) radians
  # on the circle defined by (to_point, v3)
  angle = turn_radius / EARTH_RAD
  center = to_latlon(to_point * cos(angle) + v3 * sin(angle))
  
  # calculate how much we need to turn
  turn_amount = inbd_crs - outbd_crs
  if turn_right: turn_amount *= -1
  if turn_amount < 0: turn_amount += 2 * pi
  
  # sems we have no choice but to try and bisect how much we have to turn;
  # it seems it's not possible to find an inverse formula for the course
  # after turning some amount on a circle
  
  # note that v3 is exactly the inbound tangent vector
  l, v1, v2, v3 = get_turning_cirle(center, (start.lat, start.lon), turn_right)
  
  s = to_xyz(start.lat, start.lon)
  dist = sqrt((s - l).mag2())
  
  assert(abs(inbd_crs - get_course((start.lat, start.lon), v3)) < TOLERANCE)
  
  def shift_angle(angle: float):
    if turn_right and 0 <= angle < inbd_crs: angle += 2 * pi
    if not turn_right and inbd_crs < angle <= 2 * pi: angle -= 2 * pi
    if not turn_right: angle *= -1
    return angle
  
  def calc_angle(turn_ang: float):
    e = v2 * cos(turn_ang) * dist + v3 * sin(turn_ang) * dist + l
    end = to_latlon(e)
    # calculate the outbound tangent line (after flying the arc)
    # tangent line at the point is v2 * -sin(e_ang) + v3 * cos(e_ang) 
    tangent = -v2 * sin(turn_ang) + v3 * cos(turn_ang)
    
    # we want this function to be monotone increasing and continuous in turn_ang
    # if we are turning left and the course is between inbd and 2pi, we subtract 2pi
    # otherwise, if it is between 0 and inbd, we add 2pi
    # if we are turning left, also multiply by -1 to make it increasing
    return shift_angle(get_course(end, tangent))
  
  # set up binary search
  # bisect how much to turn
  ITERATIONS = 50
  TOL = 0.0000000000001
  target = shift_angle(outbd_crs)
  low = 0
  high = 2 * pi
  ans = -1
  for _ in range(ITERATIONS):
    mid = (low + high) / 2
    crs = calc_angle(mid)
    if abs(crs - target) < TOL:
      ans = mid
      break
    if target < crs: high = mid
    else: low = mid
  if ans == -1:
    ans = (low + high) / 2

  return get_arc_points_angle(center, start, ans, num_points, turn_right, (l, v1, v2, v3))
  
def to_xyz(lat: float, lon: float) -> Vec3:
  return Vec3(
    cos(lat) * cos(lon),
    cos(lat) * sin(lon),
    sin(lat)
  )

def to_xyz_earth(lat: float, lon: float) -> Vec3:
  return Vec3(
    EARTH_RAD * cos(lat) * cos(lon),
    EARTH_RAD * cos(lat) * sin(lon),
    EARTH_RAD * sin(lat)
  )

def to_latlon(v: Vec3) -> tuple[float, float]:
  return (
    asin(v.z),
    atan2(v.y, v.x)
  )

def to_latlon_earth(v: Vec3) -> tuple[float, float]:
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
