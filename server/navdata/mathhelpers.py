from server.navdata.defns import *
from pygeomag import GeoMag
import datetime
from math import cos, sin, asin, acos, atan2, sqrt, pi, ceil
from typing import Self

NM_TO_FT = 6076.12

# For calculating magnetic declination
geo_mag = GeoMag(coefficients_file="wmm/WMMHR.COF", high_resolution=True)
year = datetime.date.today().year
def to_mag(latlon: tuple[float, float], course: Course, alt: float = 0):
  if course.truenorth: return course.as_rad()
  
  decl = geo_mag.calculate(
    glat = latlon[0] * 180 / pi,
    glon = latlon[1] * 180 / pi,
    alt = alt,
    time = year
  ).d * pi / 180
  return course.as_rad() + decl

EARTH_RAD = 3443.9184665
# EARTH_RAD = 1

@dataclass
class Vec3:
  x: float
  y: float
  z: float
  
  def as_arr(self): return [self.x, self.y, self.z]
  
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

def angle_between(course: float, target_course: float, turn_right: bool):
  diff = course - target_course
  if turn_right: return (-diff) % (2 * pi)
  return diff % (2 * pi)

def get_sphere_tangent(latlon: tuple[float, float], course: float):
  outward = to_xyz(*latlon)
  north = Vec3(0, 0, 1)
  eq_pt = to_xyz(0, latlon[1])
  to_north = north * cos(latlon[0]) - eq_pt * sin(latlon[0])
  east = to_north.cross(outward)
  return to_north * cos(course) + east * sin(course)

# Returns the shortest great circle distance from a point to a great circle defined by `start` and `course`
def point_dist_to_line(point: tuple[float, float], start: tuple[float, float], course: float):
  tangent = get_sphere_tangent(start, course)
  plane_normal = to_xyz(*start).cross(tangent)
  return abs(asin(to_xyz(*point).dot(plane_normal)))

# Returns the intersection of a line and the perpendicular bisector going through a point
def point_bisect_line(point: tuple[float, float], start: tuple[float, float], course: float):
  tangent = get_sphere_tangent(start, course)
  plane_normal = to_xyz(*start).cross(tangent)
  
  point_xyz = to_xyz(*point)
  return to_latlon((point_xyz - plane_normal * (point_xyz.dot(plane_normal))).normalize())

def circle_distance(a: tuple[float, float], b: tuple[float, float]):
  arg = to_xyz(*a).dot(to_xyz(*b))
  arg = min(1, max(-1, arg))
  return abs(acos(arg))

def earth_distance(a: tuple[float, float], b: tuple[float, float]):
  return EARTH_RAD * circle_distance(a, b)

# return the first point reached when flying from a at the specified course
def get_intersection(a: tuple[float, float], a_crs: float, b: tuple[float, float], b_crs: float) -> tuple[float, float]:
  a_xyz = to_xyz(*a)
  b_xyz = to_xyz(*b)
  a_tan = get_sphere_tangent(a, a_crs)
  b_tan = get_sphere_tangent(b, b_crs)
  
  a_norm = a_xyz.cross(a_tan)
  b_norm = b_xyz.cross(b_tan)
  
  res = a_norm.cross(b_norm)
  res *= EARTH_RAD # scale by a large number because this number could be very small
  res = res.normalize()
  
  if res.mag2() < TOLERANCE:
    return a
  
  # point = cos(dist) * a_xyz + sin(dist) * a_tan
  a_dist1 = atan2(res.dot(a_tan), res.dot(a_xyz)) % (2 * pi)
  a_dist2 = atan2(-res.dot(a_tan), -res.dot(a_xyz)) % (2 * pi)

  ans = res if a_dist1 < a_dist2 else -res
  
  return to_latlon(ans)

# returns orthonormal basis
# (center of circle in xyz, v1, v2, v3), v1 v2 v3 orthonormal
# v1 goes from the origin to `center`
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

