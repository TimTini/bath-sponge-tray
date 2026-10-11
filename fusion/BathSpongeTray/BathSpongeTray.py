"""Native parametric Fusion model. Run from Utilities > Scripts and Add-Ins.

All lengths below are millimetres. Fusion geometry uses centimetres internally.
Change dimensions in Modify > Change Parameters after creating the model.
"""
import math
import traceback

# Choose 1 (raised ear) or 2 (holes in the rear wall) before running.
HOOK_COUNT = 1
# Optional native recompute checks; restores the original parameters afterwards.
VERIFY_VARIANTS = False

DEFAULTS = {
    'length': 100, 'width': 70, 'height': 30, 'wall': 3,
    'floor_thickness': 3, 'corner_radius': 8,
    'drain_diameter': 6, 'drain_pitch': 12, 'drain_edge_margin': 10,
    'hook_diameter': 10, 'hook_spacing': 60, 'hook_height': 20,
    'ear_width': 30, 'ear_rise': 17, 'ear_root_radius': 3,
}
COMMENTS = {
    'length': 'Chiều dài ngoài của khay', 'width': 'Chiều ngang ngoài của khay',
    'height': 'Chiều cao thân, không gồm tai', 'wall': 'Độ dày thành và tai',
    'floor_thickness': 'Độ dày đáy', 'corner_radius': 'Bán kính góc ngoài',
    'drain_diameter': 'Đường kính lỗ thoát nước', 'drain_pitch': 'Bước tâm lỗ thoát nước',
    'drain_edge_margin': 'Khoảng cách tối thiểu từ mép ngoài tới tâm lỗ đáy',
    'hook_diameter': 'Đường kính lỗ móc', 'hook_spacing': 'Khoảng tâm hai móc (bản 2 lỗ)',
    'hook_height': 'Cao tâm móc (bản 2 lỗ)', 'ear_width': 'Chiều rộng tai (bản 1 lỗ)',
    'ear_rise': 'Chiều cao tai trên miệng (bản 1 lỗ)',
    'ear_root_radius': 'Bán kính fillet chân tai (bản 1 lỗ)',
}
DERIVED = {
    'drain_columns': ('floor((length - 2 * drain_edge_margin) / drain_pitch) + 1', ''),
    'drain_rows': ('floor((width - 2 * drain_edge_margin) / drain_pitch) + 1', ''),
    'drain_start_x': ('(length - (drain_columns - 1) * drain_pitch) / 2', 'mm'),
    'drain_start_y': ('(width - (drain_rows - 1) * drain_pitch) / 2', 'mm'),
    'ear_hole_height': ('ear_rise / 2', 'mm'),
}


