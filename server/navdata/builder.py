from server.navdata.defns import *
from pygeomag import GeoMag
from math import pi
from server.navdata.mathhelpers import *

def build_alt_constr(legs: list[Leg], ascending: bool):
  aboves: list[int | None] = [None] * len(legs)
  belows: list[int | None] = [None] * len(legs)
  
  cur_min: int | None = None
  
  above_iter = legs if ascending else reversed(legs)
  below_iter = reversed(legs) if ascending else legs
  
  for i, leg in enumerate(above_iter):
    match leg.info.alt:
      case None: pass
      case AtAlt(at) | StepDownAt(at):
        cur_min = at
      case AltRange(above, below):
        if not above is None: cur_min = above
      case GlideslopeAlt(_, alt, is_above) | GlideslopeIntc(_, alt, is_above):
        cur_min = alt
      case StepDownAboveBelow(alt, _, is_above):
        if is_above:
          cur_min = alt
      case AltRestr(): pass
    
    if ascending:
      aboves[i] = cur_min
    else:
      aboves[len(legs) - i - 1] = cur_min
    
    cur_max: int | None = None
    
    for i, leg in enumerate(below_iter):
      match leg.info.alt:
        case None: pass
        case AtAlt(at) | StepDownAt(at):
          cur_max = at
        case AltRange(above, below):
          if not below is None: cur_max = below
        case StepDownAboveBelow(alt, _, is_above):
          if not is_above:
            cur_max = alt
        case AltRestr(): pass
      
      if ascending:
        belows[len(legs) - i - 1] = cur_max
      else:
        belows[i] = cur_max
  
  cstrs = list(zip(aboves, belows))
  for a, b in cstrs:
    if not (a is None or b is None):
      assert a <= b

  return cstrs

def build_points(legs: list[Leg], start_course: float | None, start_alt: float, ascending: bool):
  points: list[PathPoint] = []
  
  cstrs = build_alt_constr(legs, ascending)
  # print(list(zip([p.fix.name for p in legs], cstrs)))
  
  if start_course is None:
    cur_course = -1
  else:
    cur_course = start_course
  
  cur_alt = start_alt
  
  overfly = False
  
  def turn_dir(leg: Leg, target_course: float):
    if leg.info.turndir is None:
      right_diff = (target_course - cur_course) % pi
      return right_diff < pi
    else:
      return leg.info.turndir
  
  def course_to(fix: Waypoint):
    return get_course_between(points[-1].latlon(), fix.to_rad())
  
  def auto_course():
    nonlocal cur_course
    if len(points) >= 2:
      crs = get_course_between(points[-2].latlon(), points[-1].latlon())
      if crs != -1: cur_course = crs
    
  def cur_latlon():
    return points[-1].latlon()
  

  # points per revolution per radius
  # i.e. a full revolution with radius 1nm will have POINT_DENSITY points
  POINT_DENSITY = 256
  MIN_RADIUS = 1
  for i, leg in enumerate(legs):
    match leg:
      case InitialFix(info, fix):
        points.append(PathPoint(*waypoint_rad(fix), cur_course, cur_alt))
        auto_course()
      case TrackToFix(info, fix):
        req_crs = course_to(fix)
        td = turn_dir(leg, req_crs)
        if overfly:
          new_p = turn_to_course_towards(points[-1], cur_course, fix.to_rad(), req_crs, MIN_RADIUS, POINT_DENSITY, td)
          points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix), -1
        ))
        overfly = info.overfly
        auto_course()
      case CourseToFix(info, fix, course, _):
        crs = to_mag(cur_latlon(), course)
        td = turn_dir(leg, crs)
        new_p = turn_to_course_towards(points[-1], cur_course, fix.to_rad(), crs, MIN_RADIUS, POINT_DENSITY, td)
        points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix), -1
        ))
        overfly = info.overfly
        auto_course()
      case DirectToFix(info, fix, _):
        req_crs = course_to(fix)
        td = turn_dir(leg, req_crs)
        if overfly:
          new_p = turn_towards(points[-1], cur_course, fix.to_rad(), MIN_RADIUS, POINT_DENSITY, td)
          points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix), -1
        ))
        auto_course()
      case FixToAltitude(info, start, course, alt, _):
        raise NotImplementedError()
        pass
      case FixToDistance(info, start, course, dist):
        crs = to_mag(cur_latlon(), course)
        if (to_xyz(*points[-1].latlon()) - to_xyz(*start.to_rad())).mag2() >= TOLERANCE:
          
          pass
      case FixToDME(info, start, course, ref, dist):
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

      case Leg(_): raise ValueError("Invalid leg")
  
  return points
