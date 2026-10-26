from __future__ import annotations
import argparse, csv, hashlib, json, os, re, socket, ssl, sys, time, urllib.error, urllib.parse, urllib.request, certifi
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path.cwd(); EV=ROOT/'evidencias'; REPORTS=ROOT/'reports'; MANIFEST=EV/'manifest.jsonl'
OPS={'movistar':'AS6147','claro':'AS12252','entel':'AS21575','bitel':'AS262210'}
# Public endpoints, all GET/read-only. No request that creates measurements or consumes credits.
SOURCES={
 'ripestat':('https://stat.ripe.net/data/country-resource-stats/data.json?resource=PE','network_inventory','public'),
 'ripestat_asn_movistar':('https://stat.ripe.net/data/as-overview/data.json?resource=AS6147','network_inventory','public'),
 'ripestat_asn_claro':('https://stat.ripe.net/data/as-overview/data.json?resource=AS12252','network_inventory','public'),
 'ripestat_asn_entel':('https://stat.ripe.net/data/as-overview/data.json?resource=AS21575','network_inventory','public'),
 'ripestat_asn_bitel':('https://stat.ripe.net/data/as-overview/data.json?resource=AS262210','network_inventory','public'),
 'ripe_atlas':('https://atlas.ripe.net/api/v2/probes/?country_code=PE&status=1&limit=100','active_reachability','public'),
 'ooni':('https://api.ooni.io/api/v1/measurements?probe_cc=PE&limit=100','active_reachability','public'),
 'usgs':('https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime='+(datetime.now(timezone.utc)-timedelta(days=30)).date().isoformat()+'&minlatitude=-19&maxlatitude=0&minlongitude=-82&maxlongitude=-68','external_context','public'),
 'geoboundaries_adm1':('https://www.geoboundaries.org/api/current/gbOpen/PER/ADM1/','geography','public'),
 'geoboundaries_adm2':('https://www.geoboundaries.org/api/current/gbOpen/PER/ADM2/','geography','public'),
 'geoboundaries_adm3':('https://www.geoboundaries.org/api/current/gbOpen/PER/ADM3/','geography','public'),
 'infobip_status':('https://external-connectivity-status.infobip.com/','carrier_messaging','official_status_page_feed_check'),
 'twilio_status':('https://status.twilio.com/api/v2/summary.json','carrier_messaging','public_status_api'),
 'telesign_status':('https://status.telesign.com/api/v2/summary.json','carrier_messaging','public_status_api'),
 'sinch_status':('https://status.sinch.com/api/v2/summary.json','carrier_messaging','public_status_api'),
}
AUTH={'cloudflare_radar':'https://developers.cloudflare.com/radar/','x_official':'https://developer.x.com/en/docs','twexapi_x':'https://twexapi.io/get-started','globalping_account':'https://globalping.io/docs/api.globalping.io'}
def utc(): return datetime.now(timezone.utc).isoformat()
def load_env():
 # Minimal .env reader: values stay in memory and are never logged or serialized.
 out=os.environ.copy(); p=ROOT/'.env'
 if p.exists():
  for line in p.read_text(encoding='utf-8').splitlines():
   line=line.strip()
   if line and not line.startswith('#') and '=' in line:
    k,v=line.split('=',1); out.setdefault(k.strip(),v.strip().strip('"\''))
 return out
def mkdirs():
 for p in ['api_responses','historical','geographic','temporal','quotas','pricing','licensing','resilience','errors','execution','x_accounts','integration']: (EV/p).mkdir(parents=True,exist_ok=True)
 REPORTS.mkdir(exist_ok=True)
 if not MANIFEST.exists(): MANIFEST.write_text('',encoding='utf-8')