TOLERANCE = 0.3 / EARTH_RAD
RF_TOLERANCE = 0.3 / EARTH_RAD
# turndir = True => turn RIGHT
# does NOT return the start point, but returns the end point
# returns: (points, true outbound course)
# where points are on the arc from `start` to `end` centered at `center`
def get_arc_between_points(
    center: tuple[float, float],
    start: PathPoint,
    end: tuple[float, float],
    points_density: int,
    turn_right: bool = False,
    turning_circle: tuple[Vec3, Vec3, Vec3, Vec3] | None = None) -> list[PathPoint]:
  center_ = to_xyz(*center)
  s = to_xyz(*start.latlon())
  e = to_xyz(*end)

  if not abs(sqrt((center_ - s).mag2()) - sqrt((center_ - e).mag2())) < RF_TOLERANCE:
    raise ValueError("`start` and `end` do not lie on a circle centered at `latlon`.")
  
  if turning_circle is None:
    l, v1, v2, v3 = get_turning_cirle(center, start.latlon(), turn_right)
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
    points_density,
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

# gets the course you take to go from a to b in a straight line
def get_course_between(a: tuple[float, float], b: tuple[float, float]) -> float:
  # just calculate the tangent line from a to b
  a_xyz = to_xyz(*a)
  b_xyz = to_xyz(*b)
  diff = (b_xyz - a_xyz) * EARTH_RAD # the differences can be so small that it results in a division by zero
  # make diff orthogonal to a_xyz
  diff = diff - a_xyz * (a_xyz.dot(diff))
  if diff.mag2() <= TOLERANCE: return -1
  return get_course(a, diff.normalize())

# turn by `angle` radians
def get_arc_points_angle(
    center: tuple[float, float],
    start: PathPoint,
    angle: float,
    points_density: int, # points per revolution per radius
    turn_right: bool = False,
    turning_circle: tuple[Vec3, Vec3, Vec3, Vec3] | None = None) -> list[PathPoint]:
  s = to_xyz(*start.latlon())
  
  if turning_circle is None:
    l, _, v2, v3 = get_turning_cirle(center, start.latlon(), turn_right)
  else:
    l, _, v2, v3 = turning_circle
    
  dist = sqrt((s - l).mag2())
  
  radius = circle_distance(start.latlon(), center)

  e_ang = angle

  v2d = v2 * dist
  v3d = v3 * dist
  
  # now generate the points
  points_xyz: list[PathPoint] = []
  
  num_points = ceil(points_density * (e_ang / (2 * pi)) * radius * EARTH_RAD)
  if num_points == 0: return []
  
  step = e_ang / num_points
  
  for i in range(num_points):
    ang = step * (i + 1)
    lat, lon = to_latlon(v2d * cos(ang) + v3d * sin(ang) + l)
    tangent = -v2 * sin(ang) + v3 * cos(ang)
    point = PathPoint(lat, lon, get_course((lat, lon), tangent)) # altitude populated later
    points_xyz.append(point)
  
  return points_xyz

# note: this returns a fairly crude approximation
def turn_towards(
    start: PathPoint,
    inbd_crs: float,
    dest: tuple[float, float],
    turn_radius: float,
    points_density: int,
    turn_right: bool) -> list[PathPoint]:
  
  if (to_xyz(*start.latlon()) - to_xyz(*dest)).mag2() < TOLERANCE * TOLERANCE: return [] 

  # just make sure the two things are not too close to each other
  circ_dist = circle_distance(start.latlon(), dest)
  if circ_dist < 2 * turn_radius / EARTH_RAD:
    turn_radius = circ_dist / 4
  
  to_point = to_xyz(*start.latlon())
  tangent = get_sphere_tangent(start.latlon(), inbd_crs)
  v3 = to_point.cross(tangent)
  if turn_right: v3 = -v3
  
  # the turning circle's center can be found by moving (turn_radius / EARTH_RAD) radians
  # on the circle defined by (to_point, v3)
  angle = turn_radius / EARTH_RAD
  center = to_latlon(to_point * cos(angle) + v3 * sin(angle))
  
  l, v1, v2, v3 = get_turning_cirle(center, start.latlon(), turn_right)
  
  # calculate how much we need to turn to directly face the destination
  # done using bisection
  s = to_xyz(*start.latlon())
  dist = sqrt((s - l).mag2())
  
  # assert(abs(inbd_crs - get_course(start.latlon(), v3)) < TOLERANCE)
  
  # cur course = a
  # target course = b
  def angle_between(a: float, b: float):
    return min(abs(b - a), abs(2 * pi - (b - a)), abs(2 * pi - (a - b)))
  
  # not monotone
  def calc_angle(turn_ang: float):
    e = v2 * cos(turn_ang) * dist + v3 * sin(turn_ang) * dist + l
    end = to_latlon(e)
    # calculate the outbound tangent line (after flying the arc)
    # tangent line at the point is v2 * -sin(e_ang) + v3 * cos(e_ang) 
    tangent = -v2 * sin(turn_ang) + v3 * cos(turn_ang)
    
    # current course
    course = get_course(end, tangent)
    
    # course needed to fly towards the point
    req_crs = get_course_between(end, dest)
    
    # we want this function to be strictly increasing (this should be the case usually)
    # if we are turning left, then (course - req_course)
    return angle_between(course, req_crs)
  
  # set up binary search
  # bisect how much to turn
  ITERATIONS = 720
  step = 2 * pi / ITERATIONS
  best = 100
  best_ang = -1
  for i in range(ITERATIONS):
    turn = i * step
    ang = calc_angle(turn)
    if ang == -1:
      best = 0
      best_ang = turn
      break
    
    if ang < best:
      best = ang
      best_ang = turn

  # one degree of tolerance
  if best > 2 * pi / 360 or best_ang == -1:
    return [] # just give up and fly directly to the dest
  
  return get_arc_points_angle(to_latlon(l), start, best_ang, points_density, turn_right, (l, v1, v2, v3))

