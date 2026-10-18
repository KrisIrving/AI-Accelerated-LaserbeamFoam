#!/usr/bin/env python3
"""DEC-011: one retained three-run M1 batch on this perf-blocked workstation.

Uses existing native preparation, runners, checks and feedback exporter. Never
changes solver code, retries a case, resumes, cleans or installs anything.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import time

import export_smoke_feedback as feedback
from check_smoke_case import gnu_time_record

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def entries(path):
    return {line.split(None,1)[1].strip(): line.split()[0] for line in path.read_text().splitlines()}


def stability(values):
    median = statistics.median(values)
    cv = statistics.stdev(values)/statistics.mean(values)
    spread = (max(values)-min(values))/median
    return {"values_seconds":values,"median_seconds":median,"min_seconds":min(values),
            "max_seconds":max(values),"mean_seconds":statistics.mean(values),
            "sample_sd_seconds":statistics.stdev(values),"sample_cv":cv,
            "range_over_median":spread,"stable_for_sampling":cv<=0.05 and spread<=0.10,
            "criterion":"sample CV<=5% and range/median<=10%; numerical standards unchanged"}


def descendants(pid):
    found=[]
    pending=[pid]
    while pending:
        child=pending.pop(); found.append(child)
        try:
            pending.extend(map(int,Path(f'/proc/{child}/task/{child}/children').read_text().split()))
        except (OSError,ValueError):
            pass
    return found


def solver_telemetry(pid, elapsed):
    for child in descendants(pid):
        proc=Path('/proc')/str(child)
        try:
            if proc.joinpath('comm').read_text().strip()!='laserbeamFoam':
                continue
            state={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in (proc/'status').read_text().splitlines() if ':' in line}
            io={k:int(v) for k,v in (line.split(':',1) for line in (proc/'io').read_text().splitlines())}
            return {"elapsed_batch_seconds":elapsed,"pid":child,"threads":int(state['Threads']),
                    "rss_kib":int(state['VmRSS'].split()[0]),"io":io,
                    "cpu0_frequency_khz":Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq').read_text().strip()}
        except (OSError,ValueError,KeyError):
            continue
    return None


def run_batch(out):
    started=time.monotonic(); deadline=started+1800
    marker=out/'.batch-started'; marker.mkdir()
    freeze=json.loads((ROOT/'benchmarks/performance/M1-stage2.json').read_text())
    state={"schema":"stage2-m1-batch-v1","decision":"DEC-011","status":"RUNNING",
           "started_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
           "commit":subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
           "batch_budget_seconds":1800,"resource_policy":"MONITORED_ONLY",
           "cpu_affinity":[0],"numeric_threads":1,"runs":[],"freeze":freeze,
           "sampling":{"status":"BLOCKED","solver_attempted":False,
                       "perf_probe_exit":int((out/'perf-permission-probe.exit.txt').read_text()),
                       "perf_event_paranoid":Path('/proc/sys/kernel/perf_event_paranoid').read_text().strip(),
                       "probe_log_sha256":digest(out/'perf-permission-probe.log'),
                       "overhead":"NOT_MEASURABLE_NO_SAMPLING_RUN"},"stages":[]}
    assert state['sampling']['perf_probe_exit']!=0, 'Host sampling preflight changed; review actual supported sampling path before this host-specific batch'
    build=out/'build'
    current=None

    def save():
        state['elapsed_seconds']=time.monotonic()-started
        temp=out/'batch.json.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(out/'batch.json')

    def remaining():
        if time.monotonic()>=deadline:
            raise TimeoutError('30-minute batch budget exhausted; stop without retry')

    def stage(name, command, time_path=None, pin=False):
        nonlocal current
        remaining()
        log=out/(name+'.log');timer=time_path or out/(name+'.time.txt')
        if log.exists() or timer.exists():
            raise ValueError('stage evidence exists; refusing overwrite: '+name)
        command=['/usr/bin/time','-v','-o',str(timer),*command]
        if pin:command=['taskset','-c','0',*command]
        rec={"name":name,"started_seconds":time.monotonic()-started}
        state['stages'].append(rec);state['current_stage']=name;save()
        print('STAGE_START',name,flush=True)
        with log.open('xb') as stream:
            current=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            last_sample=0
            while current.poll() is None:
                if time.monotonic()>=deadline:
                    os.killpg(current.pid,signal.SIGTERM)
                    try:current.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(current.pid,signal.SIGKILL);current.wait()
                    rec['exit']=current.returncode;save()
                    raise TimeoutError('batch deadline during '+name+'; logs retained')
                if time.monotonic()-last_sample>=1:
                    sample=solver_telemetry(current.pid,time.monotonic()-started)
                    if sample:
                        with (out/(name+'.telemetry.jsonl')).open('a') as f:f.write(json.dumps(sample)+'\n')
                    last_sample=time.monotonic()
                time.sleep(0.2)
            rec.update(exit=current.returncode,finished_seconds=time.monotonic()-started)
        rec['gnu_time']=gnu_time_record(timer)
        save();print('STAGE_END',name,'exit',rec['exit'],flush=True)
        if rec['exit']!=0:raise RuntimeError(name+' failed; no later case or retry')
        remaining()
        return rec

    try:
        # Preserve existing generated build logs before the unchanged Allwmake rewrites them.
        for base in ('src','applications'):
            for old in (ROOT/base).rglob('log.Allwmake'):
                dest=out/'previous-generated-build-logs'/Path(str(old.relative_to(ROOT))+'.txt')
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,dest)
        stage('build',['bash','scripts/validate_build.sh','--jobs','8','--report-dir',str(build)])
        state['build']={"binary_sha256":digest(build/'install/bin/laserbeamFoam'),
            "libraries":{p.name:digest(p) for p in sorted((build/'install/lib').glob('*.so'))},
            "binary_manifest_sha256":digest(build/'binary.sha256'),
            "library_manifest_sha256":digest(build/'custom-libraries.sha256')}
        state['frozen_initialized_sha256']=None
        for index in range(1,4):
            remaining();label=f'baseline-{index}'
            case=ROOT/'runs'/f'{out.name}-{label}'
            run={"id":label,"case_relative":str(case.relative_to(ROOT)),"status":"PREPARING",
                 "started_seconds":time.monotonic()-started}
            state['runs'].append(run);save()
            stage(label+'-prepare',['python3','scripts/prepare_m_case.py','--experiment','M1','--run-dir',str(case),'--build-dir',str(build)])
            if entries(case/'inputs.sha256')!=freeze['input_sha256']:
                raise ValueError('prepared inputs differ from approved original M1')
            stage(label+'-mesh',['bash',str(case/'Allrun'),'mesh'],case/'time.workflow.mesh.txt',True)
            initialized=entries(case/'initialized.sha256')
            if state['frozen_initialized_sha256'] is None:
                state['frozen_initialized_sha256']=initialized
                state['frozen_initial_snapshot_manifest_sha256']=digest(case/'initialized.sha256')
            if initialized!=state['frozen_initialized_sha256']:
                raise ValueError('mesh/initial fields differ from frozen first native initialization')
            run['inputs_manifest_sha256']=digest(case/'inputs.sha256')
            run['initialized_manifest_sha256']=digest(case/'initialized.sha256')
            run['status']='MESH_PASSED';save()
            stage(label+'-solve',['bash',str(case/'Allrun'),'solve'],case/'time.workflow.solve.txt',True)
            report=json.loads((case/'m.json').read_text())
            if report['status']!='EXPLORATION_CHECKS_PASSED' or report['issues']:
                raise ValueError('full original M checks did not pass')
            run['check']={"status":report['status'],"issues":report['issues'],"steps":report['steps'],
                          "output_times_s":report['output_times_s'],"field_files":sum(map(len,report['fields'].values())),
                          "uniform_times":len(report['uniform']),"full_check_body_seconds":report['offline_check_wall_seconds']}
            check_calls=[]
            for action in ('mesh','solve'):
                check_calls.extend(map(float,re.findall(r'Offline checker seconds:\s*([0-9.eE+-]+)',(out/(label+'-'+action+'.log')).read_text())))
            run['check']['all_check_body_seconds_by_call']=check_calls
            run['check']['all_check_body_seconds_sum']=sum(check_calls)
            run['solver_time']=gnu_time_record(case/'time.laserbeamFoam.txt')
            run['mesh_wrapper_time']=gnu_time_record(case/'time.workflow.mesh.txt')
            run['solve_wrapper_time']=gnu_time_record(case/'time.workflow.solve.txt')
            run['solver_gnu_time_text']=(case/'time.laserbeamFoam.txt').read_text()
            run['numerical_report_sha256']=digest(case/'m.json')
            remaining();export_start=time.monotonic()
            bundle=feedback.export_feedback(case,check_exit_code=0,profile='m')
            run['feedback_export_seconds']=time.monotonic()-export_start
            run['feedback']={k:v for k,v in bundle.items() if k not in ('archive_path','sha256_path','files_path')}
            if bundle['archive_status']!='EXPORTED' or bundle['collection_status']!='COMPLETE':
                raise ValueError('feedback export incomplete; stop later cases')
            archives=list((case/'feedback').glob('*.tar.gz'));assert len(archives)==1
            run['archive_sha256']=digest(archives[0]);run['archive_bytes']=archives[0].stat().st_size
            run['case_bytes']=sum(p.stat().st_size for p in case.rglob('*') if p.is_file())
            run['complete_wall_seconds']=time.monotonic()-started-run['started_seconds']
            run['status']='PASSED'
            state['new_batch_directory_bytes']=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())+sum(r.get('case_bytes',0) for r in state['runs'])
            save();print('CASE_PASSED',label,'solver',run['solver_time']['wall_seconds'],'complete',run['complete_wall_seconds'],flush=True)
            if run['solver_time']['max_rss_kib']>8388608 or state['new_batch_directory_bytes']>3221225472:
                raise RuntimeError('observed RSS/data warning crossed; retain completed case and stop later runs')
            remaining()
        state['stability']=stability([r['solver_time']['wall_seconds'] for r in state['runs']])
        state['status']='THREE_BASELINES_PASSED_SAMPLING_BLOCKED'
        state['sampling']['baseline_stability_eligible']=state['stability']['stable_for_sampling']
        state['sampling']['modules']={name:{"share":None,"evidence":"UNMEASURED_NO_CALL_STACKS"} for name in ('ray_heat_source','VOF','properties_phase_change','linear_solves','IO','unknown')}
    except Exception as exc:
        state['status']='STOPPED';state['error']=type(exc).__name__+': '+str(exc)
        if current and current.poll() is None:
            os.killpg(current.pid,signal.SIGTERM);current.wait()
        print('BATCH_STOPPED',state['error'],flush=True)
    finally:
        state['current_stage']='FINISHED';state['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
    print('BATCH_FINAL',state['status'],state['elapsed_seconds'],'seconds',flush=True)
    return 0 if state['status']=='THREE_BASELINES_PASSED_SAMPLING_BLOCKED' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-dir',type=Path,required=True)
    args=parser.parse_args();out=args.batch_dir.resolve(strict=True)
    if not out.is_relative_to(ROOT/'validation') or os.environ.get('WM_PROJECT_VERSION')!='v2512':
        raise SystemExit('Require existing private validation directory and loaded v2512')
    raise SystemExit(run_batch(out))
