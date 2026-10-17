"""Analytical checks for the narrow optical audit; no OpenFOAM execution."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_optical_threshold as audit
import compare_plate2d_ab as native


class OpticalAuditTests(unittest.TestCase):
    def test_lazy_mesh_grammar_preserves_validation(self):
        text = 'FoamFile {format ascii; class vectorField;} 2 ((0 1 2)(3 4 5))'
        parsers = [native.Parser(text), audit.MeshTokenStream(text)]
        parsed = []
        for parser in parsers:
            parsed.append((parser.header(), parser.pop(), parser.item()))
            parser.done()
        self.assertEqual(parsed[0], parsed[1])
        malformed = audit.MeshTokenStream('(0 1]')
        with self.assertRaises(native.ReviewRequired):
            malformed.item()

    def test_affine_field_has_analytical_normal_on_shuffled_lattice(self):
        # Anisotropic spacing and reversed numbering reject cell-order stencils.
        keys = [(i,j,k) for i in range(4) for j in range(4) for k in range(4)][::-1]
        lookup = {key: cell for cell, key in enumerate(keys)}
        spacing = [2e-5, 3e-5, 4e-5]
        slopes = [100, -200, 50]
        alpha = [0.5+sum(slopes[a]*key[a]*spacing[a] for a in range(3)) for key in keys]
        grid = {"shape": [4]*3, "lookup": lookup, "spacing": spacing,
                "volumes": [math.prod(spacing)]*64}
        normals, delta = audit.interior_normals(grid, alpha)
        expected_g = math.sqrt(sum(x*x for x in slopes))
        self.assertEqual(len(normals), 8)
        for value in normals.values():
            self.assertAlmostEqual(value, expected_g/(expected_g+delta), places=14)

    def test_inclusive_gate_does_not_snap_adjacent_floats(self):
        values = [math.nextafter(0.5, 0), 0.5, math.nextafter(0.5, 1)]
        result = audit.threshold_stats(values)
        self.assertEqual((result["lt_half"], result["eq_half"], result["gt_half"]), (1,1,1))
        self.assertLess(result["min_minus_half"], 0)
        self.assertGreater(result["max_minus_half"], 0)


if __name__ == "__main__":
    unittest.main()
