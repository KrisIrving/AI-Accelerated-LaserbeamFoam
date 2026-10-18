"""Exact arithmetic controls for the final sampled diagnosis; no CFD."""
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_restriction_samples import restriction_numbers


class RestrictionArithmeticTests(unittest.TestCase):
    def test_exact_equal_volume_interface_is_noncommutative(self):
        result=restriction_numbers([0,0,1,1,0,0,1,1],[1.0]*8,[Fraction(1)]*8)
        self.assertEqual(result["actual_restricted_alpha"],0.5)
        self.assertEqual(result["threshold_then_restrict"],0.5)
        self.assertEqual(result["restrict_then_threshold"],1)
        self.assertEqual(result["exact_binary_commutator"],"1/2")
        self.assertFalse(result["rounding_crosses_binary_volume_exact_gate"])

    def test_geometric_asymmetry_and_final_rounding_are_separated(self):
        # Metal children have exact smaller volume: even exact arithmetic is below half.
        alpha=[0,0,1,1,0,0,1,1]
        volumes=[1.0 if a==0 else 0.75 for a in alpha]
        result=restriction_numbers(alpha,volumes,list(map(Fraction,volumes)))
        self.assertEqual(result["binary_volume_exact_mean"],"3/7")
        self.assertEqual(result["restrict_then_threshold"],0)
        self.assertFalse(result["rounding_crosses_binary_volume_exact_gate"])
        self.assertEqual(result["ideal_equal_volume_restrict_then_threshold"],1)


if __name__=="__main__":
    unittest.main()
