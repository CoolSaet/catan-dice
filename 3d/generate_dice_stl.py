#!/usr/bin/env python3
"""
generate_dice_stl.py  –  Procedural STL generator for the Catan-Dice housing.

Produces  dice.stl  and  dice_lid.stl  in the same directory.

Geometry overview
-----------------
A 50 mm rounded-corner cube shell houses a Wemos D1 Mini (34.2 × 25.6 mm).

  TOP    (+Z) : face 1  –  push-button hole (Ø 13 mm) centred
  BOTTOM (−Z) : face 6  –  toggle-switch slot (10 × 5.5 mm)
  FRONT  (+Y) : face 2
  BACK   (−Y) : face 5  –  open slot for PCB insertion + snap-fit lid
  RIGHT  (+X) : face 3
  LEFT   (−X) : face 4

The rounded corners are approximated by bevelling each edge/corner with a
sphere-swept Minkowski sum, implemented here as a triangulated mesh built
directly from a CSG description evaluated with pycsg (pure-Python CSG) and
exported via numpy-stl.

Dependencies:  pip install numpy numpy-stl pycsg
"""

import math
import os
import sys
import numpy as np

try:
    from stl import mesh as stl_mesh
except ImportError:
    sys.exit("numpy-stl not found.  Run:  pip install numpy-stl")

# ---------------------------------------------------------------------------
# Tiny polygon-mesh builder
# ---------------------------------------------------------------------------

class Mesh:
    """Accumulate triangles and export as STL."""

    def __init__(self):
        self.tris = []   # list of (v0, v1, v2)  –  each v is (x,y,z)

    def add_tri(self, v0, v1, v2):
        self.tris.append((np.array(v0, dtype=float),
                          np.array(v1, dtype=float),
                          np.array(v2, dtype=float)))

    def add_quad(self, v0, v1, v2, v3):
        """Two triangles, CCW winding looking from outside."""
        self.add_tri(v0, v1, v2)
        self.add_tri(v0, v2, v3)

    def save(self, path):
        data = np.zeros(len(self.tris),
                        dtype=stl_mesh.Mesh.dtype)
        for i, (v0, v1, v2) in enumerate(self.tris):
            data["vectors"][i] = [v0, v1, v2]
        m = stl_mesh.Mesh(data)
        m.save(path)
        print(f"Saved {path}  ({len(self.tris)} triangles)")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def circle_pts(n, r, phase=0.0):
    """n points on a circle of radius r in the XY plane."""
    return [(r * math.cos(2 * math.pi * i / n + phase),
             r * math.sin(2 * math.pi * i / n + phase),
             0.0)
            for i in range(n)]


def tube(m: Mesh, pts_bot, pts_top, close_bot=False, close_top=False, flip=False):
    """Build a tube (cylinder wall) from two rings of equal length."""
    n = len(pts_bot)
    for i in range(n):
        j = (i + 1) % n
        b0, b1 = pts_bot[i], pts_bot[j]
        t0, t1 = pts_top[i], pts_top[j]
        if flip:
            m.add_quad(t0, b0, b1, t1)
        else:
            m.add_quad(b0, t0, t1, b1)
    if close_bot:
        for i in range(1, n - 1):
            if flip:
                m.add_tri(pts_bot[0], pts_bot[i + 1], pts_bot[i])
            else:
                m.add_tri(pts_bot[0], pts_bot[i], pts_bot[i + 1])
    if close_top:
        for i in range(1, n - 1):
            if flip:
                m.add_tri(pts_top[0], pts_top[i], pts_top[i + 1])
            else:
                m.add_tri(pts_top[0], pts_top[i + 1], pts_top[i])


def translate(pts, dx=0, dy=0, dz=0):
    return [(x + dx, y + dy, z + dz) for x, y, z in pts]


def rotX(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(x, c*y - s*z, s*y + c*z) for x, y, z in pts]


def rotY(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(c*x + s*z, y, -s*x + c*z) for x, y, z in pts]


def rotZ(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(c*x - s*y, s*x + c*y, z) for x, y, z in pts]


# ---------------------------------------------------------------------------
# Flat face helpers
# ---------------------------------------------------------------------------