def request(source,url,kind,token=None,auth_scheme='Bearer',method='GET',payload=None,sanitizer=None,max_response_bytes=10_000_000,user_agent=None,timeout=20):
 started=time.monotonic(); at=utc(); status=None; err=None; headers={}; body=b''
 try:
  req_headers={'User-Agent':user_agent or 'win-outage-validation/0.1 (research; contact: local validation)','Accept':'application/json, application/geo+json, application/xml, text/xml, application/rss+xml, application/atom+xml, text/csv, */*'}
  if token: req_headers['Authorization']=f'{auth_scheme} {token}'
  data=json.dumps(payload).encode() if payload is not None else None
  if data is not None: req_headers['Content-Type']='application/json'
  req=urllib.request.Request(url,data=data,headers=req_headers,method=method)
  with urllib.request.urlopen(req,timeout=timeout,context=ssl.create_default_context(cafile=certifi.where())) as response:
   status=response.status; headers=dict(response.headers); body=response.read(max_response_bytes)
 except urllib.error.HTTPError as e:
  status=e.code; headers=dict(e.headers); body=e.read(10_000_000); err=f'HTTPError: {e.code} {e.reason}'
 except Exception as e:
  err=f'{type(e).__name__}: {e}'; body=json.dumps({'error':err,'url':url,'observed_at_utc':at}).encode()
 latency=round(time.monotonic()-started,3); ok=status is not None and 200<=status<300
 truncated=bool(headers.get('Content-Length','').isdigit() and int(headers['Content-Length'])>len(body))
 sub='errors' if not ok else 'api_responses/'+source
 path=EV/sub; path.mkdir(parents=True,exist_ok=True)
 content_type=headers.get('Content-Type','').lower()
 ext='.json' if 'json' in content_type or body[:1] in (b'{',b'[') else ('.xml' if ('xml' in content_type or body.lstrip().startswith(b'<?xml')) else ('.csv' if 'csv' in content_type else '.bin'))
 stored=sanitizer(body) if sanitizer and ok else body
 artifact=path/(at.replace(':','').replace('-','')+ext); artifact.write_bytes(stored); digest=hashlib.sha256(stored).hexdigest()
 eid=source+'-'+digest[:12]
 attempt=('TRUNCATED_RESPONSE' if truncated else ('AUTH_BLOCKED' if status in (401,403) else ('RATE_LIMITED' if status==429 else ('TRANSIENT_ERROR' if status is None or (status is not None and status>=500) else ('VALIDATION_ERROR' if status is not None and status>=400 else ('SUCCESS_WITH_EVIDENCE' if ok else 'UNAVAILABLE'))))))
 query=urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
 signature_input=json.dumps({'method':method,'endpoint':urllib.parse.urlparse(url)._replace(query='',fragment='').geturl(),'query':query,'payload':payload},sort_keys=True,default=str,separators=(',',':'))
 query_signature=hashlib.sha256(signature_input.encode()).hexdigest()
 record={'evidence_id':eid,'source_id':source,'operator':None,'country':'PE','observed_at_utc':at,'source_published_at_utc':None,'artifact_path':artifact.relative_to(ROOT).as_posix(),'sha256':digest,'result_status':attempt,'attempt_status':attempt,'query_signature':query_signature,'window_start':(query.get('from') or query.get('starttime') or [None])[0],'window_end':(query.get('until') or query.get('endtime') or [None])[0],'next_retry_at_utc':None,'related_report':'reports/validation_report.md','url':url,'http_status':status,'latency_seconds':latency,'error':err,'response_bytes':len(stored),'original_response_bytes':len(body),'truncated':truncated,'redaction_applied':bool(sanitizer),'headers':{k:v for k,v in headers.items() if k.lower() in ('content-type','etag','last-modified','retry-after','content-length','x-ratelimit-limit','x-ratelimit-remaining','x-ratelimit-reset')}}
 with MANIFEST.open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n')
 return record,body