def turn_to_course_towards(
    start: PathPoint,
    inbd_crs: float,
    dest: tuple[float, float],
    course: float,
    min_radius: float,
    points_density: int,
    turn_right: bool
) -> list[PathPoint]:
  # The turning circle intersects the radial if and only if
  # min_dist(circle center, radial) <= radius
  # Furthermore, radius - min_dist(circle center, radial) is increasing
  # So we can bisect
  
  to_point = to_xyz(*start.latlon())
  tangent = get_sphere_tangent(start.latlon(), inbd_crs)
  v3 = to_point.cross(tangent)
  if turn_right: v3 = -v3
  
  # Bisect the smallest radius required
  low = min(4, min_radius) / EARTH_RAD
  high = -1
  ITERATIONS = 60
  step = 1 / EARTH_RAD
  for i in range(10): # 1024 nautical miles should be more than enough
    radius = low + step * (2**i)
    center = to_latlon(to_point * cos(radius) + v3 * sin(radius))
    dist = point_dist_to_line(center, dest, course)
    diff = radius - dist
    if diff >= 0:
      high = radius
      low = radius / 2
      break
  if high == -1: raise Exception("Could not find a large enough circle")
  
  TOL = 0.0000000000001
  ans = -1
  diff = -1
  for i in range(ITERATIONS):
    radius = (low + high) / 2
    center = to_latlon(to_point * cos(radius) + v3 * sin(radius))
    dist = point_dist_to_line(center, dest, course)
    diff = radius - dist
    if abs(diff) < TOL:
      ans = radius
      break
    if diff < 0: # no intersection, need to increase radius
      low = radius
    else:
      high = radius
  ans = (low + high) / 2

  center = to_point * cos(ans) + v3 * sin(ans)
  center_l = to_latlon(center)
  l, v1, v2, v3 = get_turning_cirle(center_l, start.latlon(), turn_right)
  
  circ_dist = sqrt((to_point - center).mag2())
  v2d = v2 * circ_dist
  v3d = v3 * circ_dist
  
  if abs(diff) - TOL <= TOL: # The circle is the perfect size
    # We can just terminate at the desired course.
    return turn_from(start, inbd_crs, course, ans * EARTH_RAD, points_density, turn_right)
  elif diff > 0: # The circle is too big, but we still intersect the radial
    
    # we can analytically solve for the intersection!
    # a point x is on the radial if and only if
    # a dot n = 0
    # where n is the normal to the radial.
    # Note that for f(a) = v2d * cos(a) + v3d * sin(a) + l, where l is the circle center
    # f(a) is on the intersection if and only if f(a) dot n = 0
    # i.e. (v2d dot n) cos(a) + (v3d dot n) sin(a) + l dot n = 0
    # which may be solved analytically by writing the cos and sin sum as
    # ksin(a + c) for some k, c, which gives
    # sin(a + c) = (-l dot norm) / k
    
    dest_xyz = to_xyz(*dest)
    dest_tan = get_sphere_tangent(dest, course)
    norm = dest_xyz.cross(dest_tan)
    
    v2n = v2d.dot(norm)
    v3n = v3d.dot(norm)

    c = atan2(v2n, v3n)
    k = sqrt(v2n * v2n + v3n * v3n)
    rhs = asin(-l.dot(norm) / k)
    
    a1 = rhs
    a2 = pi - rhs
    ans1 = (a1 - c) % (2 * pi)
    ans2 = (a2 - c) % (2 * pi)
    
    ans = min(ans1, ans2)
    
    return get_arc_points_angle(center_l, start, ans, points_density, turn_right, (l, v1, v2, v3))
  else:
    # just fly direct
    return []

