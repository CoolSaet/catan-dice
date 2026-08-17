// ==========================================
// PARAMETRIC AMS DICE ENCLOSURE 
// (12.5mm ROUND SWITCH + EXTRA WEMOS CLEARANCE)
// ==========================================
$fn = 60; // Smoothness for circles/cylinders

/* [Render Selection] */
part = "all"; // [body_ams: Main Body (Color 1), pips_ams: All Pips (Color 2), top_lid_ams: Top Lid (Color 1), top_pips_ams: Top Lid Pips (Color 2), bottom_lid_ams: Bottom Lid (Color 1), bottom_pip_ams: Bottom Lid Pip (Color 2), all: Color Preview]

/* [Core Dimensions] */
inner_size    = 63.0; // 63mm internal cavity for 2000mAh battery
wall_thick    = 1.8;  // Wall thickness
dice_size     = inner_size + (2 * wall_thick); // 66.6mm outer cube
corner_rad    = 3.5;  // Outer rounded corner/edge radius (mm)

/* [AMS Pip Specs] */
pip_dia       = 6.0;  
pip_depth     = 0.8;  // Flush skin depth

/* [Internal Compartments] */
bat_bay_h     = 17.0; 
floor_thick   = 2.0;  

/* [Board Specs - Matched to Photo] */
wemos_w       = 25.8; // Board width
wemos_l       = 34.4; // Board length
pcb_thick     = 1.6;  
standoff_h    = 8.0;  // Standoff height above internal floor

// Mounting Holes & Threaded Inserts (Opposite USB Port)
insert_hole_dia = 4.0; // Pilot hole for M2 heat-set insert
insert_depth    = 5.0; // Depth for heat-set insert
standoff_dia    = 6.8; // Outer diameter of standoff pillar
v4_hole_spacing = 20.0; // Distance between mounting holes

// Board & Switch Layout Offsets
wemos_x_shift = -8.5; // Shifted 8.5mm to the left to free up room for chunky switch
wemos_y_shift = (inner_size/2) - (wemos_l/2) - 0.5; // Micro-USB flush against back wall
switch_x_pos  = 16.5; // Positioned on the right side of the back wall

// Ports & Cutouts
usb_c_w         = 10.5; // Micro-USB port cutout width
usb_c_h         = 6.0;  // Micro-USB port cutout height
usb_w         = 12.5; // Micro-USB port cutout width
usb_h         = 8.5;  // Micro-USB port cutout height
button_dia    = 16.2; // Top lid button hole diameter
switch_dia    = 12.2; // Round power switch hole diameter

/* [Lid Parameters] */
lid_thick     = 3.5;  // Matches corner_rad for smooth curvature transition
lip_height    = 3.5;  
clearance     = 0.15; 

// ==========================================
// RENDER CONTROL
// ==========================================

if (part == "body_ams") {
    difference() {
        dice_body();
        side_pips();
    }
} else if (part == "pips_ams") {
    intersection() {
        outer_block(dice_size - 2*lid_thick);
        side_pips();
    }
} else if (part == "top_lid_ams") {
    difference() {
        top_lid();
        top_side6_pips();
    }
} else if (part == "top_pips_ams") {
    intersection() {
        top_lid_outer();
        top_side6_pips();
    }
} else if (part == "bottom_lid_ams") {
    difference() {
        bottom_lid();
        bottom_side1_pip();
    }
} else if (part == "bottom_pip_ams") {
    intersection() {
        bottom_lid_outer();
        bottom_side1_pip();
    }
} else if (part == "all") {
    // Multi-Material Color Preview
    color("DarkSlateGray") difference() { dice_body(); side_pips(); }
    color("White") intersection() { outer_block(dice_size - 2*lid_thick); side_pips(); }
    
    translate([0, 0, dice_size/2 + 12]) {
        color("DarkSlateGray") difference() { top_lid(); top_side6_pips(); }
        color("White") intersection() { top_lid_outer(); top_side6_pips(); }
    }
    
    translate([0, 0, -dice_size/2 - 12]) {
        color("DarkSlateGray") difference() { bottom_lid(); bottom_side1_pip(); }
        color("White") intersection() { bottom_lid_outer(); bottom_side1_pip(); }
    }
}