def authenticated_stage():
 env=load_env(); results=[]
 cf=env.get('CLOUDFLARE_API_TOKEN','').strip()
 if cf:
  # Official Cloudflare token verification endpoint.
  r,b=request('cloudflare_token_verify','https://api.cloudflare.com/client/v4/user/tokens/verify','auth',cf)
  try: valid=bool(json.loads(b).get('success'))
  except Exception: valid=False
  r['result_status']='AUTH_PASS' if valid else ('AUTH_BLOCKED' if r.get('http_status') in (401,403) else r['result_status'])
  if valid:
   # Documented first-request endpoint, bounded 7-day PE aggregate; no operator attribution claimed here.
   u='https://api.cloudflare.com/client/v4/radar/http/summary/device_type?dateRange=7d&location=PE&format=json'
   x,body=request('cloudflare_radar_pe_device_summary',u,'traffic_dns',cf); results.append(x)
   try:
    obj=json.loads(body); x['sample_count']=len(obj.get('result',{}).get('series_0',{}).get('timestamps',[]))
   except Exception: pass
  results.append(r)
 else: print('Cloudflare token absent; AUTH_BLOCKED_NO_CREDENTIAL')
 tw=env.get('TWEXAPI_API_KEY','').strip()
 if tw:
  # Reuse last documented balance response; avoid repeated balance calls (observed to deduct 5 credits each).
  old=[json.loads(line) for line in MANIFEST.read_text(encoding='utf-8').splitlines() if line.strip() and json.loads(line).get('source_id')=='twexapi_balance'] if MANIFEST.exists() else []
  if old:
   prior=old[-1]; saved=json.loads((ROOT/prior['artifact_path']).read_text(encoding='utf-8')); data=saved.get('data',{}); balance=float(data.get('balance',0) if isinstance(data,dict) else data or 0); balance_http=prior.get('http_status')
  else:
   r,b=request('twexapi_balance','https://api.twexapi.io/balance','auth',tw); results.append(r); saved=json.loads(b); data=saved.get('data',{}); balance=float(data.get('balance',0) if isinstance(data,dict) else data or 0); balance_http=r.get('http_status')
  print(f'TwexAPI cached balance check: HTTP={balance_http}, free-trial-floor-met={balance>=19000}; no extra balance request issued.')
  if balance>=19000 and balance_http==200:
   # Handles below are only those linked by the operators' official Peruvian homepages.
   # One page per operator, <=20 returned tweets; content/author identifiers are never persisted.
   accounts={'movistar':('MovistarPeru','https://www.movistar.com.pe/'),'claro':('claroperu','https://www.claro.com.pe/'),'bitel':('bitelperu','https://bitel.com.pe/')}
   def redact_x(raw):
    try:
     obj=json.loads(raw); texts=[]; list_counts={}
     def inspect(value,path='$'):
      if isinstance(value,dict):
       for key,item in value.items():
        if key.lower() in ('text','full_text','content','body','tweet_text') and isinstance(item,str): texts.append(item.lower())
        inspect(item,path+'.'+key)
      elif isinstance(value,list):
       list_counts[path]=len(value)
       for i,item in enumerate(value[:25]): inspect(item,path+'[]')
     inspect(obj)
     terms=['sin internet','sin señal','intermitencia','caída','fibra','datos móviles','internet lento']
     summary={'redacted':True,'top_level_keys':sorted(obj.keys()) if isinstance(obj,dict) else [],'text_fields_detected':len(texts),'keyword_match_count':sum(any(t in text for t in terms) for text in texts),'service_term_counts':{t:sum(t in text for text in texts) for t in ('fijo','móvil','sms','voz','fibra','internet')},'array_lengths':list_counts}
     return json.dumps(summary,ensure_ascii=False).encode()
    except Exception: return json.dumps({'redacted':True,'parse_error':'unrecognized response schema; user content omitted'}).encode()
   for operator,(handle,official_url) in accounts.items():
    query=f'to:{handle} ("sin internet" OR "sin señal" OR intermitencia OR fibra) since:{(datetime.now(timezone.utc)-timedelta(days=30)).date()} until:{datetime.now(timezone.utc).date()}'
    url='https://api.twexapi.io/twitter/advanced_search/page'
    x,raw=request('twexapi_x_'+operator,url,'human_reports',tw,'Bearer','POST',{'searchTerms':[query],'sortBy':'Latest'},redact_x)
    x['operator']=operator; results.append(x)
    print(f'TwexAPI {operator}: HTTP={x.get("http_status")}, sensitive post fields omitted from evidence; account identity linked from {official_url}')
   print('TwexAPI scope excluded Entel and institutions pending official-handle verification; no global keyword search performed.')
  else: print('TwexAPI content search not run: free Starter credits were not conclusively confirmed.')
 else: print('TwexAPI token absent; AUTH_BLOCKED_NO_CREDENTIAL')
 write_reports(results)
def run_ris():
 from .adapters.ripe_ris_live import collect
 mkdirs(); observed=utc(); result=collect({op:int(asn[2:]) for op,asn in OPS.items()},12)
 result['observed_at_utc']=observed
 body=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode()
 path=EV/'api_responses'/'ripe_ris_live'; path.mkdir(parents=True,exist_ok=True)
 artifact=path/(observed.replace(':','').replace('-','')+'.json'); artifact.write_bytes(body); digest=hashlib.sha256(body).hexdigest()
 status='SUCCESS_WITH_EVIDENCE' if result['message_count'] else ('UNAVAILABLE' if result['error'] else 'EMPTY_VALID_RESPONSE')
 record={'evidence_id':'ripe_ris_live-'+digest[:12],'source_id':'ripe_ris_live','operator':None,'country':None,'observed_at_utc':observed,'source_published_at_utc':None,'artifact_path':artifact.relative_to(ROOT).as_posix(),'sha256':digest,'result_status':status,'related_report':'reports/validation_report.md','url':result['endpoint'],'http_status':None,'latency_seconds':result['duration_seconds'],'error':result['error'],'response_bytes':len(body),'query':{'origin_asns':list(OPS.values()),'duration_seconds':12},'note':'WebSocket live-window; empty is not healthy/coverage-negative.'}
 with MANIFEST.open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n')
 print(f"RIS Live: {status}; messages={result['message_count']}; evidence={record['evidence_id']}")
 write_reports()
def run_all():
 mkdirs(); results=[]
 for source,(url,family,access) in SOURCES.items():
  r,b=request(source,url,family); results.append(r); print(f"{source}: {r['result_status']} HTTP={r['http_status']} {r['latency_seconds']}s {r['artifact_path']}")
  time.sleep(.25)
  results.extend(run_ioda_stage())
  write_reports(results)
