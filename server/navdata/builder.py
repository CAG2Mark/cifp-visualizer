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
  print(list(zip([p.fix.name for p in legs], cstrs)))
  
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

  # points per revolution per radius
  # i.e. a full revolution with radius 1nm will have POINT_DENSITY points
  POINT_DENSITY = 256
  for i, leg in enumerate(legs):
    match leg:
      case InitialFix(info, fix):
        points.append(PathPoint(*waypoint_rad(fix), cur_course, cur_alt))
      case TrackToFix(info, fix):
        if overfly:
          turn_towards(points[-1], cur_course, fix.to_rad(), 1, POINT_DENSITY, False)
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
