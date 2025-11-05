from server.navdata.defns import *
from server.navdata.mathhelpers import *
from server.navdata.point_builder import *

WIDTH = 500 / NM_TO_FT
HEIGHT = 250 / NM_TO_FT

@dataclass
class Object3D:
  vertices: list[Vec3]
  polygons: list[list[int]]
  
  def export_obj(self, file: str):
    with open(file, "w") as f:
      for v in self.vertices:
        f.write("v ")
        f.write("{:.5f} ".format(v.x))
        f.write("{:.5f} ".format(v.y))
        f.write("{:.5f}\n".format(v.z))
      for p in self.polygons:
        f.write("f")
        for i in p:
          f.write(" " + str(i))
        f.write("\n")

@dataclass
class Rect3D:
  top_left: Vec3
  top_right: Vec3
  bottom_right: Vec3
  bottom_left: Vec3

@dataclass
class SectionObject:
  start: Vec3
  end: Vec3
  
  tangent: Vec3 # points forward
  normal: Vec3 # points up
  binormal: Vec3 # tangent * normal, points rigt
  
  top: float # normal dot xyz = top
  left: float # binormal dot xyz = left
  bottom: float
  right: float
  
  start_rect: Rect3D

def compute_intersection(a: Vec3, b: Vec3, c: Vec3, x: float, y: float, z: float):
  mat = [a.as_arr(), b.as_arr(), c.as_arr()]
  rhs = [x, y, z]
  return solve_matrix(mat, rhs)

def make_section_obj(prev_sec: SectionObject | None, p1: Vec3, p2: Vec3) -> SectionObject:
  tangent = (p2 - p1).normalize()
  normal = (p1 + p2).normalize()
  normal = normal - tangent * tangent.dot(normal)
  binormal = tangent.cross(normal)
  
  top_left_point = p1 - binormal * WIDTH + normal * HEIGHT
  top_right_point = p1 + binormal * WIDTH + normal * HEIGHT
  bottom_right_point = p1 + binormal * WIDTH - normal * HEIGHT
  bottom_left_point = p1 - binormal * WIDTH - normal * HEIGHT
  
  top = top_left_point.dot(normal)
  left = top_left_point.dot(binormal)
  right = bottom_right_point.dot(binormal)
  bottom = bottom_right_point.dot(normal)
  
  def default_return():
    return SectionObject(
      p1, p2, tangent, normal, binormal, top, left, bottom, right, 
      Rect3D(top_left_point, top_right_point, bottom_right_point, bottom_left_point))
  if not prev_sec is None:
    try:
      tl = compute_intersection(normal, binormal, prev_sec.normal, top, left, prev_sec.top)
      tr = compute_intersection(normal, binormal, prev_sec.binormal, top, right, prev_sec.right)
      br = compute_intersection(normal, binormal, prev_sec.normal, bottom, right, prev_sec.bottom)
      bl = compute_intersection(normal, binormal, prev_sec.binormal, bottom, left, prev_sec.right)
      
      print(tl.dot(prev_sec.binormal) - prev_sec.left)
      
      return SectionObject(
        p1, p2, tangent, normal, binormal, top, left, bottom, right, 
        Rect3D(tl, tr, br, bl))
    except:
      return default_return()
  else:
    return default_return()
    

def build_3d(leg_points: list[tuple[Leg, list[PathPoint]]]):
  objs: list[tuple[Leg, tuple[list[SectionObject], Rect3D | None]]] = []
  
  prev: PathPoint | None = None
  for leg, points in leg_points:
    sections: list[SectionObject] = []
    for p in points:
      if prev is None:
        prev = p
        continue
      
      # note: I had to extract these to make pylance shut up
      lat, lon = prev.latlon()
      prev_xyz = to_xyz_earth(lat, lon, prev.altitude)
      xyz = to_xyz_earth(*p.latlon(), p.altitude)
      
      # TODO
      if sections:
        prev_sec = sections[-1]
      else:
        prev_sec = None
      
      if (prev_xyz - xyz).mag2() < 0.000001:
        prev = p
        continue
      
      section = make_section_obj(None, prev_xyz, xyz)
      sections.append(section)
      
      prev = p
    
    if not sections:
      objs.append((leg, (sections, None)))
      continue
    
    # endpoint
    last = sections[-1]
    tl = last.end - last.binormal * WIDTH + last.normal * HEIGHT
    tr = last.end + last.binormal * WIDTH + last.normal * HEIGHT
    br = last.end + last.binormal * WIDTH - last.normal * HEIGHT
    bl = last.end - last.binormal * WIDTH - last.normal * HEIGHT
    
    objs.append((leg, (sections, Rect3D(tl, tr, br, bl))))
  
  ret: list[tuple[Leg, Object3D]] = []
  
  for leg, (sections, last) in objs:
    if not last:
      ret.append((leg, Object3D([], [])))
      continue
    
    assert (len(sections) >= 1)
    
    obj = Object3D([], [])
    for i in range(len(sections)):
      s = sections[i]
      obj.vertices += [s.start_rect.top_left, s.start_rect.bottom_left, s.start_rect.bottom_right, s.start_rect.top_right]
      tl, bl, br, tr = 4*i + 1, 4*i + 2, 4*i + 3, 4*i + 4
      tln, bln, brn, trn = tl + 4, bl + 4, br + 4, tr + 4
      if i == 0:
        obj.polygons.append([tl, bl, br, tr])
      
      obj.polygons.append([tln, tl, tr, trn]) # top
      obj.polygons.append([tln, bln, bl, tl]) # left
      obj.polygons.append([bln, brn, br, bl]) # bottom
      obj.polygons.append([tr, br, brn, trn]) # right
    
    n = len(sections)
    tl, bl, br, tr = 4*n + 1, 4*n + 2, 4*n + 3, 4*n + 4
    
    obj.vertices += [last.top_left, last.bottom_left, last.bottom_right, last.top_right]
    obj.polygons.append([tl, tr, br, bl])
    
    ret.append((leg, obj))
  
  return ret
