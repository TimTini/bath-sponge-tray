"""Check exported default mesh; requires numpy, trimesh and networkx."""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

root = Path(__file__).resolve().parent
two_hooks = '--two-hooks' in sys.argv[1:]
stem = 'khay-bong-tam-2-lo' if two_hooks else 'khay-bong-tam'
mesh = trimesh.load_mesh(root / f'exports/{stem}.stl')
if not mesh.is_watertight or not mesh.is_winding_consistent:
    raise ValueError('Mesh must be watertight with consistent winding')
components = len(mesh.split())
if components != 1 or mesh.volume <= 0:
    raise ValueError('Expected one connected solid with positive volume')
np.testing.assert_allclose(mesh.bounds, [[0, 0, 0], [100, 70, 30 if two_hooks else 47]], atol=0.002)

# Inspect actual cross-sections through the floor and back wall.
floor_section = mesh.section(plane_origin=[0, 0, 1.5], plane_normal=[0, 0, 1])
floor_loops = floor_section.discrete
drains = [loop for loop in floor_loops if np.ptp(loop[:, 0]) < 7]
if len(floor_loops) != 36 or len(drains) != 35:
    raise ValueError('Expected outer floor outline and 35 drainage holes')
for loop in drains:
    np.testing.assert_allclose(np.ptp(loop[:, :2], axis=0), [6, 6], atol=0.002)

back_section = mesh.section(plane_origin=[0, 68.5, 0], plane_normal=[0, 1, 0])
back_loops = back_section.discrete
hooks = [loop for loop in back_loops if np.ptp(loop[:, 0]) < 11]
expected_hooks = 2 if two_hooks else 1
if len(back_loops) != expected_hooks + 1 or len(hooks) != expected_hooks:
    raise ValueError('Unexpected back wall outline or hook count')
centres = []
for loop in hooks:
    np.testing.assert_allclose(np.ptp(loop[:, [0, 2]], axis=0), [10, 10], atol=0.002)
    centres.append((loop.min(axis=0) + loop.max(axis=0)) / 2)
np.testing.assert_allclose(sorted(c[0] for c in centres), [20, 80] if two_hooks else [50], atol=0.002)
np.testing.assert_allclose([c[2] for c in centres], [20, 20] if two_hooks else [38.5], atol=0.002)
if not two_hooks:
    np.testing.assert_allclose(mesh.bounds[1, 2] - hooks[0][:, 2].max(), 3.5, atol=0.002)
    np.testing.assert_allclose(hooks[0][:, 2].min() - 30, 3.5, atol=0.002)
    # Raised ear must be 30 mm wide and remain attached to the back wall.
    ear = mesh.section(plane_origin=[0, 0, 32], plane_normal=[0, 0, 1])
    if len(ear.discrete) != 1:
        raise ValueError('Expected one continuous raised ear')
    expected_width = 30 + 2 * (3 - np.sqrt(3**2 - 1**2))
    np.testing.assert_allclose(np.ptp(ear.discrete[0][:, :2], axis=0),
                               [expected_width, 3], atol=0.012)
    root_section = mesh.section(plane_origin=[0, 0, 31], plane_normal=[0, 0, 1])
    expected_width = 30 + 2 * (3 - np.sqrt(3**2 - 2**2))
    np.testing.assert_allclose(np.ptp(root_section.discrete[0][:, :2], axis=0),
                               [expected_width, 3], atol=0.012)

report = {
    'bounds_mm': mesh.bounds.tolist(),
    'watertight': bool(mesh.is_watertight),
    'winding_consistent': bool(mesh.is_winding_consistent),
    'components': components,
    'triangles': len(mesh.faces),
    'volume_mm3': float(mesh.volume),
    'drain_count': len(drains),
    'drain_diameter_mm': 6,
    'hook_count': len(hooks),
    'hook_diameter_mm': 10,
    'hook_spacing_mm': 60 if two_hooks else None,
    'physical_print_verified': False,
}
(root / ('exports/audit-2-lo.json' if two_hooks else 'exports/audit.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
