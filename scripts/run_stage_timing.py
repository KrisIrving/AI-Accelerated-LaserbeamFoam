#!/usr/bin/env python3
"""DEC-012: isolated coarse timers; one S gate then at most one frozen M1.

Reuses approved prepared input bytes, unchanged native mesh utilities and full
checkers. Baseline build/libraries and original sources are read-only. A physical
solver-family label is retained for legacy checkers; observation.executable
always records the actual distinct binary. No retry/resume/cleanup.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import check_m_case as mc
import check_smoke_case as sc
import compare_plate2d_ab as native
from run_stage2_m1_batch import digest, entries

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'validation/stage2-M1-20261017-001/build'
MREF = ROOT/'runs/stage2-M1-20261017-001-baseline-1'
SREF = ROOT/'runs/local-codex-S-20261017-001'


def generate(source):
    """Only inject standalone statements; keep include scopes/lifetimes intact."""
    changes = [
        ('#include "fvCFD.H"', '#include "stageTiming.H"\n#include "fvCFD.H"'),
        ('int main(int argc, char *argv[])\n{', 'int main(int argc, char *argv[])\n{\n    StageTiming stageTiming;'),
        ('    while (runTime.run())', '    stageTiming.enter(StageTiming::OTHER);\n    while (runTime.run())'),
        ('            if (interfaceTrackingScheme == "MULES")', '            stageTiming.enter(StageTiming::VOF);\n            if (interfaceTrackingScheme == "MULES")'),
        ('            #include "updateProps.H"', '            stageTiming.enter(StageTiming::PROPS);\n            #include "updateProps.H"'),
        ('            laser.updateDeposition', '            stageTiming.enter(StageTiming::LASER);\n            laser.updateDeposition'),
        ('            mixture.correct();', '            stageTiming.enter(StageTiming::MIXTURE);\n            mixture.correct();\n            stageTiming.enter(StageTiming::OTHER);'),
        ('            #include "UEqn.H"', '            stageTiming.enter(StageTiming::U);\n            #include "UEqn.H"'),
        ('                mthd->solve(phi, U);', '                stageTiming.enter(StageTiming::MTHD);\n                mthd->solve(phi, U);'),
        ('            #include "TEqn.H"', '            stageTiming.enter(StageTiming::T);\n            #include "TEqn.H"\n            stageTiming.enter(StageTiming::OTHER);'),
        ('                #include "pEqn.H"', '                stageTiming.enter(StageTiming::P);\n                #include "pEqn.H"\n                stageTiming.enter(StageTiming::OTHER);'),
        ('                turbulence->correct();', '                stageTiming.enter(StageTiming::TURB);\n                turbulence->correct();\n                stageTiming.enter(StageTiming::OTHER);'),
        ('        runTime.write();', '        stageTiming.enter(StageTiming::OUTPUT);\n        runTime.write();'),
        ('        runTime.printExecutionTime(Info);', '        stageTiming.enter(StageTiming::OTHER);\n        runTime.printExecutionTime(Info);'),
        ('    return 0;', '    stageTiming.finish();\n    return 0;'),
    ]
    result = source
    for old, new in changes:
        assert result.count(old) == 1, ('unexpected source anchor', old)
        result = result.replace(old, new)
    # Dropping only observation lines reproduces the entire original C file.
    stripped = ''.join(line for line in result.splitlines(keepends=True)
        if 'stageTiming' not in line and 'StageTiming stageTiming;' not in line)
    assert stripped == source, 'native source projection differs'
    return result


def snapshot():
    files = []
    for base in ('src','applications','tutorials'):
        files += [ROOT/p for p in subprocess.check_output(
            ['git','ls-files',base],cwd=ROOT,text=True).splitlines() if (ROOT/p).is_file()]
    for ref in (SREF, *(ROOT/'runs'/f'stage2-M1-20261017-001-baseline-{i}' for i in (1,2,3))):
        files += [p for p in ref.rglob('*') if p.is_file()]
    files += list((BASE/'install').rglob('*.so')) + list((BASE/'install/bin').iterdir())
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(set(files))}


def times(case):
    return {float(p.name):p for p in case.iterdir() if p.is_dir() and native.NUMBER.fullmatch(p.name) and float(p.name)>0}


def compare(case, ref, expected_fields, expected_times):
    """Exact all-file equality is stricter than unchanged numerical tolerances.

    Native full checks parse every field. Uniform state is also semantically
    parsed through the existing M parser, including the S gate's scalar state.
    """
    actual, original = times(case), times(ref)
    assert set(actual)==set(original) and len(actual)==expected_times
    physical = {}; uniform = {}; count=0
    for t, directory in sorted(actual.items()):
        old=original[t]
        names={p.name for p in directory.iterdir() if p.is_file()}
        assert names=={p.name for p in old.iterdir() if p.is_file()}
        for name in sorted(names):
            sha=digest(directory/name)
            assert sha==digest(old/name), f'physical field differs: {directory.name}/{name}'
            physical[f'{directory.name}/{name}']=sha;count+=1
        ua=native.uniform_inventory(directory/'uniform')
        ub=native.uniform_inventory(old/'uniform')
        assert ua==ub
        for name in sorted(ua):
            if ua[name] != 'file':continue
            pa,pb=directory/'uniform'/name,old/'uniform'/name
            assert digest(pa)==digest(pb), 'uniform differs: '+str(pa)
            if pa.name=='cumulativeContErr':
                assert mc.parse_uniform_dimensioned_scalar(pa)==mc.parse_uniform_dimensioned_scalar(pb)
            else:
                p=native.Parser(native.read_ascii(pa));d=p.dictionary();p.done()
                q=native.Parser(native.read_ascii(pb));e=q.dictionary();q.done()
                native.compare_tree(d,e,1e-12,1e-10,name)
            uniform[f'{directory.name}/uniform/{name}']=digest(pa)
    assert count==expected_fields
    return {'status':'ALL_BYTE_IDENTICAL_AND_NATIVE_CHECKED','physical_fields':count,
            'output_times':len(actual),'uniform_files':len(uniform),
            'physical_sha256':physical,'uniform_sha256':uniform}


def run(out):
    (out/'.started').mkdir()  # Exclusive retained marker; refusing a second attempt.
    state={'schema':'stage2-coarse-timing-v1','decision':'DEC-012','status':'RUNNING',
           'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'base_build_commit':'2d3b2591bb8fec521448f9e47662ab595983f737',
           'runs':[],'stages':[],'tools':json.loads((out/'tools.json').read_text())}
    started=time.monotonic()
    def save():
        state['elapsed_seconds']=time.monotonic()-started
        (out/'progress.json').write_text(json.dumps(state,indent=2)+'\n')
    def command(name,args,cwd=ROOT,limit=180,env=None,timer=None,log=None):
        timer=timer or out/(name+'.time.txt');log=log or out/(name+'.log')
        assert not timer.exists() and not log.exists()
        start=time.monotonic()
        with log.open('xb') as f:
            # GNU timeout owns process termination; parent blocks, no polling.
            result=subprocess.run(['/usr/bin/time','-v','-o',str(timer),
                'timeout','--signal=TERM','--kill-after=10s',str(limit)+'s',
                'taskset','-c','0',*map(str,args)],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        rec={'name':name,'exit':result.returncode,'wall_seconds':time.monotonic()-start,
             'resources':sc.gnu_time_record(timer)}
        state['stages'].append(rec);save()
        if result.returncode:raise RuntimeError(f'{name} exit {result.returncode}; no retry')
        return rec
    try:
        assert os.environ.get('WM_PROJECT_VERSION')=='v2512'
        assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
        protected=snapshot();(out/'protected-before.json').write_text(json.dumps(protected,indent=2)+'\n')
        state['protected_files']=len(protected);save()
        source=ROOT/'applications/solvers/laserbeamFoam'
        build=out/'solver';build.mkdir()
        for p in source.rglob('*'):
            rel=p.relative_to(source)
            if not p.is_file() or p.name.startswith('log.') or ('Make' in rel.parts and rel.parts[0]=='Make' and len(rel.parts)>2):continue
            if p.suffix not in ('.H','.C') and rel.as_posix() not in ('Make/files','Make/options'):continue
            dest=build/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        original=(source/'laserbeamFoam.C').read_text()
        (build/'laserbeamFoam.C').write_text(generate(original))
        shutil.copy2(ROOT/'profiling/stageTiming.H',build/'stageTiming.H')
        (build/'Make/files').write_text('laserbeamFoam.C\n\nEXE = $(FOAM_USER_APPBIN)/laserbeamFoamStageTiming\n')
        options=(build/'Make/options').read_text().replace('../../../src',str(ROOT/'src'))
        (build/'Make/options').write_text(options)
        env=os.environ.copy();env.update(FOAM_USER_APPBIN=str(out/'bin'),FOAM_USER_LIBBIN=str(BASE/'install/lib'),
            LD_LIBRARY_PATH=str(BASE/'install/lib')+':'+env.get('LD_LIBRARY_PATH',''),
            OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        (out/'bin').mkdir()
        command('build',['wmake'],build,600,env)
        exe=out/'bin/laserbeamFoamStageTiming'
        state['binary_sha256']=digest(exe)
        state['generated_source_sha256']=digest(build/'laserbeamFoam.C')
        deps=command('dependencies',['ldd',exe],env=env)
        deptext=(out/'dependencies.log').read_text();assert 'not found' not in deptext
        origins={line.split()[0]:line.split()[2] for line in deptext.splitlines() if ' => ' in line}
        expected=dict(line.split() for line in (BASE/'dependencies.laserbeamFoam.tsv').read_text().splitlines())
        assert origins==expected, 'dynamic library origins differ from original baseline'
        state['dependency_origins_match_baseline']=True
        for label,ref in (('S',SREF),('M1',MREF)):
            case=ROOT/'runs'/f'{out.name}-{label}';case.mkdir()
            runrec={'id':label,'status':'PREPARING','actual_executable':'laserbeamFoamStageTiming'}
            state['runs'].append(runrec);save()
            prep=time.monotonic()
            approved=entries(ref/'inputs.sha256')
            if label=='M1':assert approved==json.loads((ROOT/'benchmarks/performance/M1-stage2.json').read_text())['input_sha256']
            for rel,sha in approved.items():
                assert digest(ref/rel)==sha
                dest=case/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ref/rel,dest)
            shutil.copy2(ref/'inputs.sha256',case/'inputs.sha256')
            manifest=json.loads((ref/'manifest.json').read_text())
            manifest.update(project_commit=state['source_commit'],build_commit=state['source_commit'],
                build_dir=str(build),threads=1,execution='ISOLATED_COARSE_TIMING')
            manifest['observation']={'executable':str(exe),'binary_sha256':state['binary_sha256'],
                'baseline_build_commit':state['base_build_commit'],'solver_field_semantics':'physical solver family for unchanged legacy checkers; actual executable recorded here',
                'timing_enabled':True,'input_origin':'existing approved byte-identical inputs'}
            (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            (case/'preparation.time.txt').write_text('preparation_wall_seconds='+str(time.monotonic()-prep)+'\n')
            shutil.copytree(case/'initial',case/'0')
            meshstart=time.monotonic()
            for stage in ('blockMesh','checkMesh','setFields'):
                rec=command(label+'-'+stage,[stage],case,180,env,case/f'time.{stage}.txt',case/f'log.{stage}')
                (case/f'exit.{stage}.txt').write_text(str(rec['exit'])+'\n')
            assert 'Mesh OK' in (case/'log.checkMesh').read_text()
            for rel,sha in entries(ref/'initialized.sha256').items():assert digest(case/rel)==sha,rel
            shutil.copy2(ref/'initialized.sha256',case/'initialized.sha256')
            (case/'.mesh-complete').touch()
            (case/'execution.txt').write_text(f'program={exe}\nmpi_ranks=1\nthreads=1\nresource_policy=MONITORED_ONLY\n')
            (case/'.solve-started').mkdir()
            runtime=env.copy();runtime.update(LBF_STAGE_TIMING='1',LBF_STAGE_TIMING_FILE=str(case/'stage-timing.csv'))
            rec=command(label+'-solver',[exe],case,120 if label=='S' else 1800,runtime,
                case/'time.laserbeamFoam.txt',case/'log.laserbeamFoam')
            (case/'solver.exit.txt').write_text('0\n');(case/'exit.laserbeamFoam.txt').write_text('0\n')
            shutil.copy2(case/'time.laserbeamFoam.txt',case/'solver.time.txt')
            runrec['solver']=rec;save()
            if label=='S':
                report=sc.check(case);expected='SMOKE_CHECKS_PASSED'
            else:
                report=mc.check(case);expected='EXPLORATION_CHECKS_PASSED'
            (case/'numeric-check.json').write_text(json.dumps(report,indent=2)+'\n')
            runrec['check']={'status':report['status'],'issues':report.get('issues',[]),
                'wall_seconds':report.get('offline_check_wall_seconds')};save()
            assert report['status']==expected and not report.get('issues'), runrec['check']
            runrec['comparison']=compare(case,ref,19 if label=='S' else 190,1 if label=='S' else 10)
            with (case/'stage-timing.csv').open() as stream:
                rows=list(csv.DictReader(stream))
            modules={r['phase']:{'calls':int(r['calls']),'wall_nanoseconds':int(r['wall_nanoseconds'])} for r in rows}
            total=modules.pop('TOTAL')['wall_nanoseconds']
            assert sum(r['wall_nanoseconds'] for r in modules.values())==total
            wall=rec['resources']['wall_seconds']
            assert 0<total/1e9<=wall+0.02
            runrec.update(status='PASSED',modules=modules,internal_total_seconds=total/1e9,
                external_unmeasured_seconds=wall-total/1e9)
            if label=='M1':
                overhead=wall/205.96-1;runrec['relative_wall_change_vs_205_96']=overhead
                state['credible_ranking']=overhead<=0.05
                state['status']='M1_TIMING_PASSED' if state['credible_ranking'] else 'OVERHEAD_ABOVE_5_PERCENT_NO_RANKING'
            save()
        after=snapshot();(out/'protected-after.json').write_text(json.dumps(after,indent=2)+'\n')
        assert after==protected,'protected baseline/source files changed'
        state['protected_sha_unchanged']=True
    except Exception as exc:
        state.update(status='STOPPED',error=type(exc).__name__+': '+str(exc),credible_ranking=False)
        if 'protected' in locals():
            after=snapshot();(out/'protected-after.json').write_text(json.dumps(after,indent=2)+'\n')
            state['protected_sha_unchanged']=after==protected
    finally:save()
    print(state['status'],state.get('error',''),flush=True)
    return 0 if state['status']=='M1_TIMING_PASSED' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-dir',type=Path,required=True)
    args=parser.parse_args();out=args.batch_dir.resolve(strict=True)
    assert out.is_relative_to(ROOT/'validation')
    sys.exit(run(out))
