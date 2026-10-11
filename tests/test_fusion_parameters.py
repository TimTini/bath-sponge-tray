"""Checks independent of Fusion; these do not replace a Fusion geometry test."""
import importlib.util
from pathlib import Path
import re
import math
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'tray_fusion', ROOT / 'fusion' / 'BathSpongeTray' / 'BathSpongeTray.py')
tray = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tray)


class ParametersTest(unittest.TestCase):
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