def flat_face_with_holes(m: Mesh, size, z, holes, flip=False, seg=32):
    """
    Square face at height z, with circular or rectangular holes cut out.
    holes: list of dicts with keys:
        {'type': 'circle', 'x': ..., 'y': ..., 'r': ...}
        {'type': 'rect',   'x': ..., 'y': ..., 'w': ..., 'h': ...}

    Strategy: build a 2-D polygon with holes, triangulate with fan.
    For simplicity we use a coarse outer polygon + inner polygons and
    connect them via bridge edges (this is the "bridge cut" approach).
    """
    half = size / 2

    # outer border, CCW when viewed from +Z
    outer = [(-half, -half), ( half, -half), ( half,  half), (-half,  half)]

    def add_flat_quad(ax, ay, bx, by, cx, cy, dx, dy):
        if flip:
            m.add_quad((ax,ay,z),(dx,dy,z),(cx,cy,z),(bx,by,z))
        else:
            m.add_quad((ax,ay,z),(bx,by,z),(cx,cy,z),(dx,dy,z))

    if not holes:
        # plain square
        add_flat_quad(-half,-half, half,-half, half,half, -half,half)
        return

    # For each hole, we carve a polygon and bridge to the outer square.
    # Here we use a simpler approach: draw the face as many quads
    # arranged in a grid, skipping cells that overlap holes.
    N = 40  # grid resolution
    step = size / N

    def in_hole(cx, cy):
        for h in holes:
            if h['type'] == 'circle':
                if (cx - h['x'])**2 + (cy - h['y'])**2 <= h['r']**2:
                    return True
            elif h['type'] == 'rect':
                if (abs(cx - h['x']) <= h['w']/2 and
                        abs(cy - h['y']) <= h['h']/2):
                    return True
        return False

    for ix in range(N):
        for iy in range(N):
            x0 = -half + ix * step
            y0 = -half + iy * step
            x1, y1 = x0 + step, y0 + step
            # Use centre of cell to decide
            if in_hole((x0+x1)/2, (y0+y1)/2):
                continue
            add_flat_quad(x0,y0, x1,y0, x1,y1, x0,y1)


def add_cylinder_shell(m: Mesh, cx, cy, z_bot, z_top, r, seg=32, flip=False):
    """Hollow cylinder (just the wall) standing along Z."""
    pts_bot = [(cx + r*math.cos(2*math.pi*i/seg),
                cy + r*math.sin(2*math.pi*i/seg),
                z_bot) for i in range(seg)]
    pts_top = [(cx + r*math.cos(2*math.pi*i/seg),
                cy + r*math.sin(2*math.pi*i/seg),
                z_top) for i in range(seg)]
    tube(m, pts_bot, pts_top, flip=flip)


def add_rect_shell(m: Mesh, cx, cy, z_bot, z_top, w, h, flip=False):
    """Rectangular tube wall."""
    hw, hh = w/2, h/2
    corners = [(cx-hw,cy-hh), (cx+hw,cy-hh), (cx+hw,cy+hh), (cx-hw,cy+hh)]
    pb = [(x, y, z_bot) for x,y in corners]
    pt = [(x, y, z_top) for x,y in corners]
    tube(m, pb, pt, flip=flip)


# ---------------------------------------------------------------------------
# Die dimensions
# ---------------------------------------------------------------------------

OUTER  = 50.0          # outer edge
WALL   = 3.0           # wall thickness
CORNER = 5.0           # bevel rounding (approximated as chamfer)
INNER  = OUTER - 2*WALL

HALF   = OUTER / 2
IHALF  = INNER / 2

BTN_R  = 6.5           # push button hole radius
SW_W   = 10.0          # switch slot width
SW_H   = 5.5           # switch slot height
SW_OY  = -OUTER*0.22   # switch offset toward back

PIP_R  = 2.5           # pip hole radius
PIP_D  = 1.2           # pip depth
S      = OUTER * 0.22  # pip grid step


# ---------------------------------------------------------------------------
# Rounded box – approximated by chamfering 12 edges (no sphere corners here,
# but good enough for FDM printing).  We build each of the 6 outer panels
# independently, then add thin chamfer strips at edges.
# ---------------------------------------------------------------------------