// ==========================================
// MODULES & GEOMETRY
// ==========================================

module outer_shell() {
    minkowski() {
        cube([dice_size - 2*corner_rad, dice_size - 2*corner_rad, dice_size - 2*corner_rad], center=true);
        sphere(r=corner_rad);
    }
}

module outer_block(h_val) {
    linear_extrude(height=h_val, center=true)
        offset(r=corner_rad)
            square([dice_size - 2*corner_rad, dice_size - 2*corner_rad], center=true);
}

module top_lid_outer() {
    intersection() {
        outer_shell();
        translate([0, 0, dice_size/2 - lid_thick/2 + 0.01])
            cube([dice_size + 10, dice_size + 10, lid_thick + 0.02], center=true);
    }
}

module bottom_lid_outer() {
    intersection() {
        outer_shell();
        translate([0, 0, -dice_size/2 + lid_thick/2 - 0.01])
            cube([dice_size + 10, dice_size + 10, lid_thick + 0.02], center=true);
    }
}

module dice_body() {
    floor_z = -dice_size/2 + wall_thick + bat_bay_h;
    body_h = dice_size - 2*lid_thick;
    
    difference() {
        // Outer Body Wall
        outer_block(body_h);
        
        // Inner Cavity
        cube([inner_size, inner_size, inner_size], center=true);
            
        // Top Lid Lip Recess
        translate([0, 0, body_h/2 - lip_height/2 + 0.1])
            cube([inner_size + clearance, inner_size + clearance, lip_height + 0.2], center=true);

        // Bottom Lid Lip Recess
        translate([0, 0, -body_h/2 + lip_height/2 - 0.1])
            cube([inner_size + clearance, inner_size + clearance, lip_height + 0.2], center=true);

        // --- PORTS & CUTOUTS ---

        // Wire Pass-Through Cutout in Middle Floor
        translate([wemos_x_shift + wemos_w/2 + 3, wemos_y_shift, floor_z])
            cube([10, 14, floor_thick * 3], center=true);

        // Micro-USB-C Port Cutout (Shifted with Wemos)
        translate([wemos_x_shift, dice_size/2, floor_z + floor_thick + standoff_h + pcb_thick ])
            cube([usb_c_w, wall_thick * 3, usb_c_h], center=true);

    // Micro-USB Shield Port Cutout (Shifted with Wemos)
        translate([wemos_x_shift + -5, dice_size/2, floor_z + floor_thick + standoff_h + pcb_thick + 12 ])
            cube([usb_w, wall_thick * 3, usb_h], center=true);


        // 12.5mm Round Power Switch Cutout
        translate([switch_x_pos, dice_size/2, floor_z + floor_thick + standoff_h + pcb_thick + 7.0])
            rotate([90, 0, 0])
                cylinder(d=switch_dia, h=wall_thick * 3, center=true);
    }
    
    // Internal Divider Floor + Integrated Standoffs
    translate([0, 0, floor_z]) {
        difference() {
            union() {
                // Main Divider Plate
                cube([inner_size, inner_size, floor_thick], center=true);
                
                // Threaded Insert Standoffs attached directly onto middle plate
                translate([wemos_x_shift, wemos_y_shift, floor_thick/2]) {
                    wemos_v4_standoffs();
                }
                
                // Threaded Insert Standoffs attached directly onto middle plate
                translate([wemos_x_shift, wemos_y_shift+30, floor_thick/2]) {
                    wemos_v4_standoffs();
                }
            }
            
            // Re-apply Battery Wire Pass-Through Hole
            translate([wemos_x_shift + wemos_w/2 + 3, wemos_y_shift, 0])
                cube([10, 14, floor_thick * 4], center=true);
        }
    }
}

module wemos_v4_standoffs() {
    hole_y_pos = -wemos_l/2 ; 

