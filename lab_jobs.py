"""One-click finite job, disk checkpoints, OS single-writer lock, UI-free worker."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import os
import threading
import traceback
import pandas as pd
from lab_config import Config,VERSION
from lab_io import Store,JobLock,PauseRequested,SourceBlocked,DataError,atomic_json,read_json,code_hash,sha,frame_write
from lab_data import build_dataset
from lab_candidates import candidate_registry
from lab_backtest import build_cases,evaluate_grid
from lab_search import nested_study
from lab_report import write_report

_THREADS={};_THREAD_LOCK=threading.Lock()

def now():return datetime.now(timezone.utc).isoformat()

def input_hash(directory):
    if not directory:return ''
    root=Path(directory);h=hashlib.sha256()
    for p in sorted(root.iterdir()):
        if p.is_file():h.update(p.name.encode());h.update(sha(p).encode())
    return h.hexdigest()

def identifier(cfg,idir=None):
    key={'config':cfg.to_dict(),'code_hash':code_hash(),'input_hash':input_hash(idir),'version':VERSION}
    return hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()[:20]


def run_pipeline(root,cfg,token=None,input_dir=None):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    job=identifier(cfg,input_dir);run=root/'runs'/job
    run.mkdir(parents=True,exist_ok=True)
    statefile=run/'state.json';pause=run/'PAUSE'
    state=read_json(statefile)
    if state.get('status')=='COMPLETE':return run
    with JobLock(root/'worker.lock'):
        def check():
            if pause.exists():raise PauseRequested('Paused; resume uses existing cache')
        def progress(**kw):
            old=read_json(statefile)
            old.update(wait_seconds=0);old.update(kw);old.update(status='RUNNING',updated_at=now(),job_id=job,pid=os.getpid())
            atomic_json(statefile,old)
        protocol=read_json(run/'protocol.json')
        if not protocol:
            protocol={'version':VERSION,'registered_at':now(),'code_hash':code_hash(),
                      'config':cfg.to_dict(),'input_hash':input_hash(input_dir),
                      'run_id':job,'finite_search':True,'automatic_orders_authorized':False,
                      'scope_is_not_reconstructed_from_successfully_downloaded_symbols':True}
            atomic_json(run/'protocol.json',protocol)
        candidates=candidate_registry(cfg)
        atomic_json(run/'candidates.json',candidates)
        atomic_json(root/'latest.json',{'job_id':job,'run':str(run),'config':cfg.to_dict(),'input_dir':str(input_dir) if input_dir else None})
        progress(phase='START',message='Starting/resuming finite research protocol',done=0,total=None)
        try:
            # Import datasets get their own DB. Automatic histories can reuse the
            # amount/adjusted cache between runs; each study retains its own roster.
            store_root=run/'import_cache' if cfg.source_mode=='import' else root/'cache'
            store=Store(store_root)
            ready=read_json(run/'prepared.json')
            cachefiles=['features.csv.gz','labels.csv.gz','monthly_pools.csv.gz','calendar.json','source_scope.json']
            usable=ready and all((run/p).is_file() and sha(run/p)==ready.get(p) for p in cachefiles)
            if usable:
                snap=pd.read_csv(run/'features.csv.gz',parse_dates=['date'])
                labels=pd.read_csv(run/'labels.csv.gz',parse_dates=['date','entry','exit'])
                pools=pd.read_csv(run/'monthly_pools.csv.gz',parse_dates=['date'])
                cal=pd.DatetimeIndex(read_json(run/'calendar.json'));source=read_json(run/'source_scope.json')
                progress(phase='CACHE',message='Validated feature/outcome checkpoint restored')
            else:
                snap,labels,pools,cal,source=build_dataset(store,cfg,run,progress,check,token,input_dir)
                atomic_json(run/'prepared.json',{p:sha(run/p) for p in cachefiles})
            check()
            cov=[{'factor':c.removeprefix('rank_'),'coverage':float(snap[c].notna().mean())} for c in snap if c.startswith('rank_')]
            frame_write(run/'feature_coverage.csv',pd.DataFrame(cov))
            progress(phase='CASES',message='Building shared comparison calendar and same-pool controls')
            cases=build_cases(snap,labels,pools,cfg)
            grids=evaluate_grid(cases,candidates,cfg,progress,check)
            result=nested_study(grids,cases,candidates,cal,cfg,run,source,progress,check)
            check();progress(phase='EXPORT',message='Writing verified small report files')
            write_report(result,run)
            atomic_json(statefile,{'status':'COMPLETE','phase':'DONE','job_id':job,'updated_at':now(),
                'message':'Finite study complete; read all scope/coverage limits before interpreting the selected model.',
                'run':str(run),'verdicts':{h:x['verdict'] for h,x in result['models'].items()},'done':1,'total':1})
        except PauseRequested as e:
            atomic_json(statefile,{'status':'PAUSED','job_id':job,'updated_at':now(),'message':str(e)})
        except (DataError,SourceBlocked) as e:
            atomic_json(statefile,{'status':'BLOCKED','job_id':job,'updated_at':now(),'message':str(e),
                                  'results_approved':False,'cached_work_retained':True})
        except Exception as e:
            # Never log tokens or request URLs containing tokens.
            (run/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            atomic_json(statefile,{'status':'ERROR','job_id':job,'updated_at':now(),'message':type(e).__name__+': '+str(e),
                                  'results_approved':False,'cached_work_retained':True})
    return run


def start(root,cfg,token=None,input_dir=None):
    root=Path(root);job=identifier(cfg,input_dir);run=root/'runs'/job
    with _THREAD_LOCK:
        running=_THREADS.get(str(root.resolve()))
        if running and running.is_alive():return run
        if read_json(run/'state.json').get('status')=='COMPLETE':return run
        run.mkdir(parents=True,exist_ok=True);(run/'PAUSE').unlink(missing_ok=True)
        thread=threading.Thread(target=run_pipeline,args=(root,cfg,token,input_dir),daemon=True)
        _THREADS[str(root.resolve())]=thread;thread.start()
    return run

def alive(root):
    t=_THREADS.get(str(Path(root).resolve()))
    return bool(t and t.is_alive())

def request_pause(run):
    p=Path(run);p.mkdir(parents=True,exist_ok=True);(p/'PAUSE').write_text('pause',encoding='ascii')
