"""Standalone Streamlit app. It does not replace or resume V20 C1/C2."""
from pathlib import Path
from dataclasses import replace
import hashlib
import json
import os
import streamlit as st
from lab_config import VERSION,Config,load_config
from lab_io import read_json,DataError
from lab_jobs import start,alive,request_pause
from lab_data import extract_dataset

ROOT=Path('data/v21_universe_lab')
T={
 'title':'\u6bcd\u6c60\uff0b\u56e0\u5b50\u6b0a\u91cd\u7814\u7a76\u5ba4',
 'intro':'\u6bd4\u8f03\u6210\u4ea4\u91d1\u984d\u524d100 / 200 / 300 / 500\u6a94\uff0c\u8a13\u7df4\u671f\u9078\u6a21\u578b\uff0c\u5176\u5f8c\u671f\u9593\u9a57\u8b49\u3002\u4e0d\u81ea\u52d5\u4e0b\u55ae\u3002',
 'warning':'\u9996\u6b21\u9700\u8981\u5168\u5e02\u5834\u6b77\u53f2\u6210\u4ea4\u91d1\u984d\u3002\u514d\u8cbbAPI\u914d\u984d\u6703\u5f71\u97ff\u6642\u9593\uff1b\u53ef\u80fd\u9700\u6578\u5c0f\u6642\uff0c\u4e26\u975e\u6309\u4e00\u6b21\u5c31\u80fd\u5728\u5e7e\u5206\u9418\u5b8c\u6210\u3002\u4e0d\u6703\u4ee5150\u6a94\u4ee3\u66ff\u5168\u5e02\u5834\u3002',
 'start':'\u25b6 \u4e00\u9375\u57f7\u884c / \u7e8c\u8dd1',
 'pause':'\u66ab\u505c\uff08\u4fdd\u7559\u5feb\u53d6\uff09',
 'auto':'\u81ea\u52d5\u6536\u96c6\u73fe\u884c\u5b98\u65b9\u540d\u518a\u7684\u6b77\u53f2\u8cc7\u6599',
 'import':'\u532f\u5165\u5df2\u6574\u7406\u7684\u5e02\u5834\u8cc7\u6599ZIP',
 'limits':'\u73fe\u884c\u540d\u518a\u4e0d\u7b49\u65bc\u6b77\u53f2\u6210\u5206\u80a1\u3002\u81ea\u52d5\u6a21\u5f0f\u6703\u6a19\u793a\u5016\u5b58\u8005\u504f\u5dee\uff1b\u5e02\u503c\u53ca\u57fa\u672c\u9762\u8981\u53e6\u5099\u6b77\u53f2\u6642\u9ede\u8cc7\u6599\uff0c\u4e0d\u6703\u7528\u73fe\u503c\u5012\u586b\u3002',
 'download':'\u4e0b\u8f09\u5831\u544a',
}

def token():
    try:return str(st.secrets.get('FINMIND_TOKEN',os.getenv('FINMIND_TOKEN','')))
    except Exception:return os.getenv('FINMIND_TOKEN','')

st.set_page_config(page_title='Alpha Radar V21 Lab',layout='wide')
st.title(T['title']);st.caption(VERSION);st.write(T['intro']);st.warning(T['warning'])
cfg=load_config(Path(__file__).parent/'config.json')
mode=st.radio('Data source / \u8cc7\u6599\u4f86\u6e90',[T['auto'],T['import']],horizontal=True)
idir=None
with st.expander('\u8a2d\u5b9a\u8207\u8cc7\u6599\u9650\u5236',expanded=False):
    st.write(T['limits'])
    st.json(cfg.to_dict())
    st.caption('Optional FINMIND_TOKEN may be set in Streamlit Secrets. It is never written to exports. No Sponsor endpoint is used.')
if mode==T['import']:
    cfg=replace(cfg,source_mode='import')
    upload=st.file_uploader('Normalized market dataset (not v19_results)',type=['zip'])
    historical=st.checkbox('I am supplying dated historical membership.csv (source declaration, not independent certification)')
    caps=st.checkbox('Also compare market-cap Top-N (requires dated market_caps.csv)')
    extra=st.checkbox('Include PIT revenue / EPS / institutional factors (requires evidence.csv)')
    cfg=replace(cfg,requested_scope='HISTORICAL_MEMBERSHIP' if historical else 'CURRENT_OFFICIAL_SNAPSHOT',
                include_market_cap_pools=caps,enable_optional_factors=extra)
    if upload:
        data=upload.getvalue();digest=hashlib.sha256(data).hexdigest()
        idir=ROOT/'inputs'/digest
        marker=idir/'manifest.json'
        if not marker.exists():
            archive=ROOT/'uploads'/(digest+'.zip');archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(data)
            try:extract_dataset(archive,idir)
            except Exception as e:st.error(str(e));st.stop()
    else:st.info('Upload dataset prepared using DATA_CONTRACT.md; a prior 150-stock report is not sufficient.')
col1,col2=st.columns(2)
if col1.button(T['start'],type='primary',disabled=(mode==T['import'] and not idir)):
    try:
        last=read_json(ROOT/'latest.json')
        last_state=read_json(Path(last['run'])/'state.json') if last.get('run') else {}
        if last_state.get('status') in ('PAUSED','RUNNING'):
            cfg=Config(**last['config']);idir=last.get('input_dir')
        cfg.validate();start(ROOT,cfg,token(),idir)
    except Exception as e:st.error(str(e))
latest=read_json(ROOT/'latest.json')
if col2.button(T['pause'],disabled=not latest):
    request_pause(latest['run'])

@st.fragment(run_every='3s')
def monitor():
    item=read_json(ROOT/'latest.json')
    if not item:st.info('\u5c1a\u672a\u555f\u52d5\u3002');return
    run=Path(item['run']);state=read_json(run/'state.json')
    st.subheader(str(state.get('status','STARTING'))+' | '+str(state.get('phase','')))
    st.write(state.get('message','Preparing ...'))
    total=state.get('total');done=state.get('done')
    if total and done is not None:st.progress(min(1.,max(0.,done/total)),text=f'{done} / {total}')
    if state.get('wait_seconds'):st.caption('Quota wait seconds: '+str(state['wait_seconds']))
    if state.get('status')=='RUNNING' and not alive(ROOT):
        st.warning('Worker process was restarted. Click resume; files must still exist. Cloud local storage is not guaranteed persistent.')
    if (run/'REPORT.txt').exists():
        report=(run/'REPORT.txt').read_text(encoding='utf-8-sig');st.text(report)
        st.download_button(T['download']+' TXT',report.encode('utf-8-sig'),'LAB_REPORT.txt','text/plain',on_click='ignore')
        for name in ('selected_models.json','results.json','LAB_RESULTS.zip'):
            p=run/name
            if p.exists() and p.stat().st_size<30*1024*1024:
                st.download_button(T['download']+' '+name,p.read_bytes(),name,
                                  'application/zip' if name.endswith('.zip') else 'application/json',on_click='ignore')
        st.caption('Large raw inputs stay in the local cache. Download buttons never rerun a study.')
monitor()