    difference() {
        union() {
            // Reinforcing Base Plate tied to middle floor
            translate([0, hole_y_pos, 1.0])
                cube([v4_hole_spacing + standoff_dia, standoff_dia, 2.0], center=true);

            // 2 Standoff Pillars
            for (x = [-v4_hole_spacing/2, v4_hole_spacing/2]) {
                translate([x, hole_y_pos, standoff_h/2])
                    cylinder(d=standoff_dia, h=standoff_h, center=true);
            }
        }
        
        // Heat-Set Insert Pilot Holes
        for (x = [-v4_hole_spacing/2, v4_hole_spacing/2]) {
            translate([x, hole_y_pos, standoff_h - insert_depth/2 + 0.1])
                cylinder(d=insert_hole_dia, h=insert_depth + 0.2, center=true);
        }
    }
}

module top_lid() {
    floor_z = -dice_size/2 + wall_thick + bat_bay_h;
    
    difference() {
        union() {
            // Top Lid Outer Plate
            top_lid_outer();
                
            // Retaining Lip
            translate([0, 0, dice_size/2 - lid_thick - lip_height/2])
                cube([inner_size - clearance, inner_size - clearance, lip_height], center=true);
                
            // Down-clamp Pillars to keep PCB locked onto standoffs
    //        c_height = (dice_size/2 - lid_thick) - (floor_z + floor_thick + standoff_h + pcb_thick);
            
    //        translate([wemos_x_shift - wemos_w/2 + 1.5, wemos_y_shift, dice_size/2 - lid_thick - c_height/2])
    //            cube([3, 6, c_height], center=true);
                
    //        translate([wemos_x_shift + wemos_w/2 - 1.5, wemos_y_shift, dice_size/2 - lid_thick - c_height/2])
    //            cube([3, 6, c_height], center=true);
        }
        
        // Pushbutton Cutout
        translate([0, 10, dice_size/2 - lid_thick])
            cylinder(h=lid_thick * 4, d=button_dia, center=true);
    }
}

module bottom_lid() {
    union() {
        // Bottom Lid Outer Plate
        bottom_lid_outer();
            
        // Retaining Lip
        translate([0, 0, -dice_size/2 + lid_thick + lip_height/2])
            cube([inner_size - clearance, inner_size - clearance, lip_height], center=true);
    }
}

// --- PIP FLUSH VOLUMES MODULES ---

module pip_volume(x, y, z, rx=0, ry=0) {
    translate([x, y, z])
        rotate([rx, ry, 0])
            cylinder(d=pip_dia, h=pip_depth * 2, center=true);
}

module side_pips() {
    d = 16; 
    off = dice_size/2 - pip_depth/2 + 0.05;
    
    // Side 2 (Front)
    pip_volume(-d, -off, d, 90, 0); pip_volume(d, -off, -d, 90, 0);
    
    // Side 3 (Right)
    pip_volume(off, -d, d, 0, 90); pip_volume(off, 0, 0, 0, 90); pip_volume(off, d, -d, 0, 90);
    
    // Side 4 (Left)
    pip_volume(-off, -d, d, 0, -90); pip_volume(-off, d, d, 0, -90);
    pip_volume(-off, -d, -d, 0, -90); pip_volume(-off, d, -d, 0, -90);
    
    // Side 5 (Back)
    pip_volume(-d, off, d, -90, 0); pip_volume(d, off, d, -90, 0);
    pip_volume(0, off, 0, -90, 0);
    pip_volume(-d, off, -d, -90, 0); pip_volume(d, off, -d, -90, 0);
}

module top_side6_pips() {
    d = 16;
    z_off = dice_size/2 - pip_depth/2 + 0.05;
    
    pip_volume(-d, -d, z_off); pip_volume(-d, 0, z_off); pip_volume(-d, d, z_off);
    pip_volume( d, -d, z_off); pip_volume( d, 0, z_off); pip_volume( d, d, z_off);
}

module bottom_side1_pip() {
    z_off = -dice_size/2 + pip_depth/2 - 0.05;
    pip_volume(0, 0, z_off);
}