def chamfer_box(m: Mesh, size, chamfer, flip=False):
    """
    Closed rounded box, approximated by trimming each edge with a 45° bevel.
    size: total outer dimension (cube is centred at origin)
    chamfer: width of bevel strip
    """
    h = size / 2
    c = chamfer
    inner_h = h - c   # where face panels stop

    # Face normals and their local coordinate systems
    # We draw each face as a 2D polygon and transform it.

    def face(ax, ay, az,            # 4 corners in local space
             bx, by, bz,
             cx, cy, cz,
             dx, dy, dz):
        if flip:
            m.add_quad((ax,ay,az),(dx,dy,dz),(cx,cy,cz),(bx,by,bz))
        else:
            m.add_quad((ax,ay,az),(bx,by,bz),(cx,cy,cz),(dx,dy,dz))

    ih = inner_h

    # Top (+Z)
    face(-ih,-ih, h,   ih,-ih, h,   ih, ih, h,  -ih, ih, h)
    # Bottom (-Z)
    face(-ih,-ih,-h,  -ih, ih,-h,   ih, ih,-h,   ih,-ih,-h)
    # Front (+Y)
    face(-ih, h,-ih,  -ih, h, ih,   ih, h, ih,   ih, h,-ih)
    # Back (-Y)
    face(-ih,-h,-ih,   ih,-h,-ih,   ih,-h, ih,  -ih,-h, ih)
    # Right (+X)
    face( h,-ih,-ih,   h, ih,-ih,   h, ih, ih,   h,-ih, ih)
    # Left (-X)
    face(-h,-ih,-ih,  -h,-ih, ih,  -h, ih, ih,  -h, ih,-ih)

    # 12 edge chamfer strips (2 tris each)
    # Edges parallel to Z
    for sx, sy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
        x0 = sx*ih; y0 = sy*ih
        x1 = sx*h;  y1 = sy*ih
        x2 = sx*ih; y2 = sy*h
        if sx*sy > 0:  # +x+y  or  -x-y
            if flip:
                face(x0,y0,-ih, x1,y1,-ih, x1,y1, ih, x0,y0, ih)
                face(x0,y0,-ih, x0,y0, ih, x2,y2, ih, x2,y2,-ih)
            else:
                face(x0,y0,-ih, x0,y0, ih, x1,y1, ih, x1,y1,-ih)
                face(x0,y0,-ih, x2,y2,-ih, x2,y2, ih, x0,y0, ih)
        else:  # +x-y  or  -x+y
            if flip:
                face(x0,y0,-ih, x0,y0, ih, x1,y1, ih, x1,y1,-ih)
                face(x0,y0,-ih, x2,y2,-ih, x2,y2, ih, x0,y0, ih)
            else:
                face(x0,y0,-ih, x1,y1,-ih, x1,y1, ih, x0,y0, ih)
                face(x0,y0,-ih, x0,y0, ih, x2,y2, ih, x2,y2,-ih)

    # 8 corner triangles (connecting three face-strips at each corner)
    for sx, sy, sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                        (-1,-1, 1),(1,-1, 1),(1,1, 1),(-1,1, 1)]:
        ax = sx*h;  ay = sy*ih; az = sz*ih
        bx = sx*ih; by = sy*h;  bz = sz*ih
        cx = sx*ih; cy = sy*ih; cz = sz*h
        if flip:
            m.add_tri((ax,ay,az),(cx,cy,cz),(bx,by,bz))
        else:
            m.add_tri((ax,ay,az),(bx,by,bz),(cx,cy,cz))


# ---------------------------------------------------------------------------
# Pip (spherical indent on a face)
# ---------------------------------------------------------------------------

def add_pip(m: Mesh, face_normal, cx, cy, r=PIP_R, depth=PIP_D, seg=24):
    """
    Add a dome-shaped indent (hemisphere) on the given face.
    face_normal: one of '+z','-z','+y','-y','+x','-x'
    cx, cy: position in the local face coordinate system.
    """
    half = HALF
    # Build hemisphere pointing inward (normals outward = INTO die)
    pts = []
    rings = 8
    for ir in range(rings + 1):
        lat = math.pi / 2 * ir / rings   # 0 = equator, pi/2 = pole
        rr = r * math.cos(lat)
        zz = depth * math.sin(lat)
        ring = [(rr * math.cos(2*math.pi*j/seg),
                 rr * math.sin(2*math.pi*j/seg),
                 zz) for j in range(seg)]
        pts.append(ring)

    # Transform into face coordinates
    def xf(x, y, z):
        # z goes INTO the face (subtract from face position)
        if face_normal == '+z':
            return (cx + x, cy + y, half - z)
        if face_normal == '-z':
            return (cx + x, cy - y, -half + z)
        if face_normal == '+y':
            return (cx + x, half - z, cy + y)
        if face_normal == '-y':
            return (cx - x, -half + z, cy + y)
        if face_normal == '+x':
            return (half - z, cx + x, cy + y)
        if face_normal == '-x':
            return (-half + z, cx - x, cy + y)

    # Cap (equator ring already exists as pts[0])
    # Tube rings
    for ir in range(rings):
        ring0 = [xf(*p) for p in pts[ir]]
        ring1 = [xf(*p) for p in pts[ir + 1]]
        if ir < rings - 1:
            tube(m, ring0, ring1, flip=True)
        else:
            # Last ring → pole (single point)
            pole = xf(0, 0, depth)
            for j in range(seg):
                jn = (j + 1) % seg
                m.add_tri(ring0[j], pole, ring0[jn])

    # Close equator disk (fill the mouth of the indent)
    equator = [xf(*p) for p in pts[0]]
    for j in range(1, seg - 1):
        m.add_tri(equator[0], equator[j + 1], equator[j])


