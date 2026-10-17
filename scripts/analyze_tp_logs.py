#!/usr/bin/env python3
"""Read-only DEC-013 M1 T/p work-count analysis. Never launches CFD."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

import check_m_case as mc

ROOT=Path(__file__).resolve().parents[1]
SOLVE=re.compile(r'Solving for ([^,]+), Initial residual = (\S+), Final residual = (\S+), No Iterations (\d+)')
EPS=re.compile(r'Correcting epsilon1, mean residual = (\S+), max residual = (\S+)')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def per_step(lines):
    steps=[]
    for line in lines:
        match=re.fullmatch(r'\s*Time\s*=\s*(\S+)\s*',line)
        if match:
            steps.append({'step':len(steps)+1,'time_s':float(match[1]),'T':[],'p_rgh':[],'epsilon':[]})
        solve=SOLVE.search(line)
        if solve and solve[1] in ('T','p_rgh'):
            assert steps, 'evolved solve precedes Time'
            steps[-1][solve[1]].append({'iterations':int(solve[4]),'initial':float(solve[2]),'final':float(solve[3])})
        eps=EPS.search(line)
        if eps:
            assert steps
            steps[-1]['epsilon'].append({'mean':float(eps[1]),'max':float(eps[2])})
    for step in steps:
        assert len(step['T'])==len(step['epsilon']) and len(step['p_rgh'])==3
        assert 1<=len(step['T'])<=21
    return steps


def stats(steps,field):
    events=[event for step in steps for event in step[field]]
    counts=[len(step[field]) for step in steps]
    return {'solves':len(events),'iterations_total':sum(e['iterations'] for e in events),
        'iterations_max':max(e['iterations'] for e in events),'iterations_per_solve':sum(e['iterations'] for e in events)/len(events),
        'zero_iteration_solves':sum(e['iterations']==0 for e in events),
        'iteration_histogram':dict(sorted(Counter(e['iterations'] for e in events).items())),
        'solves_per_step_min':min(counts),'solves_per_step_max':max(counts),
        'solves_per_step_mean':len(events)/len(steps),'solves_per_step_histogram':dict(sorted(Counter(counts).items()))}


def analyze(out):
    started=time.monotonic();out.mkdir()  # Refuse overwrite and preserve progress/evidence.
    cases=[ROOT/'runs'/f'stage2-M1-20261017-001-baseline-{i}' for i in (1,2,3)]
    cases.append(ROOT/'runs/stage2-timing-20261017-002-M1')
    sources=[ROOT/'applications/solvers/laserbeamFoam'/n for n in ('TEqn.H','pEqn.H','readControls.H','updateProps.H')]
    files=sources+[p for c in cases for p in (c/'manifest.json',c/'log.laserbeamFoam',c/'system/fvSolution')]
    files += [cases[-1]/'numeric-check.json',ROOT/'docs/validation/stage2-M1-timing-20261017-summary.json']
    before={str(p.relative_to(ROOT)):digest(p) for p in files}
    result={'schema':'m1-tp-readonly-analysis-v1','decision':'DEC-013','status':'RUNNING',
        'analysis_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'cfd_runs_started':0,'input_sha256':before,'runs':[]}
    for case in cases:
        config=json.loads((case/'manifest.json').read_text())['config']
        checked=mc.parse_log(case,config)  # Existing fatal/time/count/residual validation unchanged.
        steps=per_step(mc.scan_log(case/'log.laserbeamFoam'))
        assert len(steps)==1000
        st={field:stats(steps,field) for field in ('T','p_rgh')}
        for field in st:
            for key in ('solves','iterations_total','iterations_max'):
                assert st[field][key]==checked['linear_summaries'][field][key]
        event_sha=hashlib.sha256(json.dumps(steps,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result['runs'].append({'case_id':case.name,'event_trace_sha256':event_sha,'statistics':st})
        if case==cases[-1]:
            bins=[]
            for begin in range(0,1000,100):
                group=steps[begin:begin+100]
                bins.append({'step_first':begin+1,'step_last':begin+100,'time_end_us':(begin+100)/100,
                    'T_solves':sum(len(x['T']) for x in group),'T_iterations':sum(e['iterations'] for x in group for e in x['T']),
                    'T_zero_iterations':sum(e['iterations']==0 for x in group for e in x['T']),
                    'T_correctors_max':max(len(x['T']) for x in group),
                    'T_final_epsilon_over_1e_6_steps':sum(x['epsilon'][-1]['max']>1e-6 for x in group),
                    'p_solves':sum(len(x['p_rgh']) for x in group),'p_iterations':sum(e['iterations'] for x in group for e in x['p_rgh']),
                    'p_zero_iterations':sum(e['iterations']==0 for x in group for e in x['p_rgh'])})
            result['time_bins']=bins
            result['pressure_corrector_positions']={str(i+1):stats([dict(p_rgh=[x['p_rgh'][i]]) for x in steps],'p_rgh') for i in range(3)}
            result['thermal_features']={
                'first_step_multiple_T_solves':next(({'step':x['step'],'time_s':x['time_s'],'T_solves':len(x['T'])} for x in steps if len(x['T'])>1),None),
                'max_correctors_per_step':max(len(x['T']) for x in steps),
                'steps_21_correctors':sum(len(x['T'])==21 for x in steps),
                'steps_last_epsilon_residual_gt_1e_6':sum(x['epsilon'][-1]['max']>1e-6 for x in steps),
                'last_epsilon_residual_max':max(x['epsilon'][-1]['max'] for x in steps),
                'first_unresolved_step':next(({'step':x['step'],'time_s':x['time_s'],'T_solves':len(x['T']),'last_max_epsilon_residual':x['epsilon'][-1]['max']} for x in steps if x['epsilon'][-1]['max']>1e-6),None)}
            (out/'per-step.json').write_text(json.dumps(steps,indent=2)+'\n')
    assert len({r['event_trace_sha256'] for r in result['runs']})==1,'native/timed event traces differ'
    result['all_four_event_traces_identical']=True
    result['source_sha_unchanged']=before=={str(p.relative_to(ROOT)):digest(p) for p in files}
    assert result['source_sha_unchanged']
    result['status']='READ_ONLY_TP_ANALYSIS_PASSED';result['analysis_seconds']=time.monotonic()-started
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (out/'time-bins.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(result['time_bins'][0]),lineterminator='\n');writer.writeheader();writer.writerows(result['time_bins'])
    print(json.dumps({k:result[k] for k in ['status','analysis_seconds','thermal_features','pressure_corrector_positions']},indent=2))
    print((out/'time-bins.csv').read_text())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.absolute()
    assert out.resolve().is_relative_to(ROOT/'validation')
    analyze(out)