def run_ioda_stage():
 results=[]; now=int(time.time()); start=now-30*86400
 for op,asn in OPS.items():
  code=asn.removeprefix('AS')
  meta_url='https://api.ioda.inetintel.cc.gatech.edu/v2/entities/query?'+urllib.parse.urlencode({'entityType':'asn','entityCode':code})
  mr,mb=request('ioda_entity_'+op,meta_url,'network_inventory'); results.append(mr)
  # Endpoint and field names are from the provider's published OpenAPI spec.
  data_url=f'https://api.ioda.inetintel.cc.gatech.edu/v2/signals/raw/asn/{code}?'+urllib.parse.urlencode({'from':start,'until':now,'maxPoints':500})
  sr,sb=request('ioda_'+op,data_url,'bgp_routing'); results.append(sr)
  events_url='https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events?'+urllib.parse.urlencode({'entityType':'asn','entityCode':code,'from':start,'until':now,'limit':100})
  er,eb=request('ioda_events_'+op,events_url,'bgp_routing'); results.append(er)
  try:
   obj=json.loads(eb); event_count=len(obj.get('data',[])) if isinstance(obj.get('data'),list) else 0
  except Exception: event_count=0
  print(f"IODA {op}: entity HTTP={mr['http_status']}, signals HTTP={sr['http_status']}, event HTTP={er['http_status']} count={event_count}, evidence={mr['evidence_id']}/{sr['evidence_id']}/{er['evidence_id']}")
 return results
def run_globalping_stage():
 # Only the documented GET inventory/limits endpoints are used; no POST measurements are created.
 mkdirs(); limits_rec,limits_raw=request('globalping_limits','https://api.globalping.io/v1/limits','measurement_inventory')
 def minimize(body):
  try:
   obj=json.loads(body); probes=obj if isinstance(obj,list) else obj.get('probes',obj.get('data',[])); probes=probes if isinstance(probes,list) else []
   pe=[p for p in probes if str((p.get('location') or {}).get('country','')).upper()=='PE']
   counts={}
   sanitized=[]
   for p in pe:
    loc=p.get('location') or {}; asn=str(loc.get('asn','unknown'))
    counts[asn]=counts.get(asn,0)+1
    sanitized.append({'country':'PE','asn':asn,'city':loc.get('city'),'region':loc.get('region'),'network':loc.get('network')})
   return json.dumps({'redacted':True,'total_online_inventory_rows':len(probes),'peru_probe_count_in_returned_inventory':len(pe),'peru_candidate_asn_counts':{asn:counts.get(asn.removeprefix('AS'),counts.get(asn,0)) for asn in OPS.values()},'peru_asn_counts':counts,'peru_rows_coarse_location':sanitized},ensure_ascii=False).encode()
  except Exception as e: return json.dumps({'redacted':True,'parse_error':type(e).__name__,'raw_fields_omitted':True}).encode()
 time.sleep(0.6)
 probe_rec,probe_raw=request('globalping_online_probe_inventory','https://api.globalping.io/v1/probes','measurement_inventory',sanitizer=minimize,max_response_bytes=100_000_000)
 try: summary=json.loads(minimize(probe_raw))
 except Exception: summary={}
 print(f"Globalping: limits HTTP={limits_rec['http_status']}; inventory HTTP={probe_rec['http_status']}; PE probes={summary.get('peru_probe_count_in_returned_inventory','unknown')}; tests created=0")
 write_reports([limits_rec,probe_rec])

