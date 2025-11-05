from server.navdata.defns import *
from math import pi, tan
from server.navdata.mathhelpers import *

def build_alt_constr(legs: list[Leg], ascending: bool):
  aboves: list[float] = [-float('inf')] * len(legs)
  belows: list[float] = [float('inf')] * len(legs)
  
  cur_min: float = -float('inf')
  
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
    
    cur_max: float = float('inf')
    
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
    # some procedures are super weird and have an ascending leg
    # in this case just give up and let the "above" altitude take over
    cstrs[i] = (a, max(a, b))
  
  return cstrs

# points per revolution per radius
# i.e. a full revolution with radius 1nm will have POINT_DENSITY points
POINT_DENSITY = 32

# maximum distance for intercept legs
MAX_INTC_DISTANCE = 128

# the radius used when turning due to a CI or VI leg
CI_RADIUS = 2

def points_dist(points: list[PathPoint]):
  sm = 0
  for i in range(len(points) - 1):
    sm += earth_distance(points[i].latlon(), points[i + 1].latlon())
  return sm

def build_points(
    legs: list[Leg],
    config: AircraftConfig,
    start_point: Waypoint | None,
    start_course: float | None,
    start_alt: float,
    ascending: bool):
  leg_points: list[tuple[Leg, list[PathPoint]]] = []
  all_points: list[PathPoint] = []
  
  cstrs = build_alt_constr(legs, ascending)
  
  if start_course is None:
    cur_course = -1
  else:
    cur_course = start_course
  
  intercepting = False
  
  cur_alt = start_alt
  
  overfly = False
  
  points: list[PathPoint] = []
  
  def turn_dir(leg: Leg, target_course: float):
    if leg.info.turndir is None:
      right_diff = angle_between(cur_course, target_course, True)
      return right_diff < pi
    else:
      return leg.info.turndir
    
  def last_point():
    if points: return points[-1]
    return all_points[-1]
  
  def course_to(fix: Waypoint):
    return get_course_between(last_point().latlon(), fix.to_rad())
  
  def auto_course():
    nonlocal cur_course
    if len(points) == 1:
      p1 = points[-1]
      if len(all_points) == 0: return
      p2 = all_points[-1]
    elif len(points) >= 2:
      p1 = points[-1]
      p2 = points[-2]
    elif len(all_points) >= 2:
      p1 = all_points[-1]
      p2 = all_points[-2]
    else: return
      
    crs = get_course_between(p2.latlon(), p1.latlon())
    if crs != -1: cur_course = crs
    
  def cur_latlon():
    return last_point().latlon()
  
  def to_fix_track(leg: Leg, start: Waypoint, crs: float) -> list[PathPoint]:
    def giveup():
      if not overfly: return []
      # give up: just take the shortest route to the radial
      p = point_bisect_line(cur_latlon(), start.to_rad(), crs)
      req_crs = get_course_between(cur_latlon(), p)
      return [PathPoint(*p, req_crs)]
    
    course_diff = course_between(cur_course, crs)
    if cur_course == -1: return giveup()
    
    # If we are not already directly on the radial, we need to intersect it
    dist_to = point_dist_to_line(cur_latlon(), start.to_rad(), crs)
    
    # If a turn requires less than 2 degrees, don't bother
    if dist_to <= TOLERANCE and (not overfly or course_diff <= 2 * pi / 180): return []

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
          last_point(),
          cur_course,
          start.to_rad(),
          crs,
          config.min_turn_tadius, POINT_DENSITY,
          td)
      except Exception:
        if not (leg.info.turndir is None):
          return giveup()
        try:
          # try again with the other turn dir
          new_p = turn_to_course_towards(
            last_point(),
            cur_course,
            start.to_rad(),
            crs,
            config.min_turn_tadius, POINT_DENSITY,
            not td)
        except Exception:
          return giveup()
      return new_p
  
  def course_between(c1: float, c2: float):
    return min(abs(c1 - c2), abs((c2 - c1)))
    
  def turn_to_crs(leg: Leg, crs: float) -> list[PathPoint]:
    if cur_course == -1: return []
    
    td = turn_dir(leg, crs)
    if course_between(cur_course, crs) >= 2 * pi / 180:
      new_p = turn_from(last_point(), cur_course, crs, CI_RADIUS, POINT_DENSITY, td)
      return new_p
    return []
  
  def append_leg(idx: int):
    nonlocal leg_points, intercepting, points, all_points, cur_alt
    
    leg = legs[idx]
    
    if points and points[-1].altitude == float('-inf'):
      above, below = cstrs[idx]
      if leg.info.glide_angle is None:
        if ascending: grad = config.climb_grad
        else: grad = -config.descent_grad
      else:
        grad = tan(leg.info.glide_angle * pi / 180)
      
      
      if all_points and points:
        initial_dist = earth_distance(all_points[-1].latlon(), points[0].latlon())
      else:
        initial_dist = 0
      
      dist = initial_dist
      total_dist = points_dist(points) + dist
      target_alt = min(below, max(above, cur_alt + grad * total_dist * NM_TO_FT))

      if ascending:
        grad = max(grad, (target_alt - cur_alt) / (total_dist * NM_TO_FT))
      else:
        grad = min(grad, (target_alt - cur_alt) / (total_dist * NM_TO_FT))
      
      for i, p in enumerate(points):
        if i > 0:
          dist += earth_distance(points[i - 1].latlon(), points[i].latlon())
        if ascending:
          alt = min(below, cur_alt + grad * dist * NM_TO_FT)
        else:
          alt = max(above, cur_alt + grad * dist * NM_TO_FT)
        p.altitude = alt
      
      cur_alt = target_alt
    
    leg_points.append((leg, points))
    all_points += points
    points = []
    
  def flush_intercept(idx: int):
    nonlocal intercepting
    if intercepting:
      intercepting = False
      append_leg(idx - 1)

  
  # Some approaches don't start with an IF
  # we need to manually add the first point
  if start_point is None:
    match legs[0]:
      case HoldFix(_, start, _, course) \
          | FixToDistance(_, start, course, _) \
          | FixToAltitude(_, start, course, _) \
          | FixToDME(_, start, course, _, _) \
          | ProcTurn(_, start, _, course, _) :
        crs = to_mag(start.to_rad(), course)
        pnt = PathPoint(*start.to_rad(), crs, start_alt)
        points.append(pnt)
        all_points.append(pnt)
        cur_course = crs
      case _: pass
  else:
    pnt = PathPoint(*start_point.to_rad(), cur_course, start_alt)
    points.append(pnt)
    all_points.append(pnt)
  
  for i, leg in enumerate(legs):
    match leg:
      case InitialFix(info, fix):
        if not intercepting:
          points.append(PathPoint(*waypoint_rad(fix), cur_course, cur_alt))
          auto_course()
      case TrackToFix(info, fix):
        req_crs = course_to(fix)
        td = turn_dir(leg, req_crs)
        new_p = to_fix_track(leg, fix, req_crs)
        points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix)
        ))
        overfly = info.overfly
        cur_course = req_crs
      case CourseToFix(info, fix, course, _):
        crs = to_mag(cur_latlon(), course)
        td = turn_dir(leg, crs)
        new_p = to_fix_track(leg, fix, crs)
        points += new_p

        flush_intercept(i)
          
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix)
        ))
        overfly = info.overfly
        cur_course = crs
        
      case DirectToFix(info, fix, _):
        req_crs = course_to(fix)
        td = turn_dir(leg, req_crs)
        if overfly:
          new_p = turn_towards(last_point(), cur_course, fix.to_rad(), config.min_turn_tadius, POINT_DENSITY, td)
          points += new_p
        points.append(PathPoint(
          *fix.to_rad(), course_to(fix)
        ))
        auto_course()
        overfly = info.overfly
      case FixToAltitude(info, start, course, alt, _):
        
        crs = to_mag(cur_latlon(), course)
        new_p = to_fix_track(leg, start, crs)
        points += new_p
    
        flush_intercept(i)
        
        assert ascending
        
        prev = last_point()
        
        if new_p:
          initial_dist = earth_distance(cur_latlon(), new_p[0].latlon())
          prev = new_p[-1]
        else:
          initial_dist = 0
        
        total_dist = initial_dist + points_dist(points)
        
        grad = config.climb_grad
        diff = alt - cur_alt
        
        cur_course = crs
        overfly = info.overfly
        
        if diff >= 0:
          total_dist = 0

          req_dist = diff / (grad * NM_TO_FT)
          dist = req_dist - total_dist
          
          if dist >= 0:
            dest = go_dist_from(prev.latlon(), crs, dist)
            points.append(PathPoint(*dest, crs))
        
          overfly = True
        
      case FixToDistance(info, start, course, dist):
        crs = to_mag(cur_latlon(), course)
        
        new_p = to_fix_track(leg, start, crs)
        points += new_p
        
        flush_intercept(i)
        
        dest_pt = go_dist_from(start.to_rad(), crs, dist)
        points.append(PathPoint(*dest_pt, crs))
        
        overfly = True
        cur_course = crs
        
      case FixToDME(info, start, course, ref, dme):
        crs = to_mag(cur_latlon(), course)
        points += to_fix_track(leg, start, crs)
        
        flush_intercept(i)
        
        dest_pt = go_to_dme(start.to_rad(), crs, ref.to_rad(), dme, cur_alt)
        points.append(PathPoint(*dest_pt, crs))
        
        overfly = True
        cur_course = crs
        
      case FixToManual(info, start, course, _) | HeadingToManual(info, start, course):
        crs = to_mag(cur_latlon(), course)
        if not start is None:
          points += to_fix_track(leg, start, crs)
        else:
          points += turn_to_crs(leg, crs)
        
        flush_intercept(i)
        
        overfly = False
        cur_course = crs
      
      case CourseToAlt(info, course, alt) | HeadingToAlt(info, course, alt):
        assert ascending
        
        crs = to_mag(cur_latlon(), course)
        
        grad = config.climb_grad
        
        diff = alt - cur_alt
        
        if diff >= 0:
          total_dist = 0
          prev = last_point()
          if overfly:
            new_p = turn_to_crs(leg, crs)
            points += new_p
            
            if new_p:
              initial_dist = earth_distance(cur_latlon(), new_p[0].latlon())
              prev = new_p[-1]
            else:
              initial_dist = 0
            
            total_dist = initial_dist + points_dist(points)
          
          req_dist = diff / (grad * NM_TO_FT)
          dist = req_dist - total_dist
          
          cur_course = crs
          overfly = info.overfly
          
          if dist >= 0:
            dest = go_dist_from(prev.latlon(), crs, dist)
            points.append(PathPoint(*dest, crs))
          overfly = True
          
      case CourseToDME(info, course, ref, dme) | HeadingToDME(info, course, ref, dme):
        crs = to_mag(cur_latlon(), course)
        points += turn_to_crs(leg, crs)
        cur_course = crs
        
        dest_pt = go_to_dme(last_point().latlon(), crs, ref.to_rad(), dme, cur_alt)
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
        
        intc = get_intersection(last_point().latlon(), crs, ref, rad)
        if earth_distance(last_point().latlon(), intc) > MAX_INTC_DISTANCE:
          raise ValueError("Intersection distance too large")
        
        points.append(PathPoint(*intc, crs))
        overfly = True
        cur_course = crs
        
      case RadiusArc(info, waypoint, center, dist):
        assert not (info.turndir is None)
        new_p = get_arc_between_points(
          center.to_rad(),
          last_point(),
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
        
        ref = radial.fix.to_rad()
        dist = earth_distance(fix.to_rad(), ref)
        if abs(earth_distance(cur_latlon(), ref) - dist) > RF_TOLERANCE * EARTH_RAD:
          # intercept the arc
          intc = go_to_dme(cur_latlon(), cur_course, ref, dist)
          points.append(PathPoint(*intc, cur_course))
        
        flush_intercept(i)
        
        new_p = get_arc_between_points(ref, last_point(), fix.to_rad(), POINT_DENSITY, info.turndir)
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
        # raise NotImplementedError()
        points.append(PathPoint(*waypoint_rad(fix), cur_course, cur_alt))
        auto_course()
        pass
      case HoldToManual(info, fix, disttime, course):
        raise NotImplementedError()
        pass

      case Leg(_): raise ValueError("Invalid leg")
    
    if not intercepting:
      append_leg(i)
  return leg_points
