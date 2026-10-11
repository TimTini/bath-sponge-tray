"""Checks independent of Fusion; these do not replace a Fusion geometry test."""
import importlib.util
from pathlib import Path
import re
import math
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from itertools import product

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'tray_fusion', ROOT / 'fusion' / 'BathSpongeTray' / 'BathSpongeTray.py')
tray = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tray)


class ParametersTest(unittest.TestCase):
    def test_rear_coordinates_and_inward_direction_follow_sketch_frame(self):
        def point(x, y, z):
            return SimpleNamespace(x=x, y=y, z=z)

        for sx, sz, swap in product((1, -1), (1, -1), (False, True)):
            normal_y = sx * sz * (1 if swap else -1)

            class Sketch:
                def modelToSketchSpace(self, p):
                    a, b = sx * p.x, sz * p.z
                    depth = normal_y * (p.y - 7)
                    return point(b, a, depth) if swap else point(a, b, depth)

                def sketchToModelSpace(self, p):
                    a, b = (p.y, p.x) if swap else (p.x, p.y)
                    return point(a / sx, 7 + normal_y * p.z, b / sz)

            with self.subTest(sx=sx, sz=sz, swap=swap):
                sketch = Sketch()
                frame = tray.rear_frame(sketch, 7, point)
                self.assertEqual(frame['x_axis'], 1 if swap else 0)
                self.assertEqual(frame['z_axis'], 0 if swap else 1)
                self.assertEqual(frame['positive_inward'], normal_y < 0)
                local = tray.rear_point(sketch, 5, 3.85, 7, point)
                world = sketch.sketchToModelSpace(local)
                self.assertEqual((world.x, world.y, world.z), (5, 7, 3.85))
                local.z = 0.3 if frame['positive_inward'] else -0.3
                self.assertAlmostEqual(sketch.sketchToModelSpace(local).y, 6.7)

    def test_build_does_not_rename_root_component(self):
        class ReachedParameters(Exception):
            pass

        class RootComponent:
            @property
            def name(self):
                return 'Document name'

            @name.setter
            def name(self, value):
                raise RuntimeError('3 : root component name cannot be changed')

        def add_parameter(*args):
            raise ReachedParameters

        core = SimpleNamespace(ValueInput=SimpleNamespace(createByString=str),
                               Point3D=SimpleNamespace(create=lambda *args: args))
        fusion = SimpleNamespace(DimensionOrientations=SimpleNamespace(
            HorizontalDimensionOrientation=0, VerticalDimensionOrientation=1))
        adsk = SimpleNamespace(core=core, fusion=fusion)
        design = SimpleNamespace(rootComponent=RootComponent(),
                                 userParameters=SimpleNamespace(add=add_parameter))
        with patch.dict('sys.modules', {'adsk': adsk, 'adsk.core': core, 'adsk.fusion': fusion}):
            with self.assertRaises(ReachedParameters):
                tray.build(design, 1)

    def test_scad_defaults_match(self):
        source = (ROOT / 'khay-bong-tam.scad').read_text(encoding='utf-8')
        values = dict(re.findall(r'^([a-z_]+) = (\d+(?:\.\d+)?);', source, re.M))
        for name, value in tray.DEFAULTS.items():
            self.assertEqual(value, float(values[name]), name)

    def test_default_layout(self):
        result = tray.layout(tray.DEFAULTS, 1)
        self.assertEqual((result['columns'], result['rows']), (7, 5))
        self.assertEqual((result['start_x'], result['start_y']), (14, 11))
        self.assertEqual(result['hook_centres'], [(50, 38.5)])
        self.assertEqual(result['overall_height'], 47)

    def test_resize_recounts_and_centres_grid(self):
        result = tray.layout(dict(tray.DEFAULTS, length=160, width=100, ear_rise=20), 1)
        self.assertEqual((result['columns'], result['rows']), (12, 7))
        self.assertEqual((result['start_x'], result['start_y']), (14, 14))
        self.assertEqual(result['hook_centres'], [(80, 40)])

    def test_two_hooks_follow_length_and_height(self):
        result = tray.layout(dict(tray.DEFAULTS, length=150, hook_spacing=80, hook_height=22), 2)
        self.assertEqual(result['hook_centres'], [(35, 22), (115, 22)])
        self.assertEqual(result['overall_height'], 30)

    def test_single_column_and_row(self):
        result = tray.layout(dict(tray.DEFAULTS, length=52, width=21, drain_pitch=40), 1)
        self.assertEqual((result['columns'], result['rows']), (1, 1))
        self.assertEqual((result['start_x'], result['start_y']), (26, 10.5))

    def test_invalid_geometry_rejected(self):
        for changes, count in [({'wall': 8}, 1), ({'drain_pitch': 8}, 1),
                               ({'ear_rise': 14}, 1), ({'hook_spacing': 100}, 2),
                               ({'hook_height': 28}, 2), ({'length': 15}, 1)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                tray.layout(dict(tray.DEFAULTS, **changes), count)

    def test_native_derived_expressions_follow_layout(self):
        for changes in [{}, {'length': 160, 'width': 100},
                        {'length': 52, 'width': 21, 'drain_pitch': 40},
                        {'drain_pitch': 15, 'ear_rise': 20}]:
            p = dict(tray.DEFAULTS, **changes)
            expected = tray.layout(p, 1)
            values = dict(p)
            for name, (expression, _) in tray.DERIVED.items():
                values[name] = eval(expression, {'__builtins__': {}, 'floor': math.floor}, values)
            for key, target in [('drain_columns', 'columns'), ('drain_rows', 'rows'),
                                ('drain_start_x', 'start_x'), ('drain_start_y', 'start_y')]:
                self.assertEqual(values[key], expected[target])
            self.assertEqual(values['ear_hole_height'], p['ear_rise'] / 2)


if __name__ == '__main__':
    unittest.main()