# ---------------------------------------------------------------------------
# Standard pip positions for each face
# ---------------------------------------------------------------------------

def pips_for_face(n, face_normal):
    """Return list of (cx,cy) pip positions for die face 1-6."""
    positions = {
        1: [(0, 0)],
        2: [(-S, S), (S, -S)],
        3: [(-S, S), (0, 0), (S, -S)],
        4: [(-S, S), (S, S), (-S, -S), (S, -S)],
        5: [(-S, S), (S, S), (0, 0), (-S, -S), (S, -S)],
        6: [(-S, S), (S, S), (-S, 0), (S, 0), (-S, -S), (S, -S)],
    }
    return positions[n]


# ---------------------------------------------------------------------------
# Build the die
# ---------------------------------------------------------------------------

def build_die():
    m = Mesh()

    # ── Outer shell ──────────────────────────────────────────────────────────
    chamfer_box(m, OUTER, CORNER)

    # ── Inner cavity (inverted shell = remove material) ───────────────────
    # We model the shell by SUBTRACTING a smaller box.
    # numpy-stl doesn't support CSG – so we build the shell walls explicitly.

    # The shell is the space between outer box and inner box.
    # We build it as 6 flat face slabs + walls using inner-face panels.

    # Inner box (flip=True → normals point INWARD)
    # But we only need the inner *walls* (not a closed inner box) because the
    # top/bottom/side inner faces are the interior of each die face panel.
    # Strategy: build each face as an annular slab (outer polygon minus inner
    # polygon), then add the four thin sidewall quads connecting outer to inner.

    # We use the grid-based flat_face_with_holes for each face.

    # ── BOTTOM FACE (−Z, face 6) – toggle switch slot ─────────────────────
    flat_face_with_holes(m, OUTER, -HALF, flip=True,
                         holes=[{'type': 'rect',
                                 'x': 0, 'y': SW_OY,
                                 'w': SW_W, 'h': SW_H}])
    # inner bottom
    flat_face_with_holes(m, INNER, -HALF + WALL, flip=False,
                         holes=[{'type': 'rect',
                                 'x': 0, 'y': SW_OY,
                                 'w': SW_W, 'h': SW_H}])
    # switch hole walls
    add_rect_shell(m, 0, SW_OY, -HALF, -HALF + WALL, SW_W, SW_H, flip=False)
    # inner walls (bottom rim connecting outer bottom to inner bottom)
    # These are the sides of the bottom slab:
    for x0, y0, x1, y1 in [
        (-IHALF,-IHALF, IHALF,-IHALF),
        ( IHALF,-IHALF, IHALF, IHALF),
        ( IHALF, IHALF,-IHALF, IHALF),
        (-IHALF, IHALF,-IHALF,-IHALF),
    ]:
        m.add_quad((x0,y0,-HALF+WALL),(x0,y0,-HALF),
                   (x1,y1,-HALF),(x1,y1,-HALF+WALL))

    # ── TOP FACE (+Z, face 1) – button hole (no pip, replaced by button) ──
    flat_face_with_holes(m, OUTER, HALF, flip=False,
                         holes=[{'type': 'circle', 'x': 0, 'y': 0, 'r': BTN_R}])
    # inner top
    flat_face_with_holes(m, INNER, HALF - WALL, flip=True,
                         holes=[{'type': 'circle', 'x': 0, 'y': 0, 'r': BTN_R}])
    # button hole cylinder wall
    add_cylinder_shell(m, 0, 0, HALF - WALL, HALF, BTN_R, flip=True)
    # inner walls (top rim)
    for x0, y0, x1, y1 in [
        (-IHALF,-IHALF, IHALF,-IHALF),
        ( IHALF,-IHALF, IHALF, IHALF),
        ( IHALF, IHALF,-IHALF, IHALF),
        (-IHALF, IHALF,-IHALF,-IHALF),
    ]:
        m.add_quad((x0,y0,HALF-WALL),(x1,y1,HALF-WALL),
                   (x1,y1,HALF),(x0,y0,HALF))

    # ── SIDE FACES (+Y face2, +X face3, −X face4, −Y face5) ──────────────
    # Face 5 (back, −Y) has the PCB opening.  We make it mostly open
    # but leave a frame so the snap-fit lid has something to seat on.
    FRAME = WALL  # frame width around the opening

    def side_face(face_normal, pip_n, has_opening=False):
        """Build outer+inner panels and inner wall for one side face."""
        # Map face_normal to orientation
        if face_normal == '+y':
            flip_outer, flip_inner = False, True
            def out_face(pts_2d, z_val):
                return [(x, HALF, y) for x,y in pts_2d]
            def in_face(pts_2d, z_val):
                return [(x, HALF-WALL, y) for x,y in pts_2d]
            def rim_quad(x0,z0,x1,z1):
                m.add_quad((x0,HALF-WALL,z0),(x1,HALF-WALL,z1),
                           (x1,HALF,z1),(x0,HALF,z0))
        elif face_normal == '-y':
            flip_outer, flip_inner = True, False
            def out_face(pts_2d, z_val):
                return [(x,-HALF, y) for x,y in pts_2d]
            def in_face(pts_2d, z_val):
                return [(x,-HALF+WALL, y) for x,y in pts_2d]
            def rim_quad(x0,z0,x1,z1):
                m.add_quad((x0,-HALF,z0),(x1,-HALF,z1),
                           (x1,-HALF+WALL,z1),(x0,-HALF+WALL,z0))
        elif face_normal == '+x':
            flip_outer, flip_inner = True, False
            def out_face(pts_2d, z_val):
                return [(HALF, x, y) for x,y in pts_2d]
            def in_face(pts_2d, z_val):
                return [(HALF-WALL, x, y) for x,y in pts_2d]
            def rim_quad(x0,z0,x1,z1):
                m.add_quad((HALF,x0,z0),(HALF,x1,z1),
                           (HALF-WALL,x1,z1),(HALF-WALL,x0,z0))
        elif face_normal == '-x':
            flip_outer, flip_inner = False, True
            def out_face(pts_2d, z_val):
                return [(-HALF, x, y) for x,y in pts_2d]
            def in_face(pts_2d, z_val):
                return [(-HALF+WALL, x, y) for x,y in pts_2d]
            def rim_quad(x0,z0,x1,z1):
                m.add_quad((-HALF+WALL,x0,z0),(-HALF+WALL,x1,z1),
                           (-HALF,x1,z1),(-HALF,x0,z0))

        N = 40; step = OUTER / N; half = HALF; ihalf = IHALF

        if has_opening:
            # Opening is INNER×INNER centred, leaving a FRAME-wide border
            frame = FRAME
            opening = {'type': 'rect', 'x': 0, 'y': 0,
                       'w': INNER - 2*frame, 'h': INNER - 2*frame}
            holes_outer = [opening]
            holes_inner = [opening]
        else:
            holes_outer = []
            holes_inner = []

        # Build outer face panel using grid approach
        def in_h(cx, cy, holes):
            for h in holes:
                if h['type'] == 'rect':
                    if abs(cx-h['x']) <= h['w']/2 and abs(cy-h['y']) <= h['h']/2:
                        return True
                elif h['type'] == 'circle':
                    if (cx-h['x'])**2+(cy-h['y'])**2 <= h['r']**2:
                        return True
            return False

        for ix in range(N):
            for iy in range(N):
                x0 = -half + ix*step; x1 = x0+step
                y0 = -half + iy*step; y1 = y0+step
                cx,cy = (x0+x1)/2,(y0+y1)/2
                if in_h(cx,cy,holes_outer): continue
                pts2 = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
                vo = out_face(pts2, None)
                if flip_outer:
                    m.add_quad(vo[0],vo[3],vo[2],vo[1])
                else:
                    m.add_quad(vo[0],vo[1],vo[2],vo[3])

        for ix in range(N):
            for iy in range(N):
                x0 = -ihalf + ix*(INNER/N); x1 = x0+INNER/N
                y0 = -ihalf + iy*(INNER/N); y1 = y0+INNER/N
                cx,cy = (x0+x1)/2,(y0+y1)/2
                if in_h(cx,cy,holes_inner): continue
                pts2 = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
                vi = in_face(pts2, None)
                if flip_inner:
                    m.add_quad(vi[0],vi[3],vi[2],vi[1])
                else:
                    m.add_quad(vi[0],vi[1],vi[2],vi[3])

        # Rim (connecting outer to inner around the perimeter)
        rim_edges = [
            (-ihalf,-ihalf, ihalf,-ihalf),
            ( ihalf,-ihalf, ihalf, ihalf),
            ( ihalf, ihalf,-ihalf, ihalf),
            (-ihalf, ihalf,-ihalf,-ihalf),
        ]
        for x0,z0,x1,z1 in rim_edges:
            rim_quad(x0,z0,x1,z1)

        if has_opening:
            # Build the opening's inner wall (frame inner edges)
            ow = (INNER - 2*FRAME)/2
            opening_edges = [
                (-ow,-ow, ow,-ow),
                ( ow,-ow, ow, ow),
                ( ow, ow,-ow, ow),
                (-ow, ow,-ow,-ow),
            ]
            for x0,z0,x1,z1 in opening_edges:
                rim_quad(x0,z0,x1,z1)

        # Pips (indents on outer face)
        if pip_n and not has_opening:
            for cx, cy in pips_for_face(pip_n, face_normal):
                add_pip(m, face_normal, cx, cy)

    side_face('+y', 2)           # front
    side_face('-y', 5, has_opening=True)  # back (PCB slot)
    side_face('+x', 3)           # right
    side_face('-x', 4)           # left

    # ── Vertical inner walls (shell sides) ───────────────────────────────────
    # Connect inner top/bottom to inner side walls
    # These are the 4 thin inner columns at IHALF boundaries

    def inner_col(xa, ya, xb, yb):
        """Vertical wall segment from z=-IHALF to z=+IHALF."""
        m.add_quad((xa,ya,-IHALF),(xb,yb,-IHALF),(xb,yb,IHALF),(xa,ya,IHALF))

    inner_col(-IHALF,-IHALF, -IHALF, IHALF)
    inner_col(-IHALF, IHALF,  IHALF, IHALF)
    inner_col( IHALF, IHALF,  IHALF,-IHALF)
    inner_col( IHALF,-IHALF, -IHALF,-IHALF)

    # ── Pip indents – top face 1 is replaced by button hole (no pips) ─────
    # Bottom face 6
    for cx, cy in pips_for_face(6, '-z'):
        add_pip(m, '-z', cx, cy)

    return m


