/*
 * Catan Dice – Housing for Wemos D1 Mini
 * =========================================
 * A six-sided die shell that houses the Wemos D1 Mini (ESP8266).
 *
 * Orientation conventions (standard Western die layout):
 *   TOP  (+Z) : face 1  – single pip  →  push-button hole here
 *   BOTTOM (-Z): face 6  – six pips   →  toggle-switch hole here
 *   FRONT (+Y) : face 2
 *   BACK  (-Y) : face 5
 *   RIGHT (+X) : face 3
 *   LEFT  (-X) : face 4
 *
 * The D1 Mini PCB (34.2 × 25.6 mm) slides in from the back face and rests
 * horizontally inside the shell.  A snap-fit lid covers the back opening.
 *
 * Dimensions are generous so the PCB + USB cable can fit comfortably.
 * Adjust OUTER_SIZE, WALL, and CORNER_R as needed.
 */

$fn = 64;

// ── Parameters ────────────────────────────────────────────────────────────────
OUTER_SIZE = 50;          // outer edge length of the die [mm]
WALL       = 3.0;         // shell wall thickness [mm]
CORNER_R   = 5.0;         // corner rounding radius [mm]

// Inner cavity (auto-computed)
INNER      = OUTER_SIZE - 2*WALL;

// Pip geometry
PIP_R      = 2.5;         // pip dome radius [mm]
PIP_DEPTH  = 1.2;         // how deep the pip sinks [mm]

// Hardware holes
BTN_R      = 6.5;         // push-button hole radius [mm]  (12 mm momentary button)
SW_W       = 10.0;        // toggle-switch slot width [mm]
SW_H       = 5.5;         // toggle-switch slot height [mm]

// Lid slot
LID_SLOT_D = 1.5;         // depth of snap-fit slot [mm]
LID_SLOT_W = 1.5;         // width of snap-fit slot [mm]

// ── Helper: rounded cube (Minkowski) ─────────────────────────────────────────
module rounded_cube(size, r) {
    s = size - 2*r;
    minkowski() {
        cube([s, s, s], center=true);
        sphere(r=r);
    }
}

// ── Helper: pip (hemispherical indent) ───────────────────────────────────────
// Placed flush against a face – call this module and then subtract from shell.
module pip(x, y, face) {
    // face: "top","bottom","front","back","left","right"
    half = OUTER_SIZE / 2;
    translate(face == "top"    ? [x, y,  half] :
              face == "bottom" ? [x, y, -half] :
              face == "front"  ? [x,  half, y] :
              face == "back"   ? [x, -half, y] :
              face == "right"  ? [ half, x, y] :
                                 [-half, x, y])
        rotate(face == "top"    ? [0,0,0]    :
               face == "bottom" ? [180,0,0]  :
               face == "front"  ? [-90,0,0]  :
               face == "back"   ? [90,0,0]   :
               face == "right"  ? [0,90,0]   :
                                  [0,-90,0])
            // small cylinder that becomes a dome
            cylinder(h=PIP_DEPTH+0.1, r1=PIP_R, r2=0, center=false);
}

// ── Pip layouts per face ──────────────────────────────────────────────────────
S = OUTER_SIZE * 0.22;   // pip grid step

module pips_1(face) { pip(  0,   0, face); }

module pips_2(face) {
    pip(-S,  S, face);
    pip( S, -S, face);
}

module pips_3(face) {
    pip(-S,  S, face);
    pip(  0, 0, face);
    pip( S, -S, face);
}

module pips_4(face) {
    pip(-S,  S, face);
    pip( S,  S, face);
    pip(-S, -S, face);
    pip( S, -S, face);
}

module pips_5(face) {
    pip(-S,  S, face);
    pip( S,  S, face);
    pip(  0, 0, face);
    pip(-S, -S, face);
    pip( S, -S, face);
}

module pips_6(face) {
    pip(-S,  S, face);
    pip( S,  S, face);
    pip(-S,  0, face);
    pip( S,  0, face);
    pip(-S, -S, face);
    pip( S, -S, face);
}