def layout(p, hook_count):
    """Validate the SCAD design envelope and calculate expected dimensions."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(all(math.isfinite(v) and v > 0 for v in p.values()),
            'Các kích thước phải là số dương hữu hạn.')
    require(p['length'] > 2 * p['corner_radius'] and p['width'] > 2 * p['corner_radius'],
            'Dài và ngang phải lớn hơn hai lần bán kính góc.')
    require(p['corner_radius'] > p['wall'], 'Bán kính góc phải lớn hơn độ dày thành.')
    require(p['height'] > p['floor_thickness'], 'Thân phải cao hơn độ dày đáy.')
    require(p['drain_pitch'] >= p['drain_diameter'] + 3, 'Các lỗ đáy cần cách nhau ít nhất 3 mm.')
    require(p['drain_edge_margin'] >= max(p['corner_radius'], p['wall'] + p['drain_diameter'] / 2 + 3),
            'Lề đáy quá nhỏ so với góc, thành hoặc đường kính lỗ.')
    columns = math.floor((p['length'] - 2 * p['drain_edge_margin']) / p['drain_pitch']) + 1
    rows = math.floor((p['width'] - 2 * p['drain_edge_margin']) / p['drain_pitch']) + 1
    require(columns > 0 and rows > 0, 'Khay không đủ chỗ cho lưới lỗ.')
    require(hook_count in (1, 2), 'HOOK_COUNT chỉ nhận 1 hoặc 2.')
    if hook_count == 1:
        require(p['height'] > 5, 'Thân phải cao hơn 5 mm để chân tai nằm trong thành.')
        require(p['hook_diameter'] + 10 <= p['ear_width'] <= p['length'] - 2 * p['corner_radius'],
                'Chiều rộng tai không đủ cho lỗ hoặc vượt đoạn thẳng của thành.')
        require(p['ear_rise'] >= p['hook_diameter'] + 6,
                'Tai cần ít nhất 3 mm vật liệu trên và dưới lỗ móc.')
        require(p['ear_root_radius'] <= p['ear_rise'] / 2 and
                p['ear_width'] + 2 * p['ear_root_radius'] <= p['length'] - 2 * p['corner_radius'],
                'Fillet chân tai không vừa tai/thành.')
        centres = [(p['length'] / 2, p['height'] + p['ear_rise'] / 2)]
    else:
        require(p['hook_spacing'] > p['hook_diameter'] and
                (p['length'] - p['hook_spacing'] - p['hook_diameter']) / 2 >= p['corner_radius'] + 3,
                'Hai lỗ móc quá gần nhau hoặc quá gần góc thành.')
        require(p['floor_thickness'] + 3 + p['hook_diameter'] / 2 <= p['hook_height'] <=
                p['height'] - 3 - p['hook_diameter'] / 2, 'Lỗ móc quá gần đáy hoặc miệng khay.')
        centres = [((p['length'] - p['hook_spacing']) / 2, p['hook_height']),
                   ((p['length'] + p['hook_spacing']) / 2, p['hook_height'])]
    return {'columns': columns, 'rows': rows,
            'start_x': (p['length'] - (columns - 1) * p['drain_pitch']) / 2,
            'start_y': (p['width'] - (rows - 1) * p['drain_pitch']) / 2,
            'hook_centres': centres,
            'overall_height': p['height'] + (p['ear_rise'] if hook_count == 1 else 0)}


def build(design, hook_count):
    import adsk.core as core
    import adsk.fusion as fusion

    layout(DEFAULTS, hook_count)
    comp = design.rootComponent
    # Fusion owns the root component name; run() names the new document instead.
    value = core.ValueInput.createByString
    point = core.Point3D.create
    for name, number in DEFAULTS.items():
        design.userParameters.add(name, value('{} mm'.format(number)), 'mm', COMMENTS[name])
    for name, (expression, units) in DERIVED.items():
        design.userParameters.add(name, value(expression), units, 'Tự tính; giữ công thức này.')

    def cm(expression):
        return design.unitsManager.evaluateExpression(expression, 'mm')

    def collection(items):
        result = core.ObjectCollection.create()
        for item in items:
            result.add(item)
        return result

    horizontal = fusion.DimensionOrientations.HorizontalDimensionOrientation
    vertical = fusion.DimensionOrientations.VerticalDimensionOrientation

    def dimension(sketch, a, b, orientation, expression):
        text = point(b.geometry.x + 0.2, b.geometry.y + 0.2, 0)
        dim = sketch.sketchDimensions.addDistanceDimension(a, b, orientation, text)
        dim.parameter.expression = expression

    def position(sketch, vertex, x, y):
        dimension(sketch, sketch.originPoint, vertex, horizontal, x)
        dimension(sketch, sketch.originPoint, vertex, vertical, y)

    def rectangle(plane, x, y, w, h, name, at_origin=False):
        sketch = comp.sketches.add(plane)
        sketch.name = name
        lines = sketch.sketchCurves.sketchLines
        x0, y0, dx, dy = cm(x), cm(y), cm(w), cm(h)
        start = sketch.originPoint if at_origin else point(x0, y0, 0)
        bottom = lines.addByTwoPoints(start, point(x0 + dx, y0, 0))
        right = lines.addByTwoPoints(bottom.endSketchPoint, point(x0 + dx, y0 + dy, 0))
        top = lines.addByTwoPoints(right.endSketchPoint, point(x0, y0 + dy, 0))
        left = lines.addByTwoPoints(top.endSketchPoint, bottom.startSketchPoint)
        for line in (bottom, top):
            sketch.geometricConstraints.addHorizontal(line)
        for line in (right, left):
            sketch.geometricConstraints.addVertical(line)
        if not at_origin:
            position(sketch, bottom.startSketchPoint, x, y)
        dimension(sketch, bottom.startSketchPoint, bottom.endSketchPoint, horizontal, w)
        dimension(sketch, right.startSketchPoint, right.endSketchPoint, vertical, h)
        return sketch

    def circle(plane, x, y, diameter, name):
        sketch = comp.sketches.add(plane)
        sketch.name = name
        curve = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            point(cm(x), cm(y), 0), cm(diameter) / 2)
        position(sketch, curve.centerSketchPoint, x, y)
        dim = sketch.sketchDimensions.addDiameterDimension(curve, point(cm(x) + 1, cm(y) + 1, 0))
        dim.parameter.expression = diameter
        return sketch

    def offset(plane, expression, name):
        inp = comp.constructionPlanes.createInput()
        inp.setByOffset(plane, value(expression))
        result = comp.constructionPlanes.add(inp)
        result.name = name
        result.isLightBulbOn = False
        return result

    def extrude(sketch, distance, operation, name, target=None):
        if not sketch.isFullyConstrained:
            raise RuntimeError('Sketch chưa được ràng buộc đầy đủ: ' + sketch.name)
        inp = comp.features.extrudeFeatures.createInput(sketch.profiles.item(0), operation)
        inp.setOneSideExtent(fusion.DistanceExtentDefinition.create(value(distance)),
                             fusion.ExtentDirections.PositiveExtentDirection)
        if target is not None:
            inp.participantBodies = [target]
        result = comp.features.extrudeFeatures.add(inp)
        result.name = name
        sketch.isVisible = False
        return result

    def axis_edges(body, axis):
        result = []
        for edge in body.edges:
            if not core.Line3D.cast(edge.geometry):
                continue
            a, b = edge.startVertex.geometry, edge.endVertex.geometry
            delta = [abs(a.x - b.x), abs(a.y - b.y), abs(a.z - b.z)]
            if delta[axis] > 1e-6 and all(delta[i] < 1e-6 for i in range(3) if i != axis):
                result.append(edge)
        return result

    def fillet(edges, radius, name, expected):
        if len(edges) != expected:
            raise RuntimeError('{}: expected {} edges, found {}'.format(name, expected, len(edges)))
        inp = comp.features.filletFeatures.createInput()
        inp.edgeSetInputs.addConstantRadiusEdgeSet(collection(edges), value(radius), False)
        result = comp.features.filletFeatures.add(inp)
        result.name = name

    def combine(target, tool, operation, name):
        inp = comp.features.combineFeatures.createInput(target, collection([tool]))
        inp.operation = operation
        inp.isKeepToolBodies = False
        result = comp.features.combineFeatures.add(inp)
        result.name = name

    new_body = fusion.FeatureOperations.NewBodyFeatureOperation
    cut = fusion.FeatureOperations.CutFeatureOperation
    outer = rectangle(comp.xYConstructionPlane, '0 mm', '0 mm', 'length', 'width', 'Outside', True)
    body = extrude(outer, 'height', new_body, 'Tray blank').bodies.item(0)
    fillet(axis_edges(body, 2), 'corner_radius', 'Outside corners', 4)

    floor_plane = offset(comp.xYConstructionPlane, 'floor_thickness', 'Inside floor')
    inner = rectangle(floor_plane, 'wall', 'wall', 'length - 2 * wall', 'width - 2 * wall', 'Inside')
    cavity = extrude(inner, 'height - floor_thickness', new_body, 'Cavity tool').bodies.item(0)
    fillet(axis_edges(cavity, 2), 'corner_radius - wall', 'Inside corners', 4)
    combine(body, cavity, cut, 'Hollow tray')

    # XZ plane normal is -Y in Fusion; use its actual normal for the offset sign.
    rear_sign = comp.xZConstructionPlane.geometry.normal.y
    rear = offset(comp.xZConstructionPlane, '-width' if rear_sign < 0 else 'width', 'Rear wall')
    # Confirm sketch coordinates are X/Z and positive extrusion points into the wall.
    probe = comp.sketches.add(rear)
    origin = probe.sketchToModelSpace(point(0, 0, 0))
    px = probe.sketchToModelSpace(point(1, 0, 0))
    pz = probe.sketchToModelSpace(point(0, 1, 0))
    if abs(px.x - origin.x - 1) > 1e-6 or abs(pz.z - origin.z - 1) > 1e-6 or rear_sign >= 0:
        raise RuntimeError('Unexpected XZ plane orientation; cannot construct rear features safely.')
    probe.deleteMe()

    if hook_count == 1:
        ear = rectangle(rear, '(length - ear_width) / 2', 'height - 5 mm',
                        'ear_width', 'ear_rise + 5 mm', 'Ear outline')
        ear_body = extrude(ear, 'wall', new_body, 'Ear blank').bodies.item(0)
        fillet(axis_edges(ear_body, 1), '5 mm', 'Ear corners R5', 4)
        combine(body, ear_body, fusion.FeatureOperations.JoinFeatureOperation, 'Join ear')
        shoulders = []
        for edge in axis_edges(body, 1):
            a = edge.startVertex.geometry
            if abs(a.z - cm('height')) < 1e-6 and any(
                abs(a.x - cm(x)) < 1e-6 for x in ('(length - ear_width) / 2', '(length + ear_width) / 2')):
                shoulders.append(edge)
        fillet(shoulders, 'ear_root_radius', 'Ear root fillets', 2)
        hook_specs = [('length / 2', 'height + ear_hole_height')]
    else:
        hook_specs = [('(length - hook_spacing) / 2', 'hook_height'),
                      ('(length + hook_spacing) / 2', 'hook_height')]
    for index, (x, z) in enumerate(hook_specs, 1):
        sketch = circle(rear, x, z, 'hook_diameter', 'Hook {}'.format(index))
        extrude(sketch, 'wall', cut, 'Hook cut {}'.format(index), body)

    drain = circle(comp.xYConstructionPlane, 'drain_start_x', 'drain_start_y', 'drain_diameter', 'Drain seed')
    seed = extrude(drain, 'floor_thickness', cut, 'Drain cut', body)
    patterns = comp.features.rectangularPatternFeatures
    inp = patterns.createInput(collection([seed]), comp.xConstructionAxis,
                               value('drain_columns'), value('drain_pitch'),
                               fusion.PatternDistanceType.SpacingPatternDistanceType)
    inp.setDirectionTwo(comp.yConstructionAxis, value('drain_rows'), value('drain_pitch'))
    inp.patternComputeOption = fusion.PatternComputeOptions.IdenticalPatternCompute
    pattern = patterns.add(inp)
    pattern.name = 'Automatic drainage grid'
    body.name = 'Bath sponge tray'
    return body


def check_model(design, hook_count):
    """Native checks for the current document, including feature health."""
    import adsk.fusion as fusion
    p = {name: design.userParameters.itemByName(name).value * 10 for name in DEFAULTS}
    expected = layout(p, hook_count)
    if not design.computeAll():
        raise RuntimeError('Fusion computeAll failed.')
    for i in range(design.timeline.count):
        entity = design.timeline.item(i).entity
        if isinstance(entity, fusion.Feature) and entity.healthState != fusion.FeatureHealthStates.HealthyFeatureHealthState:
            raise RuntimeError('{}: {}'.format(entity.name, entity.errorOrWarningMessage))
    bodies = design.rootComponent.bRepBodies
    if bodies.count != 1 or not bodies.item(0).isSolid:
        raise RuntimeError('Expected one solid body.')
    bounds = bodies.item(0).preciseBoundingBox
    actual = [bounds.maxPoint.x - bounds.minPoint.x, bounds.maxPoint.y - bounds.minPoint.y,
              bounds.maxPoint.z - bounds.minPoint.z]
    wanted = [p['length'], p['width'], expected['overall_height']]
    if any(abs(a * 10 - b) > 0.01 for a, b in zip(actual, wanted)):
        raise RuntimeError('Unexpected model bounds: {}'.format(actual))
    for sketch in design.rootComponent.sketches:
        if not sketch.isFullyConstrained:
            raise RuntimeError('Unconstrained sketch: ' + sketch.name)
    drain_sketch = design.rootComponent.sketches.itemByName('Drain seed')
    seed = drain_sketch.sketchCurves.sketchCircles.item(0)
    if (abs(seed.centerSketchPoint.geometry.x * 10 - expected['start_x']) > 0.01 or
            abs(seed.centerSketchPoint.geometry.y * 10 - expected['start_y']) > 0.01 or
            abs(seed.radius * 20 - p['drain_diameter']) > 0.01):
        raise RuntimeError('Drain seed sketch did not follow parameters.')
    for index, (x, z) in enumerate(expected['hook_centres'], 1):
        sketch = design.rootComponent.sketches.itemByName('Hook {}'.format(index))
        circle = sketch.sketchCurves.sketchCircles.item(0)
        centre = sketch.sketchToModelSpace(circle.centerSketchPoint.geometry)
        if any(abs(a - b) > 0.01 for a, b in zip(
                [centre.x * 10, centre.y * 10, centre.z * 10], [x, p['width'], z])) or abs(circle.radius * 20 - p['hook_diameter']) > 0.01:
            raise RuntimeError('Hook sketch did not follow parameters.')
    for name, wanted in [('drain_columns', expected['columns']), ('drain_rows', expected['rows']),
                         ('drain_start_x', expected['start_x'] / 10), ('drain_start_y', expected['start_y'] / 10)]:
        if abs(design.userParameters.itemByName(name).value - wanted) > 1e-6:
            raise RuntimeError('Unexpected derived parameter: ' + name)
    pattern = design.rootComponent.features.rectangularPatternFeatures.itemByName('Automatic drainage grid')
    if (round(pattern.quantityOne.value) != expected['columns'] or
            round(pattern.quantityTwo.value) != expected['rows']):
        raise RuntimeError('Drain pattern quantities did not follow parameters.')
    return expected


def verify_variants(design, hook_count):
    """Run inside Fusion to test native parameter changes, restoring originals."""
    params = design.userParameters
    original = {name: params.itemByName(name).expression for name in DEFAULTS}
    cases = [dict(length=160, width=100), dict(length=100, width=60),
             dict(height=40, wall=4, floor_thickness=4, corner_radius=10),
             dict(drain_pitch=15, drain_diameter=5), dict(ear_rise=20, ear_width=34),
             dict(hook_diameter=8, hook_spacing=50, hook_height=19)]
    cases.append(dict(length=52, width=21, drain_pitch=40, hook_spacing=20))
    try:
        for changes in cases:
            for name, expression in original.items():
                params.itemByName(name).expression = expression
            for name, number in changes.items():
                params.itemByName(name).expression = '{} mm'.format(number)
            check_model(design, hook_count)
    finally:
        for name, expression in original.items():
            params.itemByName(name).expression = expression
        check_model(design, hook_count)
    return len(cases)


def run(context):
    import adsk.core as core
    import adsk.fusion as fusion
    app = core.Application.get()
    ui = app.userInterface
    try:
        layout(DEFAULTS, HOOK_COUNT)
        doc = app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
        doc.name = 'Bath Sponge Tray - {} hook(s)'.format(HOOK_COUNT)
        design = fusion.Design.cast(app.activeProduct)
        design.designType = fusion.DesignTypes.ParametricDesignType
        build(design, HOOK_COUNT)
        expected = check_model(design, HOOK_COUNT)
        verified = verify_variants(design, HOOK_COUNT) if VERIFY_VARIANTS else 0
        app.activeViewport.fit()
        ui.messageBox('Đã tạo khay với {} × {} lỗ đáy.\n'
                      'Chỉnh kích thước ở Modify > Change Parameters.\n'
                      'Giữ công thức của các tham số tự tính.\n'
                      'Số biến thể đã kiểm tra trong Fusion: {}.'.format(
                          expected['columns'], expected['rows'], verified))
    except Exception:
        ui.messageBox('Không tạo/kiểm tra được mô hình. Document đang mở để kiểm tra.\n\n' + traceback.format_exc())
