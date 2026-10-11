// Khay bông tắm. Tất cả kích thước tính bằng mm.
/* [Kích thước khay - mm] */
// Chiều dài ngoài của khay.
length = 100;
// Chiều ngang ngoài của khay.
width = 70;
// Chiều cao thân khay, chưa tính phần tai treo nhô lên.
height = 30;
// Độ dày thành khay, đồng thời là độ dày tai treo.
wall = 3;
// Độ dày đáy khay.
floor_thickness = 3;
// Bán kính bo góc ngoài nhìn từ trên; bán kính trong bằng giá trị này trừ độ dày thành.
corner_radius = 8;

/* [Lỗ thoát nước - mm] */
// Đường kính lỗ thoát nước; số lượng và bố trí lỗ tự tính theo kích thước khay.
drain_diameter = 6;
// Khoảng cách tâm giữa hai lỗ thoát nước liền kề.
drain_pitch = 12;
// Khoảng cách tối thiểu từ mép ngoài đến tâm các lỗ ngoài cùng.
drain_edge_margin = 10;

/* [Lỗ móc treo - mm] */
// Số lỗ móc treo; một lỗ sẽ có tai nhô ở giữa thành sau.
hook_count = 1; // [1:Một lỗ,2:Hai lỗ]
// Đường kính lỗ móc cho cả hai tùy chọn.
hook_diameter = 10;
// Khoảng cách tâm hai lỗ móc, chỉ dùng khi chọn hai lỗ.
hook_spacing = 60;
// Chiều cao tâm lỗ tính từ đáy ngoài, chỉ dùng khi chọn hai lỗ.
hook_height = 20;

/* [Tai treo một lỗ - mm] */
// Chiều rộng tai treo ở giữa, chỉ dùng khi chọn một lỗ.
ear_width = 30;
// Chiều cao tai nhô trên miệng khay; lỗ móc tự căn giữa chiều cao này.
ear_rise = 17;
// Bán kính bo lõm tại hai chân tai nối với mép thành khay.
ear_root_radius = 3;

/* [Hidden] */
$fn = 64;
eps = 0.05;
// Keep the hole centred in the exposed ear whenever its height changes.
ear_hole_height = ear_rise / 2;
drain_columns = floor((length - 2 * drain_edge_margin) / drain_pitch) + 1;
drain_rows = floor((width - 2 * drain_edge_margin) / drain_pitch) + 1;
drain_start_x = (length - (drain_columns - 1) * drain_pitch) / 2;
drain_start_y = (width - (drain_rows - 1) * drain_pitch) / 2;

assert(length > 2 * corner_radius && width > 2 * corner_radius);
assert(wall > 0 && corner_radius > wall);
assert(floor_thickness > 0 && height > floor_thickness);
assert(drain_diameter > 0 && drain_pitch >= drain_diameter + 3);
// Keep centres beyond corner arcs and at least 3 mm of floor beside each hole.
assert(drain_edge_margin >= max(corner_radius, wall + drain_diameter / 2 + 3));
assert(drain_columns > 0 && drain_rows > 0);
assert(hook_count == 1 || hook_count == 2);
assert(hook_diameter > 0);
if (hook_count == 2) {
    assert(hook_spacing > hook_diameter);
    assert((length - hook_spacing) / 2 - hook_diameter / 2 >= corner_radius + 3);
    assert(hook_height - hook_diameter / 2 >= floor_thickness + 3);
    assert(hook_height + hook_diameter / 2 <= height - 3);
} else {
    assert(ear_width >= hook_diameter + 10 && ear_width <= length - 2 * corner_radius);
    assert(ear_rise >= hook_diameter + 4);
    assert(ear_hole_height - hook_diameter / 2 >= 2);
    assert(ear_rise - ear_hole_height - hook_diameter / 2 >= 3);
    assert(ear_root_radius > 0 && ear_root_radius <= ear_rise / 2);
    assert(ear_width + 2 * ear_root_radius <= length - 2 * corner_radius);
}

module rounded_rectangle(l, w, r) {
    translate([r, r])
        offset(r = r)
            square([l - 2 * r, w - 2 * r]);
}

difference() {
    union() {
        difference() {
            linear_extrude(height = height)
                rounded_rectangle(length, width, corner_radius);
            translate([wall, wall, floor_thickness])
                linear_extrude(height = height - floor_thickness + eps)
                    rounded_rectangle(length - 2 * wall, width - 2 * wall,
                                      corner_radius - wall);
        }
        if (hook_count == 1) {
            translate([(length - ear_width) / 2, width, height - 5])
                rotate([90, 0, 0])
                    linear_extrude(height = wall)
                        rounded_rectangle(ear_width, ear_rise + 5, 5);
            // Concave quarter-circle transitions at both shoulders of the ear.
            for (side = [-1, 1])
                translate([length / 2 + side * ear_width / 2, width, height])
                    rotate([90, 0, 0])
                        linear_extrude(height = wall)
                            scale([side, 1])
                                difference() {
                                    square([ear_root_radius, ear_root_radius]);
                                    translate([ear_root_radius, ear_root_radius])
                                        circle(r = ear_root_radius);
                                }
        }
    }

    for (col = [0 : drain_columns - 1], row = [0 : drain_rows - 1])
        translate([drain_start_x + col * drain_pitch,
                   drain_start_y + row * drain_pitch, -eps])
            cylinder(d = drain_diameter, h = floor_thickness + 2 * eps);

    for (x = hook_count == 1 ? [length / 2] :
             [(length - hook_spacing) / 2, (length + hook_spacing) / 2])
        translate([x, width + eps, hook_count == 1 ? height + ear_hole_height : hook_height])
            rotate([90, 0, 0])
                cylinder(d = hook_diameter, h = wall + 2 * eps);
}