// ── Main die shell ────────────────────────────────────────────────────────────
module die_shell() {
    difference() {
        // Outer rounded cube
        rounded_cube(OUTER_SIZE, CORNER_R);

        // Inner cavity
        translate([0, 0, WALL])  // floor at bottom, open back
            rounded_cube(INNER + 2*WALL, max(CORNER_R - WALL, 1));

        // Open back face (for PCB insertion) – full inner opening
        translate([0, -(OUTER_SIZE/2 + 1), 0])
            cube([INNER, 4, INNER], center=true);

        // Lid snap-fit slot around back opening
        translate([0, -(OUTER_SIZE/2 - LID_SLOT_D/2), 0])
            cube([INNER + 2*LID_SLOT_W,
                  LID_SLOT_D,
                  INNER + 2*LID_SLOT_W], center=true);

        // ── Push-button hole – TOP face (face 1) centre ──────────────────────
        translate([0, 0, OUTER_SIZE/2 - WALL])
            cylinder(h=WALL*2 + 1, r=BTN_R, center=true);

        // ── Toggle-switch slot – BOTTOM face (face 6) ────────────────────────
        // Positioned toward the -Y side so the lever is accessible
        translate([0, -S, -(OUTER_SIZE/2 - WALL)])
            cube([SW_W, SW_H, WALL*2 + 1], center=true);

        // ── Pips ─────────────────────────────────────────────────────────────
        // Face 1 – top (single pip replaced by button hole, pips omitted)
        // Face 6 – bottom
        pips_6("bottom");
        // Face 2 – front
        pips_2("front");
        // Face 5 – back  (will be mostly open for PCB slot, but add pips anyway)
        pips_5("back");
        // Face 3 – right
        pips_3("right");
        // Face 4 – left
        pips_4("left");
    }
}

// ── Snap-fit lid (back face) ──────────────────────────────────────────────────
module die_lid() {
    LID_T = WALL;
    translate([0, -(OUTER_SIZE/2 + LID_T/2 + 0.2), 0]) {
        difference() {
            cube([INNER + 2*(LID_SLOT_W - 0.3),
                  LID_T,
                  INNER + 2*(LID_SLOT_W - 0.3)], center=true);
            // USB access hole at bottom-centre of lid
            translate([0, 0, -(INNER/2)])
                cube([12, LID_T + 1, 10], center=true);
        }
    }
}

// ── Pip plunger (pushable single-dot keycap) ─────────────────────────────────
//
// Slides into the Ø 13 mm button hole on the top face.
// Z=0 = outer die top surface.
//
//   CAP_R    = BTN_R - 0.2 = 6.3 mm  (fits through the hole with 0.4 mm clearance)
//   FLANGE_R = BTN_R + 1.0 = 7.5 mm  (wider than hole → retains plunger inside die)
//   STEM_R   = 2 mm                   (slender stem to actuate the button)
//   STEM_LEN = 8 mm                   (reaches down to the button actuator)
//
module pip_plunger() {
    CAP_R      = BTN_R - 0.2;
    CAP_T      = 1.5;
    FLANGE_R   = BTN_R + 1.0;
    FLANGE_T   = 1.5;
    FLANGE_Z   = -WALL;          // sits against inner top-face surface
    STEM_R     = 2.0;
    STEM_LEN   = 8.0;
    DOME_R     = PIP_R;
    DOME_H     = PIP_R * 0.9;

    union() {
        // Cap disc
        cylinder(h=CAP_T, r=CAP_R, center=false);

        // Pip dome on top of cap
        translate([0, 0, CAP_T])
            scale([1, 1, DOME_H / DOME_R])
                sphere(r=DOME_R);

        // Stem from cap base down through wall to flange
        translate([0, 0, FLANGE_Z - FLANGE_T])
            cylinder(h=-(FLANGE_Z - FLANGE_T), r=STEM_R, center=false);

        // Flange (retaining collar)
        translate([0, 0, FLANGE_Z - FLANGE_T])
            cylinder(h=FLANGE_T, r=FLANGE_R, center=false);

        // Stem continues below flange to button actuator
        translate([0, 0, -STEM_LEN])
            cylinder(h=STEM_LEN - WALL - FLANGE_T, r=STEM_R, center=false);
    }
}

// ── Render ────────────────────────────────────────────────────────────────────
die_shell();

// Uncomment to render lid alongside shell:
// translate([OUTER_SIZE + 5, 0, 0]) die_lid();

// Uncomment to render pip plunger alongside shell:
// translate([0, OUTER_SIZE + 5, 0]) pip_plunger();