def run_atlas_history_stage():
 # Read-only inventory of measurements attached to already identified PE probes.
 # Store only aggregate metadata; omit probe IDs, addresses, targets and result payloads.
 mkdirs()
 inventory=EV/'api_responses'/'ripe_atlas'
 candidates=[]
 for file in sorted(inventory.glob('*.json')):
  try:
   obj=json.loads(file.read_text(encoding='utf-8'))
   for probe in obj.get('results',[]):
    asn=str(probe.get('asn_v4') or probe.get('asn_v6') or '')
    op=next((name for name,value in OPS.items() if value.removeprefix('AS')==asn),None)
    if op and probe.get('id'):
     candidates.append((op,int(probe['id']),asn))
  except (OSError,ValueError,TypeError):
   continue
 # Deduplicate probes across archived inventory snapshots.
 candidates=sorted(set(candidates))
 summaries=[]
 for op,probe_id,asn in candidates:
  url=f'https://atlas.ripe.net/api/v2/probes/{probe_id}/measurements/?page_size=100'
  def summarize(raw):
   try:
    obj=json.loads(raw); rows=obj.get('results',[]) if isinstance(obj,dict) else []
    starts=[r.get('start_time') for r in rows if isinstance(r,dict) and r.get('start_time')]
    result={'redacted':True,'operator':op,'country':'PE','asn':asn,'http_page_count':obj.get('count'),
      'returned_page_rows':len(rows),'has_next_page':bool(obj.get('next')),
      'measurement_types':sorted({r.get('type','unknown') for r in rows if isinstance(r,dict)}),
      'first_start_time_in_returned_page':min(starts) if starts else None,
      'last_start_time_in_returned_page':max(starts) if starts else None,
      'ongoing_rows_in_returned_page':sum(r.get('status')=='Ongoing' for r in rows if isinstance(r,dict)),
      'note':'Public measurement inventory only; dates are measurement configuration start times, not recent result timestamps or outage evidence.'}
   except Exception:
    result={'redacted':True,'operator':op,'country':'PE','asn':asn,'parse_error':'unrecognized response schema'}
   return json.dumps(result,ensure_ascii=False).encode()
  rec,raw=request(f'ripe_atlas_measurements_{op}',url,'measurement_inventory',sanitizer=summarize)
  rec['operator']=op
  try: summary=json.loads(summarize(raw))
  except Exception: summary={}
  try:
   listing=json.loads(raw); count=int(listing.get('count',0)); page_size=100
   latest_page=(count+page_size-1)//page_size
   if latest_page>1:
    page_url=f'https://atlas.ripe.net/api/v2/probes/{probe_id}/measurements/?page_size={page_size}&page={latest_page}'
    page_rec,page_raw=request(f'ripe_atlas_measurements_latest_page_{op}',page_url,'measurement_inventory',sanitizer=summarize)
    page_rec['operator']=op
    page_obj=json.loads(page_raw); page_rows=page_obj.get('results',[]) if isinstance(page_obj,dict) else []
    starts=[m.get('start_time') for m in page_rows if isinstance(m,dict) and m.get('start_time')]
    summary['latest_page_returned_rows']=len(page_rows); summary['latest_page_start_range']=[min(starts),max(starts)] if starts else []
    summary['latest_page_evidence_id']=page_rec['evidence_id']
    # Read only the most recently configured public measurement result; never create a measurement.
    newest=max((m for m in page_rows if isinstance(m,dict) and m.get('start_time')),key=lambda m:m['start_time'],default=None)
    if newest and newest.get('id'):
     result_url=f"https://atlas.ripe.net/api/v2/measurements/{newest['id']}/latest/?probe_ids={probe_id}"
     def summarize_latest(result_body):
      try:
       result_obj=json.loads(result_body); values=[]
       if isinstance(result_obj,dict):
        for value in result_obj.values():
         values.extend(value if isinstance(value,list) else [value])
       timestamps=[]
       for value in values:
        if isinstance(value,dict):
         ts=value.get('stored_timestamp') or value.get('timestamp')
         if isinstance(ts,(int,float)):
          ts=datetime.fromtimestamp(ts,timezone.utc).isoformat()
         if isinstance(ts,str): timestamps.append(ts)
       out={'redacted':True,'operator':op,'country':'PE','asn':asn,'returned_result_count':len(values),
            'result_timestamps':timestamps,'measurement_configuration_start_time':newest.get('start_time'),
            'measurement_status':newest.get('status'),'note':'No targets, addresses, descriptions or result payloads retained.'}
      except Exception: out={'redacted':True,'operator':op,'parse_error':'unrecognized result schema'}
      return json.dumps(out,ensure_ascii=False).encode()
     result_rec,result_raw=request(f'ripe_atlas_latest_result_{op}',result_url,'measurement_result',sanitizer=summarize_latest)
     try: summary['latest_result_summary']=json.loads(summarize_latest(result_raw))
     except Exception: summary['latest_result_summary']={'parse_error':'summary unavailable'}
     summary['latest_result_evidence_id']=result_rec['evidence_id']
  except Exception as exc:
   summary['latest_page_or_result_error']=type(exc).__name__
  summaries.append({**summary,'evidence_id':rec['evidence_id'],'artifact_path':rec['artifact_path'],'http_status':rec['http_status']})
  print(f"RIPE Atlas {op}: HTTP={rec['http_status']}; public measurement inventory count={summary.get('http_page_count','unknown')}; recent result freshness not established")
  time.sleep(.25)
 csvpath=REPORTS/'atlas_measurement_inventory.csv'
 with csvpath.open('w',newline='',encoding='utf-8-sig') as f:
  fields=['operator','asn','http_page_count','returned_page_rows','has_next_page','measurement_types','first_start_time_in_returned_page','last_start_time_in_returned_page','latest_page_returned_rows','latest_page_start_range','latest_page_evidence_id','latest_result_evidence_id','latest_result_summary','ongoing_rows_in_returned_page','http_status','evidence_id','artifact_path','note']
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
  for row in summaries:
   row=dict(row); row['measurement_types']=';'.join(row.get('measurement_types',[])); row['latest_page_start_range']=json.dumps(row.get('latest_page_start_range',[])); row['latest_result_summary']=json.dumps(row.get('latest_result_summary',{}),ensure_ascii=False); row['note']=row.get('note',''); w.writerow({k:row.get(k,'') for k in fields})
 write_reports()
