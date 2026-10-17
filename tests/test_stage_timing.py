"""Observation-only guards; no CFD is launched by tests."""
import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_stage_timing as timing


class StageTimingTests(unittest.TestCase):
    def test_native_projection_and_scope(self):
        source=(ROOT/'applications/solvers/laserbeamFoam/laserbeamFoam.C').read_text()
        result=timing.generate(source)
        stripped=''.join(line for line in result.splitlines(keepends=True) if 'stageTiming' not in line)
        self.assertEqual(source,stripped)
        self.assertEqual(result.count('StageTiming::P);'),1)
        self.assertEqual(result.count('StageTiming::OUTPUT);'),1)

    @unittest.skipUnless(shutil.which('g++'),'requires C++ compiler')
    def test_timer_disabled_and_exclusive_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);source=d/'timer.C';binary=d/'timer'
            source.write_text('#include "stageTiming.H"\nint main(){ StageTiming t; '
                't.enter(StageTiming::VOF); t.enter(StageTiming::PROPS); '
                't.enter(StageTiming::VOF); t.finish(); }\n')
            subprocess.run(['g++','-std=c++17','-O3','-I',str(ROOT/'profiling'),str(source),'-o',str(binary)],check=True)
            env=dict(os.environ,LBF_STAGE_TIMING='0',LBF_STAGE_TIMING_FILE=str(d/'off.csv'))
            subprocess.run([binary],env=env,check=True)
            self.assertFalse((d/'off.csv').exists())
            env.update(LBF_STAGE_TIMING='1',LBF_STAGE_TIMING_FILE=str(d/'on.csv'))
            subprocess.run([binary],env=env,check=True)
            with (d/'on.csv').open() as stream:
                rows={r['phase']:r for r in csv.DictReader(stream)}
            total=rows.pop('TOTAL')
            self.assertEqual(int(total['wall_nanoseconds']),sum(int(r['wall_nanoseconds']) for r in rows.values()))
            self.assertEqual(rows['VOF']['calls'],'2')
            self.assertEqual(rows['p_equation']['calls'],'0')

    def test_nonmatching_native_source_refused(self):
        with self.assertRaises(AssertionError):timing.generate('int main() {}')


if __name__=='__main__':unittest.main()
