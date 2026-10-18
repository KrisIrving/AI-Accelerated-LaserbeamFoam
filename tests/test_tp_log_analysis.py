import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_tp_logs import per_step,stats


class TPAnalysisTests(unittest.TestCase):
    def test_zero_iteration_solves_and_correction_pairing(self):
        lines=['Time = 1e-08','smoothSolver: Solving for T, Initial residual = 0, Final residual = 0, No Iterations 0',
            'Correcting epsilon1, mean residual = 0, max residual = 0']
        lines+=['DICPCG: Solving for p_rgh, Initial residual = 0, Final residual = 0, No Iterations 0']*3
        data=per_step(lines)
        self.assertEqual(stats(data,'T')['solves'],1)
        self.assertEqual(stats(data,'T')['zero_iteration_solves'],1)
        self.assertEqual(stats(data,'p_rgh')['iterations_total'],0)

    def test_missing_epsilon_record_rejected(self):
        lines=['Time = 1e-08', 'Solving for T, Initial residual = 1, Final residual = 0, No Iterations 1']
        lines+=['Solving for p_rgh, Initial residual = 0, Final residual = 0, No Iterations 0']*3
        with self.assertRaises(AssertionError):per_step(lines)


if __name__=='__main__':unittest.main()