# ---------------------------------------------------------------------------
# Build the pip plunger (pushable single-dot keycap)
# ---------------------------------------------------------------------------

def build_pip_plunger():
    """
    A cylindrical plunger that sits in the Ø 13 mm button hole on the top face.

    Cross-section (side view, centred on Z axis, Z=0 is die top surface):

      ┌─────────────────────────────┐  ← pip dome (raised hemisphere on top)
      │         CAP DISC            │  z = +1.5 mm above die surface
      └──────────────────────────...┘  z = 0 (flush with top face outer)
             │  stem │                 z = -3 mm  (through the wall)
        ┌────┴────────┴────┐           z = -3 mm  (flange – stops plunger falling out)
        │     FLANGE       │           z = -4.5 mm
        └──────────────────┘
             │  stem │                 continues down to button
             └───────┘                 z = -STEM_LEN (tip that presses button)

    Clearances (all diameters):
      Hole Ø 13 mm (radius 6.5 mm)
      Cap  Ø 12.6 mm (radius 6.3 mm)  – 0.4 mm radial clearance
      Flange Ø 15 mm (radius 7.5 mm)  – sits against inner top-face surface
      Stem Ø 4 mm (radius 2 mm)        – slender, not to interfere with PCB
    """
    m = Mesh()
    SEG = 48

    # Key dimensions
    CAP_R       = BTN_R - 0.2       # 6.3 mm  – fits through the hole
    CAP_T       = 1.5               # cap disc thickness above the hole top
    CAP_BASE_Z  = 0.0               # z=0 = top of die face (outer surface)
    CAP_TOP_Z   = CAP_BASE_Z + CAP_T

    FLANGE_R    = BTN_R + 1.0       # 7.5 mm  – wider than hole → retains plunger
    FLANGE_T    = 1.5               # flange thickness
    FLANGE_TOP_Z  = CAP_BASE_Z - WALL       # flush with inside surface (−3 mm)
    FLANGE_BOT_Z  = FLANGE_TOP_Z - FLANGE_T

    STEM_R      = 2.0               # stem radius
    # Button is a standard 12 mm tactile; actuator height ≈ 3.5 mm above PCB.
    # PCB sits ~2 mm below inner top face → button actuator at about −5.5 mm.
    STEM_BOT_Z  = -8.0              # stem tip reaches well into the cavity

    # Pip dome on top of cap  (same size as die-face pips)
    PIP_DOME_R  = PIP_R             # 2.5 mm dome radius
    PIP_DOME_H  = PIP_R * 0.9      # 2.25 mm – flatter than a full hemisphere
    PIP_RINGS   = 12
    PIP_SEG     = SEG

    # ── Cap top face (annulus: full disc minus nothing, just a closed circle) ─
    # We build it as a filled disc at CAP_TOP_Z with a pip-dome indent/bump.

    def add_filled_disc(z, r, flip=False, seg=SEG):
        pts = [(r*math.cos(2*math.pi*i/seg), r*math.sin(2*math.pi*i/seg), z)
               for i in range(seg)]
        for i in range(1, seg - 1):
            if flip:
                m.add_tri(pts[0], pts[i + 1], pts[i])
            else:
                m.add_tri(pts[0], pts[i], pts[i + 1])

    # Cap bottom face (sits at CAP_BASE_Z, ring between STEM_R and CAP_R)
    def add_annulus(z, r_inner, r_outer, flip=False, seg=SEG):
        for i in range(seg):
            j = (i + 1) % seg
            a0 = 2*math.pi*i/seg
            a1 = 2*math.pi*j/seg
            xi0, yi0 = r_inner*math.cos(a0), r_inner*math.sin(a0)
            xi1, yi1 = r_inner*math.cos(a1), r_inner*math.sin(a1)
            xo0, yo0 = r_outer*math.cos(a0), r_outer*math.sin(a0)
            xo1, yo1 = r_outer*math.cos(a1), r_outer*math.sin(a1)
            if flip:
                m.add_quad((xo0,yo0,z),(xi0,yi0,z),(xi1,yi1,z),(xo1,yo1,z))
            else:
                m.add_quad((xo0,yo0,z),(xo1,yo1,z),(xi1,yi1,z),(xi0,yi0,z))

    # ── Cap outer cylindrical wall ───────────────────────────────────────────
    cap_bot = [(CAP_R*math.cos(2*math.pi*i/SEG),
                CAP_R*math.sin(2*math.pi*i/SEG),
                CAP_BASE_Z) for i in range(SEG)]
    cap_top = [(CAP_R*math.cos(2*math.pi*i/SEG),
                CAP_R*math.sin(2*math.pi*i/SEG),
                CAP_TOP_Z) for i in range(SEG)]
    tube(m, cap_bot, cap_top)

    # ── Cap top face (filled disc) ───────────────────────────────────────────
    add_filled_disc(CAP_TOP_Z, CAP_R, flip=False)

    # ── Pip dome on cap top (raised hemisphere) ───────────────────────────────
    for ir in range(PIP_RINGS):
        lat0 = math.pi / 2 * ir       / PIP_RINGS
        lat1 = math.pi / 2 * (ir + 1) / PIP_RINGS
        r0 = PIP_DOME_R * math.cos(lat0);  z0 = CAP_TOP_Z + PIP_DOME_H * math.sin(lat0)
        r1 = PIP_DOME_R * math.cos(lat1);  z1 = CAP_TOP_Z + PIP_DOME_H * math.sin(lat1)
        ring0 = [(r0*math.cos(2*math.pi*j/PIP_SEG),
                  r0*math.sin(2*math.pi*j/PIP_SEG), z0) for j in range(PIP_SEG)]
        ring1 = [(r1*math.cos(2*math.pi*j/PIP_SEG),
                  r1*math.sin(2*math.pi*j/PIP_SEG), z1) for j in range(PIP_SEG)]
        if ir < PIP_RINGS - 1:
            tube(m, ring0, ring1, flip=False)
        else:
            pole = (0.0, 0.0, CAP_TOP_Z + PIP_DOME_H)
            for j in range(PIP_SEG):
                jn = (j + 1) % PIP_SEG
                m.add_tri(ring0[j], ring0[jn], pole)
    # close pip dome base (annulus on cap top between pip base and edge)
    add_annulus(CAP_TOP_Z, PIP_DOME_R, CAP_R, flip=True)

    # ── Cap bottom face (annulus stem→cap edge) ───────────────────────────────
    add_annulus(CAP_BASE_Z, STEM_R, CAP_R, flip=True)

    # ── Stem outer wall from cap base down to flange top ─────────────────────
    stem_top = [(STEM_R*math.cos(2*math.pi*i/SEG),
                 STEM_R*math.sin(2*math.pi*i/SEG),
                 CAP_BASE_Z) for i in range(SEG)]
    flange_top_pts = [(STEM_R*math.cos(2*math.pi*i/SEG),
                       STEM_R*math.sin(2*math.pi*i/SEG),
                       FLANGE_TOP_Z) for i in range(SEG)]
    tube(m, flange_top_pts, stem_top)   # outward normal = outward

    # ── Flange top face (annulus stem→flange edge) ────────────────────────────
    add_annulus(FLANGE_TOP_Z, STEM_R, FLANGE_R, flip=True)

    # ── Flange outer wall ─────────────────────────────────────────────────────
    flange_outer_top = [(FLANGE_R*math.cos(2*math.pi*i/SEG),
                         FLANGE_R*math.sin(2*math.pi*i/SEG),
                         FLANGE_TOP_Z) for i in range(SEG)]
    flange_outer_bot = [(FLANGE_R*math.cos(2*math.pi*i/SEG),
                         FLANGE_R*math.sin(2*math.pi*i/SEG),
                         FLANGE_BOT_Z) for i in range(SEG)]
    tube(m, flange_outer_bot, flange_outer_top)

    # ── Flange bottom face (annulus stem→flange edge) ─────────────────────────
    add_annulus(FLANGE_BOT_Z, STEM_R, FLANGE_R, flip=False)

    # ── Stem continues from flange bottom down to tip ────────────────────────
    stem_flange_bot = [(STEM_R*math.cos(2*math.pi*i/SEG),
                        STEM_R*math.sin(2*math.pi*i/SEG),
                        FLANGE_BOT_Z) for i in range(SEG)]
    stem_tip_pts    = [(STEM_R*math.cos(2*math.pi*i/SEG),
                        STEM_R*math.sin(2*math.pi*i/SEG),
                        STEM_BOT_Z) for i in range(SEG)]
    tube(m, stem_tip_pts, stem_flange_bot)

    # ── Stem tip (flat circle) ────────────────────────────────────────────────
    add_filled_disc(STEM_BOT_Z, STEM_R, flip=True)

    return m