def write_reports(results=None):
 mkdirs(); records=[json.loads(x) for x in MANIFEST.read_text(encoding='utf-8').splitlines() if x.strip()]
 # latest execution/manifest are the source of truth; no fabricated utility claims.
 rows=[]
 for s in list(SOURCES)+[f'ioda_{x}' for x in OPS]+['cloudflare_radar','cloudflare_token_verify','cloudflare_radar_pe_device_summary','twexapi_x','twexapi_balance','globalping','x_official','osiptel_sisrep','indecopi']:
  matching=[x for x in records if x['source_id']==s]; latest=matching[-1] if matching else {}
  state=latest.get('result_status','NOT_TESTED'); rows.append({'source_id':s,'operator':latest.get('operator') or 'all/unknown','status':state,'http_status':latest.get('http_status'),'evidence_ids':latest.get('evidence_id',''),'evidence_path':latest.get('artifact_path',''),'utility':'INSUFFICIENT_EVIDENCE','notes':'HTTP availability does not establish Peru/operator coverage or incident utility.'})
 def csvout(name, data):
  fields=list(dict.fromkeys(k for x in data for k in x));
  with (REPORTS/name).open('w',newline='',encoding='utf-8-sig') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(data)
 csvout('source_matrix.csv',rows); csvout('source_access_matrix.csv',[{'source_id':x['source_id'],'official_auth_documentation_url':AUTH.get(x['source_id'],''),'account_required':x['source_id'] in AUTH,'auth_type':'free token/account' if x['source_id'] in AUTH else 'none identified for public endpoint','free_access_confirmed':'unknown pending official terms review','free_quota':'not verified','commercial_use_status':'UNKNOWN','tested_at':x.get('observed_at_utc',''),'http_status':x.get('http_status',''),'result':x['status'],'evidence_ids':x['evidence_ids'],'next_action':'review official access terms; credentials only after public stage'} for x in rows])
 csvout('temporal_validation.csv',[{'source_id':x['source_id'],'operator':x['operator'],'sample_count':0,'publication_lag':'UNKNOWN','collection_lag':'UNKNOWN','interval':'single bounded query','fields_unknown':'event start/publication timestamps'} for x in rows])
 for name in ['phase_b_peru_coverage.csv','probe_density_peru.csv','technology_coverage.csv','geo_validation.csv','evidence_independence.csv','source_dependency_matrix.csv','query_budget_by_source.csv','free_tier_simulation.csv','cost_scenarios.csv','source_pricing.csv','trigger_geography_feasibility.csv','peru_news_feeds.csv','peru_news_relevance.csv','x_official_accounts_inventory.csv','x_account_value_matrix.csv','x_final_account_decisions.csv','validation_decision_register.csv']:
  if not (REPORTS/name).exists(): csvout(name,[{'source_id':x['source_id'],'status':x['status'],'evidence_path':x['evidence_path'],'notes':'INSUFFICIENT_EVIDENCE; see validation_report.md'} for x in rows])
 for name,text in {
 'validation_report.md':'Validación en vivo ejecutada con endpoints oficiales/read-only. Consultar `source_matrix.csv`; fallos y respuestas crudas están indexados en `../evidencias/manifest.jsonl`. Un HTTP exitoso no acredita cobertura ni utilidad. La captura describe las respuestas observadas y no establece una tendencia.\n',
 'blockers.md':'Credenciales ausentes/no probadas: Cloudflare Radar, X/TwexAPI; quedan pendientes de autenticación y no se clasifican como sin cobertura. Consultar `pending_credentials.md`. Las cuotas técnicas se registran según evidencia; las licencias se revisan después y no bloquean la conclusión técnica.\n',
 'pending_credentials.md':'## Acceso condicionado pendiente\n\n- Cloudflare Radar — documentación https://developers.cloudflare.com/radar/ ; cuenta Cloudflare y token gratuito de solo lectura Radar. Revisar permiso exacto, cuotas y términos comerciales; no crear token ni incluirlo en logs. Pendiente de validación.\n- X oficial — documentación https://developer.x.com/en/docs ; token Bearer de API oficial, modalidad gratuita vigente no confirmada. Sin credenciales/prueba de acceso.\n- TwexAPI (intermediario X) — https://twexapi.io/get-started ; la arquitectura advierte posible scraping por el proveedor: bloqueado por política mientras no se autorice expresamente. Pendiente, no rechazada por cobertura.\n- Globalping cuenta opcional — https://globalping.io/docs/api.globalping.io ; probar primero anónimo; no solicitar mediciones que puedan consumir crédito.\n\nNo se solicitaron credenciales durante las pruebas públicas.\n',
 'free_access_and_licensing.md':'Las URLs y respuestas observadas están en el manifiesto. La revisión de licencias y condiciones comerciales se difiere a una etapa posterior; este informe separa acceso y cobertura técnica observados.\n',
 'economic_feasibility.md':'La ejecución local no utilizó pagos ni facturación. Precios y términos no verificados se conservan como UNKNOWN; no se han inventado cotizaciones.\n',
 'pricing_unknowns.md':'Planes, límites y costos comerciales requieren validación documental oficial por fuente. Ningún servicio pagado fue consultado.\n',
 'peru_institutional_sources.md':'OSIPTEL SISREP/medición e Indecopi requieren localizar canal de datos oficialmente automatizable. La página informativa no equivale a API. Pendiente de investigación documental oficial y permiso; no scraping.\n',
 'osiptel_sisrep_access.md':'Acceso automatizable y disponibilidad pública de SISREP: no confirmados en esta ejecución; no se intentó acceso restringido. Estado pendiente de investigación oficial.\n',
 'sonata_integration_questions.md':'Contrato Sonata/Win: PENDING. Confirmar interfaz, formato, seguridad, geografía, frecuencia, expiración y entorno de homologación con Win. No hay integración en esta PoC.\n',
 'output_contract_feasibility.md':'No hay fuentes aprobadas aún; campos de incidente/geografía/tecnología permanecen sin validar. Sin blueprint productivo ni feed.\n',
 'feed_format_decision.md':'Sin decisión de formato hasta confirmar contrato Sonata.\n',
 'cloudflare_radar_license_review.md':'Token ausente en etapa pública. Verificar condiciones Radar CC BY-NC y autorización expresa para indicadores usados en activación; no se contactó al proveedor.\n',
 'with_without_radar.md':'Sin datos Radar observados; impacto comparativo INSUFFICIENT_EVIDENCE. No asumir equivalencia de reemplazos.\n',
 'source_loss_analysis.md':'Análisis leave-one-source-out: INSUFFICIENT_EVIDENCE cuando no hay referencias independientes/eventos observados. No se inventan porcentajes.\n',
 'fallback_plans.md':'Alternativas deben validarse para Perú y por tecnología; BGP (IODA/RIS/RIPEstat routing) es dependencia común, mensajería no prueba internet y USGS es solo contexto.\n',
 'retry_policy_compliance.md':'Consultas acotadas, timeout 20s, sin reintento tras autenticación ni solicitudes de pago. Reintentar una ronda solo tras fallo transitorio documentado; no se aplicó reintento automático en ejecución inicial.\n',
 'low_density_analysis.md':'Las consultas disponibles son puntuales. Respuestas vacías y errores no significan falta de cobertura. Valorar cada fuente por la utilidad, atribución y frescura técnica que la evidencia obtenida permite demostrar.\n',
 'polling_vs_freshness.md':'Simulación hipotética: llamadas/mes por consulta y fuente = 43,200 (1m), 8,640 (5m), 2,880 (15m), 1,440 (30m); no aplica a streaming/feed y no se ejecutaron esos volúmenes. Frescura de publicación no determinada.\n',
 'source_loss_analysis.json':'{}\n','dependency_graph.json':'{}\n','revalidation_queue.json':'[]\n','approved_sources.json':'[]\n','blueprint_input.json':'{"status":"provisional","approved_sources":[],"sonata_contract":"PENDING"}\n',
 'rejected_sources.md':'Ninguna fuente autenticada se rechaza por falta de credenciales. Sin decisiones REJECTED definitivas en ausencia de evidencia suficiente.\n',
 'conditional_sources.md':'Fuentes pendientes por acceso técnico o cobertura; las licencias no forman parte de esta fase.\n',
 'insufficient_evidence.md':'La mayoría de fuentes carecen de evidencia observacional suficiente para utilidad por operador/zona, latencia e independencia.\n',
 'decision_sensitivity.md':'No hay suficientes eventos de referencia para estimar precisión/recall o sensibilidad cuantitativa. Reglas provisionales conservadoras: HTTP 200 no aprueba, sin evidencia no aprueba, autenticación pendiente => CONDITIONAL/INSUFFICIENT_EVIDENCE.\n',
 'retry_history.csv':'source_id,attempt,status,http_status,evidence_path\n',
 'source_loss_analysis.md':'INSUFFICIENT_EVIDENCE para pérdidas cuantitativas; evidencia y dependencias descritas en matrices.\n',
 'x_twexapi_access_pricing.md':'No consultado; mecanismo y trial deben verificarse oficialmente y TwexAPI podría usar scraping. Bloqueado por política pendiente, no pedir key.\n',
 'x_peru_signal_quality.md':'PENDING_AUTH / BLOCKED_POLICY: no se recuperaron conversaciones; no inferir ausencia de valor.\n',
 'x_account_exclusions.md':'Cuentas sin acceso de datos permanecen pendientes, no excluidas.\n',
 'x_source_resilience.md':'Sin acceso observacional de X; pérdida INSUFFICIENT_EVIDENCE.\n',
 'peru_news_top5.md':'No se clasifican noticias ni se extrae HTML. Los cinco feeds se validarán solo mediante RSS/Atom oficial documentado; pendiente de confirmar URLs y términos.\n',
 'peru_news_incremental_value.md':'INSUFFICIENT_EVIDENCE: no se confirmaron feeds oficiales autorizados en esta ronda.\n',
 'osiptel_quality_data.md':'Datos automatizables, granularidad y frescura no confirmados.\n',
 'source_access_matrix.csv':'',
 }.items():
  if name.endswith('.csv'): continue
  (REPORTS/name).write_text(text,encoding='utf-8')
 # final decisions deterministic and explicitly conservative
 decisions=[]
 for x in rows:
  final='CONDITIONAL' if x['source_id'] in ('cloudflare_radar','x_official','twexapi_x') else 'INSUFFICIENT_EVIDENCE'
  decisions.append({**x,'final_decision':final,'reason':'No automatic approval without verified Peru/operator utility, independent evidence, freshness and rights.'})
 (REPORTS/'validation_decision_register.csv').unlink(missing_ok=True); csvout('validation_decision_register.csv',decisions)
 md=['# Final decisions (provisional)','', 'Conservative deterministic evaluation; no source is approved from HTTP status alone. Auth-required services retain conditional/pending state. See source matrix, evidence manifest and pending credentials.','', '| Source | State | Evidence | Reason |','|---|---|---|---|']
 md += [f"| {x['source_id']} | {x['final_decision']} | {x['evidence_path'] or 'none'} | {x['reason']} |" for x in decisions]
 (REPORTS/'final_decisions.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 # Integrity audit
 errors=[]
 for x in records:
  p=ROOT/x['artifact_path']
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']: errors.append(x['evidence_id'])
 (REPORTS/'evidence_integrity.json').write_text(json.dumps({'manifest_records':len(records),'integrity_errors':errors},indent=2),encoding='utf-8')
def main():
 p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='cmd',required=True)
 sp.add_parser('doctor'); sp.add_parser('sources'); sp.add_parser('auth'); sp.add_parser('ris'); sp.add_parser('ioda'); sp.add_parser('globalping'); sp.add_parser('atlas-history'); sp.add_parser('radar-reference'); sp.add_parser('radar-netflows-replay'); sp.add_parser('audit')
 v=sp.add_parser('validate'); v.add_argument('--source'); v.add_argument('--all',action='store_true'); v.add_argument('--country',default='PE'); v.add_argument('--safe-free-only',action='store_true')
 h=sp.add_parser('historical'); h.add_argument('--days',type=int,default=30); h.add_argument('--country',default='PE'); h.add_argument('--safe-free-only',action='store_true')
 r=sp.add_parser('report'); r.add_argument('--format',default='all')
 a=p.parse_args()
 if a.cmd=='doctor': print(json.dumps({'python':sys.version,'root':str(ROOT),'env_file_present':(ROOT/'.env').exists(),'network':'not probed (doctor is non-invasive)'},indent=2))
 elif a.cmd=='sources':
  for n,(u,f,access) in SOURCES.items(): print(f'{n}\t{f}\t{access}\t{u}')
  for n,u in AUTH.items(): print(f'{n}\tAUTH_REQUIRED\t{u}')
 elif a.cmd in ('validate','historical'):
   if a.cmd=='historical': print('Historical endpoint capabilities vary; running the bounded public check (not asserting 30-day history).')
   if a.cmd=='validate' and a.source:
    if a.source not in SOURCES: print('Source is authenticated/conditional or unknown; no public request made.'); return
    mkdirs(); n=a.source; r,b=request(n,SOURCES[n][0],SOURCES[n][1]); write_reports(); print(json.dumps(r,indent=2))
   else: run_all()
 elif a.cmd=='auth': authenticated_stage()
 elif a.cmd=='ris': run_ris()
 elif a.cmd=='ioda':
  mkdirs(); run_ioda_stage(); write_reports()
 elif a.cmd=='globalping': run_globalping_stage()
 elif a.cmd=='atlas-history': run_atlas_history_stage()
 elif a.cmd=='radar-reference':
  mkdirs()
  from .closeout import run_cloudflare_reference_incidents
  print(json.dumps(run_cloudflare_reference_incidents(),ensure_ascii=False,indent=2))
 elif a.cmd=='radar-netflows-replay':
  mkdirs()
  from .closeout import run_cloudflare_netflows_incident_replay
  print(json.dumps(run_cloudflare_netflows_incident_replay(),ensure_ascii=False,indent=2))
 elif a.cmd=='audit':
  from .integrity import audit
  result=audit(ROOT)
  (REPORTS/'evidence_integrity.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
  print(json.dumps(result,indent=2))
  if result['integrity_errors']: raise SystemExit(1)
 elif a.cmd=='report':
  write_reports()
  from .finalize import write as finalize_reports
  finalize_reports()
  print(f'Reports written under {REPORTS}')
if __name__=='__main__': main()
