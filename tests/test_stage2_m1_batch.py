"""No-CFD checks for frozen identity, sampling eligibility and stop-on-failure."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_stage2_m1_batch as batch
import prepare_m_case


class Stage2BatchTests(unittest.TestCase):
    def test_approved_performance_profile_preserves_original_workload(self):
        freeze=json.loads((ROOT/'benchmarks/performance/M1-stage2.json').read_text())
        old=prepare_m_case.config_for('M1')
        self.assertEqual(freeze['status'],'APPROVED_FIXED_PERFORMANCE_WORKLOAD')
        self.assertEqual(freeze['cells'],old['cells'])
        self.assertEqual(freeze['steps'],old['steps'])
        self.assertEqual(freeze['delta_t_s'],old['delta_t'])
        self.assertEqual(freeze['write_interval_steps'],old['write_interval'])
        self.assertEqual(freeze['solver_timeout_seconds'],1800)
        self.assertEqual(len(freeze['input_sha256']),25)

    def test_sampling_is_not_enabled_by_noisy_timings(self):
        self.assertTrue(batch.stability([198,200,202])['stable_for_sampling'])
        self.assertFalse(batch.stability([150,200,250])['stable_for_sampling'])

    def test_build_failure_retains_marker_and_never_prepares_a_case(self):
        (ROOT/'validation').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'validation',prefix='stage2-unit-') as tmp:
            out=Path(tmp)
            (out/'perf-permission-probe.exit.txt').write_text('255\n')
            (out/'perf-permission-probe.log').write_text('permission denied\n')
            with patch.object(batch.subprocess,'Popen') as popen, patch.object(
                    batch.subprocess,'check_output',return_value=b'unit-test-source-sha\n'):
                popen.return_value.poll.return_value=1
                popen.return_value.returncode=1
                self.assertEqual(batch.run_batch(out),2)
                self.assertEqual(popen.call_count,1)
            saved=json.loads((out/'batch.json').read_text())
            self.assertEqual(saved['status'],'STOPPED')
            self.assertEqual(saved['runs'],[])
            with self.assertRaises(FileExistsError):
                batch.run_batch(out)


if __name__=='__main__':
    unittest.main()