# ---------------------------------------------------------------------------
# Build the snap-fit lid
# ---------------------------------------------------------------------------

def build_lid():
    m = Mesh()
    T = WALL
    LW = INNER - 2*WALL*0.1   # lid outer width (slight clearance)
    # Flat plate
    flat_face_with_holes(m, LW, T/2, flip=False,
                         holes=[{'type': 'rect', 'x': 0, 'y': -IHALF*0.6,
                                  'w': 12, 'h': 8}])  # USB cutout
    flat_face_with_holes(m, LW, -T/2, flip=True,
                         holes=[{'type': 'rect', 'x': 0, 'y': -IHALF*0.6,
                                  'w': 12, 'h': 8}])
    # Edges
    for x0,y0,x1,y1 in [
        (-LW/2,-LW/2, LW/2,-LW/2),
        ( LW/2,-LW/2, LW/2, LW/2),
        ( LW/2, LW/2,-LW/2, LW/2),
        (-LW/2, LW/2,-LW/2,-LW/2),
    ]:
        m.add_quad((x0,y0,-T/2),(x1,y1,-T/2),(x1,y1,T/2),(x0,y0,T/2))
    # USB cutout walls
    uw, uh = 12, 8
    add_rect_shell(m, 0, -IHALF*0.6, -T/2, T/2, uw, uh, flip=True)
    return m


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    print("Building die shell …")
    die = build_die()
    die.save(os.path.join(out_dir, "dice.stl"))

    print("Building lid …")
    lid = build_lid()
    lid.save(os.path.join(out_dir, "dice_lid.stl"))

    print("Building pip plunger …")
    plunger = build_pip_plunger()
    plunger.save(os.path.join(out_dir, "dice_pip_plunger.stl"))

    print("Done.")