def go_dist_from(start: tuple[float, float], course: float, dist: float):
  dist /= EARTH_RAD
  start_xyz = to_xyz(*start)
  tangent = get_sphere_tangent(start, course)
  return to_latlon(start_xyz * cos(dist) + tangent * sin(dist))

def go_to_dme(start: tuple[float, float], course: float, ref: tuple[float, float], dme: float, alt: float = 0):
  dme_ft = dme * NM_TO_FT
  if alt > dme_ft: raise ValueError("Altitude was higher than the required DME distance.")
  
  w = to_xyz(*ref)
  # calculate the ground distance required to achieve a certain DME
  # note that this is an approximation
  d = sqrt(dme_ft*dme_ft - alt*alt) / NM_TO_FT
  d /= EARTH_RAD
  
  v1 = to_xyz(*start)
  v2 = get_sphere_tangent(start, course)
  
  # f(a) = v1 cos(a) + v2 sin(a)
  # want: f(a) dot w = cos(d)
  # v1 dot w cos(a) + v2 dot w sin(a) = cos(d)
  # k sin(a + c) = cos(d)
  v1r = v1.dot(w)
  v2r = v2.dot(w)
  k = sqrt(v1r * v1r + v2r * v2r)
  c = atan2(v1r, v2r)
  
  if abs(cos(d)) > k:
    raise ValueError("This DME can never be intersected.")
  rhs = asin(cos(d) / k)
  a1 = rhs
  a2 = pi - rhs
  ans1 = (a1 - c) % (2 * pi)
  ans2 = (a2 - c) % (2 * pi)
  
  ans = min(ans1, ans2)
  point = v1 * cos(ans) + v2 * sin(ans)
  
  return to_latlon(point)

def turn_from(
    start: PathPoint,
    inbd_crs: float,
    outbd_crs: float,
    turn_radius: float,
    points_density: int,
    turn_right: bool):
  # observation: when turning at a constant rate from a point, the center of the turning circle
  # will always be at a right angle to the current course, so we can find this center easily
  # by walking perpencidular to the current course, at a distance of the turning radius
  to_point = to_xyz(*start.latlon())
  tangent = get_sphere_tangent(start.latlon(), inbd_crs)
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
  l, v1, v2, v3 = get_turning_cirle(center, start.latlon(), turn_right)
  
  s = to_xyz(*start.latlon())
  dist = sqrt((s - l).mag2())
  
  assert(abs(inbd_crs - get_course(start.latlon(), v3)) < TOLERANCE)
  
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

  return get_arc_points_angle(center, start, ans, points_density, turn_right, (l, v1, v2, v3))

def waypoint_rad(fix: Waypoint) -> tuple[float, float]:
  return (fix.lat * pi / 180, fix.lon * pi / 180)

def to_xyz(lat: float, lon: float) -> Vec3:
  return Vec3(
    cos(lat) * cos(lon),
    cos(lat) * sin(lon),
    sin(lat)
  )

def to_xyz_earth(lat: float, lon: float, altitude: float) -> Vec3:
  radius = EARTH_RAD + (altitude / NM_TO_FT)
  # the order and sign is different to accomodate threejs
  return Vec3(
    radius * cos(lat) * cos(lon),
    radius * sin(lat),
    -radius * cos(lat) * sin(lon),
  )

def to_latlon(v: Vec3) -> tuple[float, float]:
  return (
    asin(v.z),
    atan2(v.y, v.x)
  )

def solve_matrix(lhs: list[list[float]], rhs: list[float]):
  pass
  #arr = np.array(lhs, np.float64)
  #arr = np.linalg.inv(arr)
  #sol = arr @ np.array(rhs, np.float64)
  #return Vec3(sol[0].item(), sol[1].item(), sol[2].item())
  
