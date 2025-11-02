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
  for i in range(len(cstrs)):
    a, b = cstrs[i]
    if not (a is None or b is None):
      # assert a <= b
      # some procedures are super weird and have an ascending leg
      # in this case just give up and let the "above" altitude take over
      cstrs[i] = (a, max(a, b))
    
  return cstrs

# points per revolution per radius
# i.e. a full revolution with radius 1nm will have POINT_DENSITY points
POINT_DENSITY = 32

# min radius for turning
MIN_RADIUS = 1

# maximum distance for intercept legs
MAX_INTC_DISTANCE = 128

# the radius used when turning due to a CI or VI leg
CI_RADIUS = 2

def build_points(legs: list[Leg], start_course: float | None, start_alt: float, ascending: bool):
  points: list[PathPoint] = []
  
  cstrs = build_alt_constr(legs, ascending)
  # print(list(zip([p.fix.name for p in legs], cstrs)))
  
  if start_course is None:
    cur_course = -1
  else:
    cur_course = start_course
  
  intercepting = False
  
  cur_alt = start_alt
  
  overfly = False
  
  def turn_dir(leg: Leg, target_course: float):
    if leg.info.turndir is None:
      right_diff = angle_between(cur_course, target_course, True)
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
  
  def to_fix_track(start: Waypoint, crs: float) -> list[PathPoint]:
    def giveup():
      # give up: just take the shortest route to the radial
      p = point_bisect_line(cur_latlon(), start.to_rad(), crs)
      req_crs = get_course_between(cur_latlon(), p)
      return [PathPoint(*p, req_crs)]
    
    course_diff = course_between(cur_course, crs)
    if cur_course == -1: return giveup()
    
    # If we are not already directly on the radial, we need to intersect it
    dist_to = point_dist_to_line(cur_latlon(), start.to_rad(), crs)
    
    # If a turn requires less than 2 degrees, don't bother
    if dist_to <= TOLERANCE and course_diff <= 2 * pi / 180: return []
    
    print(dist_to, course_diff)

    # Try to fly direct to the intersection
    intc = get_intersection(cur_latlon(), cur_course, start.to_rad(), crs)
    
    can_intc = True
    if overfly and course_diff >= 5 * pi / 180: can_intc = False
    if earth_distance(start.to_rad(), intc) > MAX_INTC_DISTANCE: can_intc = False
    
    if can_intc:
      # we can intersect
      return [PathPoint(*intc, cur_course)]
    else:
      # try to turn
      td = turn_dir(leg, crs)
      
      try:
        new_p = turn_to_course_towards(
          points[-1],
          cur_course,
          start.to_rad(),
          crs,
          MIN_RADIUS, POINT_DENSITY,
          td)
      except ValueError:
        try:
          # try again with the other turn dir
          new_p = turn_to_course_towards(
            points[-1],
            cur_course,
            start.to_rad(),
            crs,
            MIN_RADIUS, POINT_DENSITY,
            not td)
        except ValueError:
          return giveup()
      return new_p
  
  def course_between(c1: float, c2: float):
    return min(abs(c1 - c2), abs((c2 - c1)))
    
  def turn_to_crs(leg: Leg, crs: float) -> list[PathPoint]:
    td = turn_dir(leg, crs)
    if course_between(cur_course, crs) >= 0.5 * pi / 180:
      new_p = turn_from(points[-1], cur_course, crs, CI_RADIUS, POINT_DENSITY, td)
      return new_p
    return []
  
  
  # altitude building
  def build_altitudes():
    nonlocal points
  
  # Some approaches don't start with an IF
  # we need to manually add the first point
  match legs[0]:
    case HoldFix(_, start, _, course) \
        | FixToDistance(_, start, course, _) \
        | FixToDME(_, start, course, _, _) \
        | ProcTurn(_, start, _, course, _) :
      crs = to_mag(start.to_rad(), course)
      points.append(PathPoint(*start.to_rad(), crs, start_alt))
      cur_course = crs
    case _: pass
  
  for i, leg in enumerate(legs):
    print("-------")
    print(leg)
    print()
    match leg:
      case InitialFix(info, fix):
        if intercepting:
          intercepting = False
        else:
          points.append(PathPoint(*waypoint_rad(fix), cur_course, cur_alt))
          # auto_course()
      case TrackToFix(info, fix):
        req_crs = course_to(fix)
        td = turn_dir(leg, req_crs)
        new_p = to_fix_track(fix, req_crs)
        points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix)
        ))
        overfly = info.overfly
        auto_course()
      case CourseToFix(info, fix, course, _):
        crs = to_mag(cur_latlon(), course)
        td = turn_dir(leg, crs)
        new_p = to_fix_track(fix, crs)
        points += new_p

        # TODO: we can use this to assign points to the correct leg later
        # currently, all legs are part of the same path
        if intercepting:
          intercepting = False
          
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix)
        ))
        overfly = info.overfly
        cur_course = crs
        
      case DirectToFix(info, fix, _):
        req_crs = course_to(fix)
        td = turn_dir(leg, req_crs)
        if overfly:
          new_p = turn_towards(points[-1], cur_course, fix.to_rad(), MIN_RADIUS, POINT_DENSITY, td)
          points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix)
        ))
        auto_course()
        overfly = info.overfly
      case FixToAltitude(info, start, course, alt, _):
        if intercepting:
          intercepting = False
        raise NotImplementedError()
        pass
      case FixToDistance(info, start, course, dist):
        if intercepting:
          intercepting = False
        crs = to_mag(cur_latlon(), course)
        
        new_p = to_fix_track(start, crs)
        points += new_p
        
        dest_pt = go_dist_from(start.to_rad(), crs, dist)
        points.append(PathPoint(*dest_pt, crs))
        
        overfly = True
        cur_course = crs
        
      case FixToDME(info, start, course, ref, dme):
        if intercepting:
          intercepting = False
        crs = to_mag(cur_latlon(), course)
        points += to_fix_track(start, crs)
        
        dest_pt = go_to_dme(start.to_rad(), crs, ref.to_rad(), dme, 0)
        points.append(PathPoint(*dest_pt, crs))
        
        overfly = True
        cur_course = crs
        
      case FixToManual(info, start, course, _) | HeadingToManual(info, start, course):
        if intercepting:
          intercepting = False
        pass
        raise NotImplementedError()
      
      case CourseToAlt(info, course, alt) | HeadingToAlt(info, course, alt):
        raise NotImplementedError()
        pass
      case CourseToDME(info, course, ref, dme) | HeadingToDME(info, course, ref, dme):
        crs = to_mag(cur_latlon(), course)
        points += turn_to_crs(leg, crs)
        cur_course = crs
        
        dest_pt = go_to_dme(points[-1].latlon(), crs, ref.to_rad(), dme, cur_alt)
        points.append(PathPoint(*dest_pt, crs))
        
        overfly = True
        cur_course = crs
        
      case CourseToIntercept(info, course, _) | HeadingToIntercept(info, course, _):
        crs = to_mag(cur_latlon(), course)
        if overfly:
          points += turn_to_crs(leg, crs)
        cur_course = crs
        
        # Only AF, CF, FA, FC, FD, FM, IF legs can follow a CI leg
        next = legs[i + 1]
        match next:
          case ArcToFix(): pass
          case CourseToFix(): pass
          case FixToAltitude(): pass
          case FixToDistance(): pass
          case FixToDME(): pass
          case FixToManual(): pass
          case InitialFix(): pass
          case _: raise ValueError("Leg type " + leg.type_str() + " cannot follow a CI leg")
        pass
        
        cur_course = crs
        overfly = False
        intercepting = True
        
      case CourseToRadial(info, course, radial) | HeadingToRadial(info, course, radial):
        crs = to_mag(cur_latlon(), course)
        points += turn_to_crs(leg, crs)
        cur_course = crs
        
        ref = radial.fix.to_rad()
        rad = to_mag(ref, radial.rad)
        
        intc = get_intersection(points[-1].latlon(), crs, ref, rad)
        if earth_distance(points[-1].latlon(), intc) > MAX_INTC_DISTANCE:
          raise ValueError("Intersection distance too large")
        
        points.append(PathPoint(*intc, crs))
        overfly = True
        
      case RadiusArc(info, waypoint, center, dist):
        assert not (info.turndir is None)
        new_p = get_arc_between_points(
          center.to_rad(),
          points[-1],
          waypoint.to_rad(),
          POINT_DENSITY,
          info.turndir
        )
        points += new_p
        if new_p:
          cur_course = new_p[-1].course
        
        overfly = True
        
      case ArcToFix(info, fix, radial):
        assert not (info.turndir is None)
        
        if intercepting:
          intercepting = False
        
        ref = radial.fix.to_rad()
        dist = earth_distance(fix.to_rad(), ref)
        if abs(earth_distance(cur_latlon(), ref) - dist) > RF_TOLERANCE * EARTH_RAD:
          # intercept the arc
          intc = go_to_dme(cur_latlon(), cur_course, ref, dist)
          points.append(PathPoint(*intc, cur_course))
        
        new_p = get_arc_between_points(ref, points[-1], fix.to_rad(), POINT_DENSITY, info.turndir)
        points += new_p
        
        if new_p:
          cur_course = new_p[-1].course
        
        overfly = info.overfly
      case ProcTurn(info, fix, alt, course, max_dist):
        raise NotImplementedError()
        pass
      case HoldAlt(info, fix, alt, disttime, course):
        raise NotImplementedError()
        pass
      case HoldFix(info, fix, disttime, course):
        raise NotImplementedError()
        pass
      case HoldToManual(info, fix, disttime, course):
        raise NotImplementedError()
        pass

      case Leg(_): raise ValueError("Invalid leg")
  
  return points
