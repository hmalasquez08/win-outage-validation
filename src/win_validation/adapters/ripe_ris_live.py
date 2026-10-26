"""Short, bounded RIPE RIS Live read-only subscription for candidate origin ASNs."""
from __future__ import annotations
import json, time
from websockets.sync.client import connect

def collect(asns: dict[str, int], duration_seconds: int = 12) -> dict:
    if not 1 <= duration_seconds <= 30:
        raise ValueError('RIS validation duration must be between 1 and 30 seconds')
    started=time.time(); messages=[]; subscriptions=[]; error=None
    url='wss://ris-live.ripe.net/v1/ws/?client=win-outage-validation'
    try:
        with connect(url, open_timeout=10, close_timeout=2, max_size=2_000_000) as ws:
            for operator, asn in asns.items():
                sub={'type':'ris_subscribe','data':{'path':f'{asn}$','socketOptions':{'acknowledge':True}}}
                ws.send(json.dumps(sub)); subscriptions.append({'operator':operator,'origin_asn':asn,'filter':f'{asn}$'})
            deadline=time.monotonic()+duration_seconds
            while time.monotonic()<deadline:
                try: message=json.loads(ws.recv(timeout=min(1.0,max(.05,deadline-time.monotonic()))))
                except TimeoutError: continue
                except Exception as exc:
                    if type(exc).__name__ in ('ConnectionClosedOK','ConnectionClosedError'): break
                    raise
                if message.get('type')=='ris_message':
                    data=message.get('data') or {}
                    message_asns=[str(x) for x in (data.get('path') or []) if isinstance(x,(int,str))]
                    matches=[op for op,asn in asns.items() if str(asn) in message_asns]
                    messages.append({'type':message.get('type'),'data':data,'matched_candidate_operators':matches})
                elif message.get('type')=='ris_error':
                    error=(message.get('data') or {}).get('message','RIS error')
    except Exception as exc: error=f'{type(exc).__name__}: {exc}'
    ended=time.time()
    return {'source_id':'ripe_ris_live','endpoint':url,'subscribed_at_unix':started,'ended_at_unix':ended,'duration_seconds':round(ended-started,3),'subscriptions':subscriptions,'message_count':len(messages),'messages':messages,'error':error,'interpretation':'Short live sample; no events is not evidence that routing is healthy or that coverage is absent.'}
