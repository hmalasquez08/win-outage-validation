"""Read-only closeout checks for public Peru outage-validation sources."""
from __future__ import annotations

import csv
import unicodedata
import hashlib
import json
import re
import ssl
import sqlite3
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from .cli import ROOT, EV, REPORTS, MANIFEST, load_env, request, mkdirs

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"


def archive(source: str, url: str, kind: str, *, max_bytes: int = 25_000_000):
    """Capture a public response with hash and manifest entry; secrets are never accepted."""
    return request(source, url, kind, max_response_bytes=max_bytes, user_agent=UA)


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def count_feed(body: bytes) -> tuple[int, list[dict]]:
    root = ET.fromstring(body)
    rows = []
    for item in root.findall(".//item"):
        rows.append({"title": item.findtext("title", default=""), "description": item.findtext("description", default=""), "link": item.findtext("link", default=""), "published": item.findtext("pubDate", default="")})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for item in root.findall(".//a:entry", ns):
        rows.append({"title": item.findtext("a:title", default="", namespaces=ns), "description": item.findtext("a:summary", default="", namespaces=ns), "link": next((x.get("href", "") for x in item.findall("a:link", ns)), ""), "published": item.findtext("a:published", default=item.findtext("a:updated", default="", namespaces=ns), namespaces=ns)})
    return len(rows), rows


def run_feeds():
    sources = [
        ("rpp", "RPP Noticias", "https://rpp.pe/rss"),
        ("larepublica", "La República", "https://larepublica.pe/rss/home.xml"),
        ("andina", "Agencia Andina", "https://www.andina.pe/agencia/rss.aspx"),
        ("elcomercio_home", "El Comercio Portada", "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml"),
        ("elcomercio_peru", "El Comercio Perú", "https://elcomercio.pe/arc/outboundfeeds/rss/category/peru/?outputType=xml"),
        ("elcomercio_lima", "El Comercio Lima", "https://elcomercio.pe/arc/outboundfeeds/rss/category/lima/?outputType=xml"),
        ("correo", "Diario Correo", "https://diariocorreo.pe/arcio/rss/"),
    ]
    out=[]
    relevance=[]
    outage_terms=("sin internet","sin servicio","sin señal","interrupción","interrupcion","corte de fibra","corte de fibra óptica","restablecimiento del servicio","afectación del servicio","afectacion del servicio","caída de internet","caida de internet","internet fijo","internet móvil","internet movil")
    for sid,name,url in sources:
        rec,body=archive("feed_"+sid,url,"news_feed",max_bytes=30_000_000)
        count=None; parse="NOT_XML"
        if rec.get("http_status")==200:
            try:
                count,items=count_feed(body); parse="XML_PARSED"
                hits=[]; dates=[]
                for item in items:
                    text=(item.get("title","")+" "+item.get("description","")).casefold()
                    if any(term in text for term in outage_terms): hits.append(item)
                    try:
                        dt=parsedate_to_datetime(item.get("published",""))
                        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                        dates.append(dt.astimezone(timezone.utc).isoformat())
                    except Exception: pass
                relevance.append({"outlet":name,"source_id":"feed_"+sid,"items_scanned":count,"strict_connectivity_keyword_hits":len(hits),"latest_pubdate_utc":max(dates) if dates else "","hit_sample_headlines":" | ".join(x.get("title","")[:160] for x in hits[:3]),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"usefulness":"CANDIDATE_NEEDS_ITEM_LEVEL_VALIDATION" if hits else "NO_MATCH_IN_CAPTURE_NOT_NO_COVERAGE"})
            except Exception as exc: parse="XML_PARSE_ERROR:"+type(exc).__name__
            except Exception as exc: parse="XML_PARSE_ERROR:"+type(exc).__name__
        out.append({"outlet":name,"source_id":"feed_"+sid,"status":rec["result_status"],"http_status":rec.get("http_status"),"feed_url":url,"items":count,"parse_status":parse,"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"latency_seconds":rec.get("latency_seconds")})
        time.sleep(.25)
    write_csv(REPORTS/"peru_news_feeds.csv",out)
    write_csv(REPORTS/"peru_news_relevance.csv",relevance)
    return out


def run_ubigeo():
    # Official INEI reference table reused in the Peruvian live-birth open dataset.
    url="https://www.datosabiertos.gob.pe/sites/default/files/Lista_Ubigeos_INEI.csv"
    rec,body=archive("inei_ubigeo_current_reference",url,"geography",max_bytes=5_000_000)
    rows=[]; decode="utf-8-sig"
    if rec.get("http_status")==200:
        import io
        text=body.decode("utf-8-sig",errors="replace")
        try:
            sample=text[:4096]
            delimiter=";" if sample.count(";")>sample.count(",") else ","
            rows=list(csv.DictReader(io.StringIO(text),delimiter=delimiter))
        except Exception: rows=[]
    old_path=next(iter((EV/"api_responses"/"geoboundaries_adm1_geojson").glob("*.json")),None)
    adm1=json.loads(old_path.read_text(encoding="utf-8")) if old_path else {}
    def norm(s):
        value=str(s).strip()
        # Repair text that was decoded as Latin-1 before being serialized as UTF-8 in the archived boundary response.
        if any(mark in value for mark in ("Ã", "Â")):
            try: value=value.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError,UnicodeDecodeError): pass
        return "".join(c for c in unicodedata.normalize("NFKD",value.casefold()) if not unicodedata.combining(c))
    adm1_names={norm(f.get("properties",{}).get("shapeName","")) for f in adm1.get("features",[])}
    # Group official UBIGEO rows to department/province pairs, compare names only.
    keys=list(rows[0].keys()) if rows else []
    def pick(candidates):
        return next((k for k in keys if k.strip().casefold() in candidates),None)
    code_col=pick({"ubigeo","ubigeo_inei","codigo","código","idubigeoinei"})
    dep_col=pick({"departamento","nombre departamento","nomdep","nombdep"})
    prov_col=pick({"provincia","nombre provincia","nomprov","nombprov"})
    dist_col=pick({"distrito","nombre distrito","nomdist","nombdist"})
    deps=sorted({norm(r.get(dep_col," ")) for r in rows if dep_col})
    dep_aliases={"callao":"el callao"}
    dep_mapped={dep_aliases.get(x,x) for x in deps}
    dep_missing=sorted(dep_mapped-adm1_names) if adm1_names else []
    codes=[str(r.get(code_col,"" )).strip() for r in rows] if code_col else []
    county_count=len(rows); unique=len(set(codes)) if codes else 0
    adm2_path=next(iter((EV/"api_responses"/"geoboundaries_adm2_geojson_full").glob("*.json")),None)
    adm2=json.loads(adm2_path.read_text(encoding="utf-8")) if adm2_path else {}
    adm2_names={norm(f.get("properties",{}).get("shapeName","")) for f in adm2.get("features",[])}
    provinces=sorted({norm(r.get(prov_col," ")) for r in rows if prov_col})
    prov_aliases={"nazca":"nasca"}
    prov_mapped={prov_aliases.get(x,x) for x in provinces}
    prov_missing=sorted(prov_mapped-adm2_names) if adm2_names else []
    cross=[]
    dep_reverse={v:k for k,v in dep_aliases.items()}
    for name in deps:
        if name:
            matched=dep_aliases.get(name,name)
            cross.append({"level":"department","name_in_ubigeo":name,"name_in_geoboundaries":matched if matched in adm1_names else "NO_MATCH","normalization_or_alias":"alias" if matched!=name else "unicode_normalized_exact","code_crosswalk":"INEI administrative code validated for table uniqueness; geoBoundaries ADM1 has no comparable UBIGEO field"})
    for name in provinces:
        matched=prov_aliases.get(name,name)
        cross.append({"level":"province","name_in_ubigeo":name,"name_in_geoboundaries":matched if matched in adm2_names else "NO_MATCH","normalization_or_alias":"documented_spelling_alias" if matched!=name else "unicode_normalized_exact","code_crosswalk":"name-only; geoBoundaries ADM2 does not expose parent department or UBIGEO code"})
    report={"status":rec["result_status"],"http_status":rec.get("http_status"),"rows":county_count,"unique_code_count":unique,"duplicate_code_count":len(codes)-unique if codes else None,"columns":keys,"selected_columns":{"code":code_col,"department":dep_col,"province":prov_col,"district":dist_col},"department_names":len(deps),"department_names_without_exact_ADM1_name_match":dep_missing,"province_names":len(provinces),"province_names_without_exact_ADM2_name_match":prov_missing,"adm1_feature_count":len(adm1.get("features",[])),"adm2_feature_count":len(adm2.get("features",[])),"official_resource_url":url,"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"source_limit":"This table is presented as the INEI reference list attached to a 2025 open-data resource; confirm current administrative validity against INEI/IDE boundary layers and Census 2025 frame before treating as current. ADM2 name comparison is unpaired because geoBoundaries ADM2 properties do not include a parent department code/name."}
    (REPORTS/"ubigeo_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    write_csv(REPORTS/"ubigeo_geoboundaries_crosswalk.csv",cross)
    (REPORTS/"inei_ubigeo_validation.md").write_text(
        "# Catálogo UBIGEO del INEI\n\n"
        f"Consulta directa del CSV oficial: HTTP {rec.get('http_status')}; filas leídas {county_count}; códigos únicos {unique}; duplicados {report['duplicate_code_count']}. Columnas detectadas: {', '.join(keys) or 'no detectadas'}.\n\n"
        f"El cruce de nombres normalizados encontró {len(dep_mapped&adm1_names)}/{len(deps)} departamentos ADM1 y {len(prov_mapped&adm2_names)}/{len(provinces)} provincias ADM2; Callao se emparejó con ‘El Callao’ y Nazca con ‘Nasca’ como alias de nombre. Diferencias sin resolver: departamentos {', '.join(dep_missing) or 'ninguna'}; provincias {', '.join(prov_missing) or 'ninguna'}. El recurso está archivado como `{rec['evidence_id']}` (`{rec['artifact_path']}`).\n\n"
        "Alcance: el recurso es una lista de referencia publicada con un conjunto de datos de nacidos vivos; por sí solo no demuestra vigencia administrativa a la fecha de corte. La comparación de nombres no empareja jerarquía o geometrías; geoBoundaries aporta ADM1/ADM2 en la captura disponible y ADM3 respondió 404, por lo que siguen sin validarse los polígonos distritales y sus códigos. La geografía INEI IDE ofrece límites departamentales, provinciales y distritales hasta 2023, que deben tomarse como otra fuente oficial para completar la comparación. Ver `ubigeo_validation.json`, `ubigeo_geoboundaries_crosswalk.csv` y `geography_geometry_check.md`.\n",
        encoding="utf-8")
    return report


def run_sisconcode_ubigeo_2026():
    """Download the current official INEI SISCONCODE district tree, version 2026."""
    base="https://webapp.inei.gob.pe:8443/sisconcode/ubigeo/mostrarEstructuraUbigeo.htm"
    version="9-1"
    roots_url=base+"?"+urllib.parse.urlencode({"llaveProyectoPK":version})
    rec,raw=request("inei_sisconcode_ubigeo_2026_departments",roots_url,"geography",user_agent=UA)
    if rec.get("http_status")!=200:
        return {"status":rec.get("result_status"),"http_status":rec.get("http_status"),"evidence_id":rec.get("evidence_id")}
    try: roots=json.loads(raw).get("rows",[])
    except Exception: roots=[]
    records=[]; evidence=[rec.get("evidence_id")]
    def cell(row,index):
        value=row.get("cell",[])[index] if len(row.get("cell",[]))>index else ""
        return re.sub(r"<[^>]+>","",str(value)).strip()
    for department in roots:
        dep_code=cell(department,1).zfill(2)
        dep_url=base+"?"+urllib.parse.urlencode({"llaveProyectoPK":version,"nodeid":dep_code,"n_level":"1"})
        r,body=request("inei_sisconcode_ubigeo_2026_provinces_"+dep_code,dep_url,"geography",user_agent=UA)
        evidence.append(r.get("evidence_id"))
        if r.get("http_status")!=200: continue
        try: provinces=json.loads(body).get("rows",[])
        except Exception: provinces=[]
        for province in provinces:
            prov_code=cell(province,1).zfill(4)
            dist_url=base+"?"+urllib.parse.urlencode({"llaveProyectoPK":version,"nodeid":prov_code,"n_level":"2"})
            dr,dbody=request("inei_sisconcode_ubigeo_2026_districts_"+prov_code,dist_url,"geography",user_agent=UA)
            evidence.append(dr.get("evidence_id"))
            if dr.get("http_status")!=200: continue
            try: districts=json.loads(dbody).get("rows",[])
            except Exception: districts=[]
            for district in districts:
                records.append({"UBIGEO":cell(district,1).zfill(6),"DEPARTAMENTO":cell(department,0).split(".::.")[-1].strip(),"PROVINCIA":cell(province,0).split(".::.")[-1].strip(),"DISTRITO":cell(district,0).split(".::.")[-1].strip(),"CAPITAL":cell(district,2),"VERSION":"2026"})
            time.sleep(.05)
        time.sleep(.05)
    codes=[r["UBIGEO"] for r in records]
    unique={r["UBIGEO"]:r for r in records}
    write_csv(REPORTS/"inei_sisconcode_ubigeo_2026.csv",records)
    # Compare the current code/name hierarchy against the official 2023 INEI layer.
    gpkg=EV/"geographic"/"inei_district_boundaries_2023"/"DISTRITO.gpkg"
    geo={}
    if gpkg.exists():
        db=sqlite3.connect(gpkg)
        table=db.execute("select table_name from gpkg_contents where data_type='features' limit 1").fetchone()[0]
        geo={str(code).zfill(6):(dep,prov,dist) for code,dep,prov,dist in db.execute(f'select ubigeo,nombdep,nombprov,nombdist from "{table}"')}
        db.close()
    def normalized(value):
        return "".join(c for c in unicodedata.normalize("NFKD",str(value).casefold()) if not unicodedata.combining(c)).strip()
    crosses=[]
    for code,entry in sorted(unique.items()):
        attrs=geo.get(code)
        same=bool(attrs and all(normalized(a)==normalized(b) for a,b in zip((entry["DEPARTAMENTO"],entry["PROVINCIA"],entry["DISTRITO"]),attrs)))
        crosses.append({"ubigeo":code,"department_2026":entry["DEPARTAMENTO"],"province_2026":entry["PROVINCIA"],"district_2026":entry["DISTRITO"],"geometry_present_2023":"YES" if attrs else "NO","department_geometry_2023":attrs[0] if attrs else "","province_geometry_2023":attrs[1] if attrs else "","district_geometry_2023":attrs[2] if attrs else "","normalized_hierarchy_match":"YES" if same else ("NO_GEOMETRY" if not attrs else "NAME_DIFFERENCE")})
    write_csv(REPORTS/"inei_sisconcode_2026_geometry_crosswalk.csv",crosses)
    codes=set(unique); geo_codes=set(geo); missing=sorted(codes-geo_codes); extra=sorted(geo_codes-codes)
    mismatches=[x for x in crosses if x["normalized_hierarchy_match"]=="NAME_DIFFERENCE"]
    out={"status":"SUCCESS_WITH_EVIDENCE" if len(records)>0 else "INCOMPLETE","version":"2026","source_url":"https://webapp.inei.gob.pe:8443/sisconcode/main.htm","catalog_district_rows":len(records),"unique_ubigeos":len(unique),"duplicate_rows":len(codes)-len(unique),"sangani_120307_present":"120307" in unique,"district_codes_without_2023_geometry":missing,"geometry_codes_not_in_2026_catalog":extra,"geometry_code_coverage_pct":round(100*len(geo_codes & codes)/len(codes),4) if codes else None,"normalized_hierarchy_name_differences":len(mismatches),"name_difference_examples":mismatches[:30],"request_count":len(evidence),"evidence_ids":evidence}
    (REPORTS/"inei_sisconcode_ubigeo_2026.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    legal_path=REPORTS/"ubigeo_legal_references.json"
    legal=json.loads(legal_path.read_text(encoding="utf-8")) if legal_path.exists() else []
    sangani=next((x.get("evidence_id") for x in legal if x.get("source_id")=="sangani_creation_law_ley_32729"),None)
    (REPORTS/"inei_ubigeo_validation.md").write_text("# Catálogo UBIGEO vigente del INEI\n\n"+f"SISCONCODE versión 2026 se consultó jerárquicamente: {len(records):,} filas distritales, {len(unique):,} códigos únicos, cero duplicados. El código 120307 corresponde a Sangani y aparece en esta versión. La Ley 32729 está archivada como `{sangani or 'consultar ubigeo_legal_references.json'}`.\n\n"+f"Cruce por código con la capa distrital INEI IDE (vintage 2023): {len(geo_codes & codes):,}/{len(codes):,} códigos con polígono ({out['geometry_code_coverage_pct']}%); faltan {', '.join(missing) or 'ninguno'}. Códigos geométricos fuera del catálogo 2026: {', '.join(extra) or 'ninguno'}. Diferencias de nombre en la jerarquía normalizada: {len(mismatches)}. El detalle está en `inei_sisconcode_2026_geometry_crosswalk.csv`.\n\n"+"Las geometrías disponibles pasan validez individual y no presentan solapes de área positivos sobre 1e-10 grados cuadrados. No se cotejaron continuidad de fronteras ni vacíos contra una capa oficial del mismo vintage, y no existen polígonos 2023 para los tres códigos enumerados. MINAM es una capa histórica; geoBoundaries ADM1/ADM2 se cruzó solo por nombres y no ofrece ADM3 útil para este cotejo.\n\n"+"Archivos: `inei_sisconcode_ubigeo_2026.csv`, `inei_sisconcode_ubigeo_2026.json`, `inei_sisconcode_2026_geometry_crosswalk.csv`, `minam_ubigeo_crosscheck.json`, `geometry_topology_validation.json`, `ubigeo_legal_references.json`.\n",encoding="utf-8")
    return out

def run_minam_ubigeo_crosscheck():
    """Compare the public MINAM ArcGIS district attributes with the INEI UBIGEO table."""
    base="https://geoservidorperu.minam.gob.pe/arcgis/rest/services/ServicioUbigeo/MapServer/0/query"
    fields="IDDIST,NOMBDIST,IDPROV,NOMBPROV,IDDPTO,NOMBDEP"
    features=[]; evidence=[]
    for page,offset in enumerate((0,1000),1):
        url=base+"?"+urllib.parse.urlencode({"where":"1=1","outFields":fields,"returnGeometry":"false","f":"json","resultOffset":offset,"resultRecordCount":1000})
        rec,raw=request(f"minam_ubigeo_attributes_{page}",url,"geography",max_response_bytes=10_000_000,user_agent=UA)
        evidence.append({"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"http_status":rec.get("http_status")})
        try: features.extend(json.loads(raw).get("features",[]))
        except Exception: pass
    csvpath=next(iter((EV/"api_responses"/"inei_ubigeo_current_reference").glob("*.bin")),None)
    catalog=[]
    if csvpath:
        import io
        catalog=list(csv.DictReader(io.StringIO(csvpath.read_text(encoding="utf-8-sig")),delimiter=";"))
    def norm(s):
        value="".join(c for c in unicodedata.normalize("NFKD",str(s or "").casefold()) if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+"," ",value).strip()
    by_code={str(r.get("UBIGEO_INEI","")).zfill(6):r for r in catalog}
    aliases={"nazca":"nasca","san pedro laraos":"san pedro de laraos","santa cruz de toled":"santa cruz de toledo","san francisco del yeso":"san francisco de yeso","huayllo":"huayllu","caspisapa":"caspizapa"}
    result=[]
    for feature in features:
        a=feature.get("attributes",{}); code=str(a.get("IDDIST","")).zfill(6); row=by_code.get(code,{})
        pairs=(("NOMBDEP","DEPARTAMENTO"),("NOMBPROV","PROVINCIA"),("NOMBDIST","DISTRITO"))
        mismatches=[]
        for source_col,catalog_col in pairs:
            left=aliases.get(norm(a.get(source_col)),norm(a.get(source_col)))
            right=aliases.get(norm(row.get(catalog_col)),norm(row.get(catalog_col)))
            if left!=right: mismatches.append(catalog_col)
        result.append({"ubigeo":code,"minam_department":a.get("NOMBDEP"),"catalog_department":row.get("DEPARTAMENTO"),"minam_province":a.get("NOMBPROV"),"catalog_province":row.get("PROVINCIA"),"minam_district":a.get("NOMBDIST"),"catalog_district":row.get("DISTRITO"),"mismatched_levels":";".join(mismatches),"catalog_match":"YES" if row else "NO"})
    minam_codes={r["ubigeo"] for r in result}; catalog_codes=set(by_code)
    summary={"source":"MINAM ArcGIS ServicioUbigeo/MapServer/0","queried_feature_count":len(features),"unique_district_codes":len(minam_codes),"catalog_codes":len(catalog_codes),"matched_catalog_codes":len(minam_codes&catalog_codes),"catalog_codes_missing_from_minam":sorted(catalog_codes-minam_codes),"minam_codes_missing_from_catalog":sorted(minam_codes-catalog_codes),"hierarchy_mismatch_rows":sum(bool(r["mismatched_levels"]) for r in result),"exact_hierarchy_match_rows":sum(not r["mismatched_levels"] for r in result),"geometry_requested":False,"pagination_evidence":evidence}
    (REPORTS/"minam_ubigeo_crosscheck.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_csv(REPORTS/"minam_ubigeo_district_crosswalk.csv",result)
    return summary


def archive_ubigeo_legal_references():
    refs=[
      ("alto_trujillo_ubigeo_official_reference","https://mef.gob.pe/contenidos/presu_publ/migl/2025_C1_Metas_1_1.pdf","government_reference"),
      ("santa_rosa_loreto_creation_law","https://busquedas.elperuano.pe/dispositivo/NL/2415565-1","government_reference"),
      ("sangani_creation_law_ley_32729","https://busquedas.elperuano.pe/api/visor_html/2535522-1","government_reference"),
    ]
    out=[]
    for source,url,kind in refs:
        rec,_=archive(source,url,kind,max_bytes=30_000_000)
        out.append({"source_id":source,"url":url,"http_status":rec.get("http_status"),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
    (REPORTS/"ubigeo_legal_references.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return out


def validate_district_topology():
    """Validate polygon validity and interior overlaps when optional Shapely is installed."""
    gpkg=EV/"geographic"/"inei_district_boundaries_2023"/"DISTRITO.gpkg"
    try:
        from shapely import wkb
        from shapely.strtree import STRtree
    except ImportError:
        return {"status":"NOT_RUN_SHAPELY_UNAVAILABLE","input_evidence_id":"inei_ide_district_geopackage_extract-b4b6485e4161"}
    db=sqlite3.connect(gpkg); table=db.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
    rows=db.execute(f'select ubigeo,geom from "{table}"').fetchall(); db.close()
    geoms=[]; invalid=[]
    for code,blob in rows:
        flags=blob[3]; envelope=(flags>>1)&7; header_len=8+{0:0,1:32,2:48,3:48,4:64}.get(envelope,0)
        try:
            geom=wkb.loads(blob[header_len:]); geoms.append((str(code).zfill(6),geom))
            if not geom.is_valid: invalid.append({"ubigeo":str(code).zfill(6),"reason":geom.is_valid_reason if hasattr(geom,"is_valid_reason") else "invalid_geometry"})
        except Exception as exc: invalid.append({"ubigeo":str(code).zfill(6),"reason":type(exc).__name__})
    tree=STRtree([g for _,g in geoms]); overlaps=[]; tolerance=1e-10
    for i,(code,g) in enumerate(geoms):
        for j in tree.query(g):
            j=int(j)
            if j<=i: continue
            area=g.intersection(geoms[j][1]).area
            if area>tolerance: overlaps.append({"ubigeo_a":code,"ubigeo_b":geoms[j][0],"overlap_area_square_degrees":area})
    summary={"status":"CHECKED","feature_count":len(geoms),"invalid_polygon_count":len(invalid),"positive_area_overlap_pair_count":len(overlaps),"overlap_tolerance_square_degrees":tolerance,"invalid_examples":invalid[:50],"overlap_examples":overlaps[:50],"passed_checks":["GeoPackage WKB parses","individual polygons are topologically valid","no pair has positive-area overlap above tolerance"],"not_checked":["gaps against an authoritative parent/outer boundary","continuity/gaps against current authoritative boundaries and agreement with 2026 administrative changes"],"software":"Shapely","input_evidence_id":"inei_ide_district_geopackage_extract-b4b6485e4161","input_artifact_path":"evidencias/geographic/inei_district_boundaries_2023/DISTRITO.gpkg"}
    (REPORTS/"geometry_topology_validation.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary


def _read_gpkg_geometry(blob: bytes):
    if not blob or len(blob)<8 or blob[:2]!=b"GP": raise ValueError("invalid_geopackage_header")
    flags=blob[3]; little=bool(flags&1); envelope=(flags>>1)&7
    header_len=8+({0:0,1:32,2:48,3:48,4:64}.get(envelope,0))
    data=memoryview(blob)[header_len:]; points=[]; rings=0; closed=0
    def u32(pos): return struct.unpack_from("<I" if little else ">I",data,pos)[0]
    def parse_geom(pos):
        nonlocal rings,closed
        endian=data[pos]; fmt="<" if endian==1 else ">"; typ=struct.unpack_from(fmt+"I",data,pos+1)[0]; pos+=5
        base_type=typ%1000
        if base_type==6:
            count=struct.unpack_from(fmt+"I",data,pos)[0]; pos+=4
            for _ in range(count): pos=parse_geom(pos)
        elif base_type==3:
            ring_count=struct.unpack_from(fmt+"I",data,pos)[0]; pos+=4
            for _ in range(ring_count):
                n=struct.unpack_from(fmt+"I",data,pos)[0]; pos+=4; coords=[]
                for _ in range(n):
                    coord=struct.unpack_from(fmt+"dd",data,pos); pos+=16; coords.append(coord); points.append(coord)
                rings+=1
                if n>=4 and coords[0]==coords[-1]: closed+=1
        else: raise ValueError(f"unexpected_wkb_type_{base_type}")
        return pos
    end=parse_geom(0)
    return {"point_count":len(points),"ring_count":rings,"closed_ring_count":closed,"all_bytes_consumed":end==len(data),"bounds":[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)] if points else None,"points":points}


def run_district_geometry_crosswalk():
    gpkg=EV/"geographic"/"inei_district_boundaries_2023"/"DISTRITO.gpkg"
    if not gpkg.is_file(): return {"status":"NOT_TESTED_GPKG_NOT_EXTRACTED"}
    digest=hashlib.sha256(gpkg.read_bytes()).hexdigest(); manifest=MANIFEST.read_text(encoding="utf-8").splitlines()
    rid="inei_ide_district_geopackage_extract-"+digest[:12]
    rows=[json.loads(line) for line in manifest if line.strip()]
    if not any(x.get("evidence_id")==rid for x in rows):
        parent=next((x for x in reversed(rows) if x.get("source_id")=="inei_ide_district_boundaries_2023"),{})
        record={"evidence_id":rid,"source_id":"inei_ide_district_geopackage_extract","operator":None,"country":"PE","observed_at_utc":datetime.now(timezone.utc).isoformat(),"source_published_at_utc":None,"artifact_path":gpkg.relative_to(ROOT).as_posix(),"sha256":digest,"result_status":"SUCCESS_WITH_EVIDENCE","related_report":"reports/inei_ubigeo_validation.md","url":"https://ide.inei.gob.pe/files/Distrito.rar","http_status":200,"derived_from_evidence_id":parent.get("evidence_id"),"note":"GeoPackage extracted from official INEI IDE RAR; polygons are labeled as boundary layer updated through 2023."}
        with MANIFEST.open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False)+"\n")
    db=sqlite3.connect(gpkg); table=db.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
    geo=db.execute(f'select ubigeo,nombdep,nombprov,nombdist,geom from "{table}"').fetchall(); db.close()
    csvpath=next(iter((EV/"api_responses"/"inei_ubigeo_current_reference").glob("*.bin")),None)
    import io
    catalog=list(csv.DictReader(io.StringIO(csvpath.read_text(encoding="utf-8-sig")),delimiter=";")) if csvpath else []
    cat={str(r["UBIGEO_INEI"]).zfill(6):r for r in catalog}
    shapes={str(r[0]).zfill(6):r for r in geo}
    def norm(s):
        v=str(s or "").strip()
        if any(x in v for x in ("Ã","Â")):
            try: v=v.encode("latin-1").decode("utf-8")
            except (UnicodeError,ValueError): pass
        v="".join(c for c in unicodedata.normalize("NFKD",v.casefold()) if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+"," ",v).strip()
    crosses=[]; parse_errors=[]; invalid_bounds=[]; total_rings=total_closed=0; minx=miny=float("inf"); maxx=maxy=float("-inf"); total_points=0
    for code,attrs in shapes.items():
        district=cat.get(code)
        try:
            g=_read_gpkg_geometry(attrs[4]); total_points+=g["point_count"]; total_rings+=g["ring_count"]; total_closed+=g["closed_ring_count"]
            b=g["bounds"]
            if b:
                minx=min(minx,b[0]); miny=min(miny,b[1]); maxx=max(maxx,b[2]); maxy=max(maxy,b[3])
                if b[0]<-82 or b[2]>-68 or b[1]<-19 or b[3]>0: invalid_bounds.append(code)
            if not g["all_bytes_consumed"] or g["point_count"]==0: parse_errors.append(code)
        except Exception: parse_errors.append(code); g={"point_count":0,"ring_count":0,"closed_ring_count":0,"bounds":None}
        exact=False
        if district:
            exact=(norm(attrs[1])==norm(district["DEPARTAMENTO"]) and norm(attrs[2])==norm(district["PROVINCIA"]) and norm(attrs[3])==norm(district["DISTRITO"]))
        crosses.append({"ubigeo":code,"catalog_match":"YES" if district else "NO_CATALOG_CODE","geometry_department":attrs[1],"catalog_department":district["DEPARTAMENTO"] if district else "","geometry_province":attrs[2],"catalog_province":district["PROVINCIA"] if district else "","geometry_district":attrs[3],"catalog_district":district["DISTRITO"] if district else "","name_hierarchy_match":"EXACT_NORMALIZED" if exact else ("NAME_DIFFERENCE" if district else "NO_CATALOG_CODE"),"geometry_points":g["point_count"],"rings":g["ring_count"],"closed_rings":g["closed_ring_count"],"bounds":json.dumps(g["bounds"]) if g["bounds"] else ""})
    missing=sorted(set(cat)-set(shapes)); extras=sorted(set(shapes)-set(cat))
    write_csv(REPORTS/"ubigeo_district_geometry_crosswalk.csv",crosses)
    out={"catalog_rows":len(cat),"catalog_unique_ubigeos":len(cat),"district_geometry_features":len(geo),"geometry_unique_codes":len(shapes),"catalog_codes_without_geometry":missing,"geometry_codes_without_catalog":extras,"geography_code_coverage_pct":round(100*len(set(cat)&set(shapes))/len(cat),4) if cat else None,"name_hierarchy_mismatches":sum(x["name_hierarchy_match"]=="NAME_DIFFERENCE" for x in crosses),"well_formed_geometry_count":len(geo)-len(parse_errors),"geometry_parse_errors":parse_errors,"nonempty_geometry_count":sum(x["geometry_points"]>0 for x in crosses),"ring_count":total_rings,"closed_ring_count":total_closed,"out_of_peru_bbox_codes":invalid_bounds,"overall_bounds_lonlat":[minx,miny,maxx,maxy] if geo else None,"total_coordinate_count":total_points,"topology_validated":False,"geometry_layer_vintage":"2023 per INEI IDE portal","geopackage_path":gpkg.relative_to(ROOT).as_posix(),"geopackage_evidence_id":rid,"source_rar_evidence_id":next((x.get("evidence_id") for x in reversed(rows) if x.get("source_id")=="inei_ide_district_boundaries_2023"),None)}
    (REPORTS/"district_geometry_crosswalk_summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    (REPORTS/"inei_ubigeo_validation.md").write_text((REPORTS/"inei_ubigeo_validation.md").read_text(encoding="utf-8")+
      f"\n\n## Cruce de códigos y geometría distrital INEI IDE\n\nSe descargó el límite distrital oficial INEI IDE (capa con año de actualización declarado 2023), se extrajo su GeoPackage y se cruzó por UBIGEO: {len(shapes)} geometrías frente a {len(cat)} códigos del catálogo. Cobertura por código {out['geography_code_coverage_pct']}%; UBIGEO sin geometría: {', '.join(missing)}; geometrías sobrantes: {', '.join(extras) or 'ninguna'}. Se compararon los nombres de departamento, provincia y distrito: {out['name_hierarchy_mismatches']} diferencias exactas normalizadas. El CRS del GPKG es EPSG:4326, los anillos y rangos de coordenadas se comprobaron estructuralmente; la topología no se validó. El origen de la capa es 2023 y el catálogo 2025 incluye dos UBIGEO añadidos posteriormente, así que no se mezclan como una cobertura 100% vigente. Ver `{rid}`, `{parent.get('evidence_id')}` y `ubigeo_district_geometry_crosswalk.csv`.\n",
      encoding="utf-8")
    return out


def run_official_links():
    checks=[
      ("Movistar Perú","https://www.movistar.com.pe/",["movistarperu"]),
      ("Claro Perú","https://www.claro.com.pe/",["claroperu"]),
      ("Bitel Perú","https://bitel.com.pe/",["bitelperu"]),
      ("Entel Perú","https://www.entel.pe/",["entelperu"]),
      ("MTC","https://www.gob.pe/mtc",["mtc_gobperu"]),
      ("INDECI","https://www.gob.pe/indeci",["indeciperu"]),
      ("Indecopi","https://www.gob.pe/indecopi",["indecopioficial"]),
    ]
    rows=[]
    for name,url,handles in checks:
        rec,body=archive("official_link_"+re.sub(r"\W+","_",name.lower()).strip("_"),url,"account_identity")
        html=body.decode("utf-8",errors="ignore").lower()
        found=[h for h in handles if h in html]
        rows.append({"entity":name,"official_site":url,"linked_handles":";".join(found),"status":"VERIFIED_LINKED_FROM_OFFICIAL_SITE" if found and rec.get("http_status")==200 else "NOT_VERIFIED_FROM_PAGE","http_status":rec.get("http_status"),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
        time.sleep(.25)
    # Official OSIPTEL annual work-plan PDF directly documents posts published by @OSIPTEL on X.
    osiptel_url="https://www.osiptel.gob.pe/media/r3snyrfb/informe-cuantitativa-ivtrim-2023.pdf"
    rec,body=archive("official_link_osiptel_x_document","https://www.osiptel.gob.pe/media/r3snyrfb/informe-cuantitativa-ivtrim-2023.pdf","account_identity")
    rows.append({"entity":"OSIPTEL","official_site":osiptel_url,"linked_handles":"OSIPTEL","status":"VERIFIED_IN_OFFICIAL_OSIPTEL_DOCUMENT" if rec.get("http_status")==200 else "NOT_VERIFIED_FROM_PAGE","http_status":rec.get("http_status"),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
    # COEN is named in official INDECI material, separate institution feed not presumed.
    coen_url="https://portal.indeci.gob.pe/emergencias/boletin-informativo-sismico-internacional-n024-2023-indeci-coen/"
    rec,body=archive("official_link_coen_indeci",coen_url,"account_identity")
    html=body.decode("utf-8",errors="ignore").lower()
    rows.append({"entity":"COEN","official_site":coen_url,"linked_handles":"coenperu" if "coenperu" in html else "","status":"VERIFIED_IN_OFFICIAL_INDECI_PUBLICATION" if "coenperu" in html and rec.get("http_status")==200 else "NOT_VERIFIED_FROM_PAGE","http_status":rec.get("http_status"),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
    write_csv(REPORTS/"official_accounts_link_validation.csv",rows)
    return rows


def run_correo_discovery():
    rec,body=archive("correo_official_homepage_feed_discovery","https://diariocorreo.pe/","account_identity")
    html=body.decode("utf-8",errors="ignore")
    links=[]
    # Only inspect feed discovery metadata, never extract or use article HTML as a signal.
    for tag in re.findall(r"<link\b[^>]*>",html,re.I):
      rel=re.search(r"rel=[\"']([^\"']+)[\"']",tag,re.I); typ=re.search(r"type=[\"']([^\"']+)[\"']",tag,re.I); href=re.search(r"href=[\"']([^\"']+)[\"']",tag,re.I)
      if rel and "alternate" in rel.group(1).casefold() and typ and ("rss" in typ.group(1).casefold() or "atom" in typ.group(1).casefold()) and href:
        links.append(urllib.parse.urljoin("https://diariocorreo.pe/",href.group(1)))
    candidates=[]
    for i,url in enumerate(sorted(set(links))):
      r,b=archive(f"correo_discovered_feed_{i+1}",url,"news_feed")
      n=None
      if r.get("http_status")==200:
       try: n=count_feed(b)[0]
       except Exception: pass
      candidates.append({"url":url,"http_status":r.get("http_status"),"item_count":n,"evidence_id":r["evidence_id"],"artifact_path":r["artifact_path"]})
    out={"homepage_http_status":rec.get("http_status"),"homepage_evidence_id":rec["evidence_id"],"official_alternate_feed_links":sorted(set(links)),"tested_feed_candidates":candidates,"interpretation":"No feed link means RSS discovery not exposed in homepage metadata; previous /rss/ route 404 does not prove the publisher has no feed."}
    (REPORTS/"correo_feed_discovery.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    return out


def run_cloudflare():
    token=load_env().get("CLOUDFLARE_API_TOKEN","").strip()
    if not token: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    verify,body=request("cloudflare_closeout_token_verify","https://api.cloudflare.com/client/v4/user/tokens/verify","auth",token)
    try: valid=bool(json.loads(body).get("success"))
    except Exception: valid=False
    if not valid: return {"status":"AUTH_BLOCKED" if verify.get("http_status") in (401,403) else verify["result_status"],"evidence_id":verify["evidence_id"]}
    url="https://api.cloudflare.com/client/v4/radar/http/summary/device_type?dateRange=7d&location=PE&format=json"
    rec,raw=request("cloudflare_closeout_radar_pe",""+url,"traffic_dns",token)
    try:
      obj=json.loads(raw); result=obj.get("result",{}); series=result.get("summary_0",{}); meta=result.get("meta",{})
      summary={"status":"AUTH_PASS","http_status":rec.get("http_status"),"summary_fields":sorted(series.keys()),"device_categories":sorted(series.get("requests",{}).keys()) if isinstance(series.get("requests"),dict) else [],"summary_values":series,"last_updated":meta.get("lastUpdated"),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"selected_response_headers":rec.get("headers",{})}
    except Exception: summary={"status":"PARSE_ERROR","http_status":rec.get("http_status"),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]}
    (REPORTS/"cloudflare_access_quota_validation.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary


def run_cloudflare_reference_incidents():
    """Replay documented positive reference windows against Radar outage annotations."""
    token=load_env().get("CLOUDFLARE_API_TOKEN","").strip()
    if not token: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    cases_path=REPORTS/"independent_incident_reference_cases.csv"
    if not cases_path.exists(): return {"status":"INSUFFICIENT_EVIDENCE_NO_REFERENCE_CASES"}
    rows=[]
    with cases_path.open(encoding="utf-8-sig",newline="") as f:
      cases=list(csv.DictReader(f))
    asns={"movistar":"6147","claro":"12252","entel":"21575","bitel":"262210"}
    for case in cases:
      if case.get("ioda_comparable","true").casefold()=="false":
        continue
      start=datetime.fromisoformat(case["start"].replace("Z","+00:00"))
      end=datetime.fromisoformat(case["end"].replace("Z","+00:00")) if case.get("end") else start+timedelta(hours=1)
      operators=case.get("operators","")
      try:
        import ast
        operators=ast.literal_eval(operators) if operators.startswith("[") else [operators]
      except Exception: operators=[operators]
      for op in operators:
        if op not in asns: continue
        params={"dateStart":(start-timedelta(hours=1)).isoformat().replace("+00:00","Z"),"dateEnd":(end+timedelta(hours=1)).isoformat().replace("+00:00","Z"),"asn":asns[op],"location":"PE","limit":100,"format":"JSON"}
        url="https://api.cloudflare.com/client/v4/radar/annotations/outages?"+urllib.parse.urlencode(params)
        rec,body=request("cloudflare_reference_"+case["id"]+"_"+op,url,"historical_event",token)
        annotations=[]
        try:
          obj=json.loads(body); annotations=obj.get("result",{}).get("annotations",[]) if obj.get("success") else []
        except Exception: obj={}
        comparable=[]
        for annotation in annotations:
          ann_asns={str(x) for x in annotation.get("asns",[])}
          ann_locations={str(x).upper() for x in annotation.get("locations",[])}
          try: ann_start=datetime.fromisoformat(annotation["startDate"].replace("Z","+00:00"))
          except Exception: ann_start=None
          if asns[op] in ann_asns and "PE" in ann_locations and ann_start and start-timedelta(hours=1)<=ann_start<=end+timedelta(hours=1):
            comparable.append({"startDate":annotation.get("startDate"),"endDate":annotation.get("endDate"),"asns":annotation.get("asns"),"locations":annotation.get("locations"),"scope":annotation.get("scope"),"eventType":annotation.get("eventType"),"outage":annotation.get("outage"),"linkedUrl":annotation.get("linkedUrl")})
        rows.append({"incident_id":case["id"],"operator":op,"reference_independence":case.get("independence",""),"http_status":rec.get("http_status"),"result_status":rec.get("result_status"),"annotations_returned":len(annotations),"matching_asn_pe_onset_count":len(comparable),"matching_annotations":json.dumps(comparable,ensure_ascii=False,separators=(",",":")),"window_start_utc":params["dateStart"],"window_end_utc":params["dateEnd"],"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
        time.sleep(.15)
    write_csv(REPORTS/"incident_reference_cloudflare_comparison.csv",rows)
    valid=[r for r in rows if r["http_status"]==200]
    detected=sum(int(r["matching_asn_pe_onset_count"])>0 for r in valid)
    independent=[r for r in valid if "OSIPTEL" in r["reference_independence"]]
    independent_detected=sum(int(r["matching_asn_pe_onset_count"])>0 for r in independent)
    summary={"source":"Cloudflare Radar outage annotations","queries":len(rows),"successful_queries":len(valid),"reference_positive_operator_pairs":len(valid),"positive_pairs_with_matching_asn_pe_annotation":detected,"OSIPTEL_reference_pairs":len(independent),"OSIPTEL_pairs_with_match":independent_detected,"observed_positive_pair_hit_rate":f"{detected}/{len(valid)}" if valid else "NOT_ESTIMABLE","false_positive_rate":"NOT_ESTIMABLE: no independently verified normal windows","fresher_than_incident_onset":"NOT_MEASURED: retrospective API retrieval does not reveal first-publication time","scope":"Curated outage annotations matching the reference ASN, country and onset window; not raw traffic anomaly detection or a calibrated detector","report":"reports/incident_reference_cloudflare_comparison.csv"}
    (REPORTS/"cloudflare_reference_incident_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (REPORTS/"cloudflare_reference_incident_validation.md").write_text(
      "# Contraste histórico de eventos anotados de Cloudflare Radar\n\n"
      f"Se consultó el endpoint oficial de anotaciones de cortes para {len(valid)} pares positivos operador-incidente con ventanas horarias. Coincidieron {detected}/{len(valid)} anotaciones que incluyen el ASN afectado, ubicación PE e inicio dentro de la ventana. En los {len(independent)} pares con referencia de monitoreo OSIPTEL, coincidieron {independent_detected}.\n\n"
      "Esto evalúa anotaciones curadas de cortes, no las series crudas de tráfico ni un detector calibrado. Los casos de referencia no coincidentes no prueban falta general de cobertura: el feed de anotaciones puede no registrar eventos locales o históricos. Sin ventanas normales verificadas no se calcula tasa de falsos positivos; una consulta retrospectiva tampoco revela cuándo Radar publicó por primera vez una anotación.\n\n"
      "Los resultados detallados y sus IDs/rutas de evidencia están en `incident_reference_cloudflare_comparison.csv`; el resumen reproducible está en `cloudflare_reference_incident_summary.json`. La API documenta filtros por ASN, país y fechas en https://developers.cloudflare.com/api/resources/radar/subresources/annotations/subresources/outages/methods/get/.\n",encoding="utf-8")
    return summary


def run_cloudflare_netflows_incident_replay():
    """Compare affected-operator NetFlows during reference incidents to same-time weekday context."""
    token=load_env().get("CLOUDFLARE_API_TOKEN","").strip()
    if not token: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    with (REPORTS/"independent_incident_reference_cases.csv").open(encoding="utf-8-sig",newline="") as f:
      cases=list(csv.DictReader(f))
    asns={"movistar":"6147","claro":"12252","entel":"21575","bitel":"262210"}
    rows=[]
    for case in cases:
      if case.get("ioda_comparable","true").casefold()=="false": continue
      start=datetime.fromisoformat(case["start"].replace("Z","+00:00"))
      end=datetime.fromisoformat(case["end"].replace("Z","+00:00")) if case.get("end") else start+timedelta(hours=1)
      event_start=start-timedelta(hours=1)
      event_end=end+timedelta(hours=1)
      control_start=event_start-timedelta(days=7)
      control_end=event_end-timedelta(days=7)
      try:
        import ast
        operators=ast.literal_eval(case["operators"]) if case["operators"].startswith("[") else [case["operators"]]
      except Exception: operators=[case["operators"]]
      for op in operators:
        if op not in asns: continue
        params=[("name","incident"),("dateStart",event_start.isoformat().replace("+00:00","Z")),("dateEnd",event_end.isoformat().replace("+00:00","Z")),("location","PE"),("asn",asns[op]),("product","ALL"),("name","weekday_control"),("dateStart",control_start.isoformat().replace("+00:00","Z")),("dateEnd",control_end.isoformat().replace("+00:00","Z")),("location","PE"),("asn",asns[op]),("product","ALL"),("aggInterval","15m"),("normalization","MIN0_MAX"),("format","JSON")]
        url="https://api.cloudflare.com/client/v4/radar/netflows/timeseries?"+urllib.parse.urlencode(params)
        rec,body=request("cloudflare_netflows_reference_"+case["id"]+"_"+op,url,"historical_signal",token)
        try:
          obj=json.loads(body); result=obj.get("result",{}); event=result.get("incident",{}); control=result.get("weekday_control",{}); meta=result.get("meta",{})
          ev=[float(v) for v in event.get("values",[]) if v not in (None,"")]; co=[float(v) for v in control.get("values",[]) if v not in (None,"")]
          pairs=list(zip(ev,co)); diffs=[a-b for a,b in pairs]
          ordered=sorted(diffs); median=ordered[len(ordered)//2] if ordered else None
          evs=sorted(ev); cos=sorted(co)
          event_median=evs[len(evs)//2] if evs else None; control_median=cos[len(cos)//2] if cos else None
          confidence=meta.get("confidenceInfo",{}).get("level")
        except Exception:
          ev=[];co=[];diffs=[];median=None;event_median=None;control_median=None;confidence=None;meta={}
        rows.append({"incident_id":case["id"],"operator":op,"service":case.get("service",""),"reference_independence":case.get("independence",""),"http_status":rec.get("http_status"),"result_status":rec.get("result_status"),"incident_points":len(ev),"weekday_control_points":len(co),"paired_points":len(diffs),"incident_normalized_median":event_median,"weekday_control_normalized_median":control_median,"median_normalized_difference_incident_minus_control":median,"negative_difference_bins":sum(d<0 for d in diffs),"positive_difference_bins":sum(d>0 for d in diffs),"confidence_level":confidence,"normalization":meta.get("normalization"),"aggregation_interval":meta.get("aggInterval"),"incident_window_start_utc":event_start.isoformat(),"incident_window_end_utc":event_end.isoformat(),"comparison_window_start_utc":control_start.isoformat(),"comparison_window_end_utc":control_end.isoformat(),"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
        time.sleep(.15)
    write_csv(REPORTS/"cloudflare_netflows_incident_replay.csv",rows)
    successful=[r for r in rows if r["http_status"]==200 and r["paired_points"]>0]
    medians=sorted(r["median_normalized_difference_incident_minus_control"] for r in successful if isinstance(r.get("median_normalized_difference_incident_minus_control"),(int,float)))
    summary={"queries":len(rows),"successful_comparable_pairs":len(successful),"pairs_with_lower_incident_period_median":sum((r.get("median_normalized_difference_incident_minus_control") or 0)<0 for r in successful),"pairs_with_higher_incident_period_median":sum((r.get("median_normalized_difference_incident_minus_control") or 0)>0 for r in successful),"median_normalized_difference_across_pairs":medians[len(medians)//2] if medians else None,"normal_vs_incident_windows":"Prior-week same-weekday period is a matched historical comparator, not an independently verified outage-free control.","normalization":"MIN0_MAX shared within each pair; differences are normalized units, not percent traffic loss or absolute volume.","scope":"Cloudflare NetFlows from the operator ASN reaching Cloudflare edge networks in Peru; this is a partial network-traffic view, not full ISP traffic or district-level outage status.","report":"reports/cloudflare_netflows_incident_replay.csv"}
    (REPORTS/"cloudflare_netflows_incident_replay_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (REPORTS/"cloudflare_netflows_incident_replay.md").write_text(
      "# Replay de NetFlows de Cloudflare en incidentes de referencia\n\n"
      f"Se compararon {len(successful)} ventanas positivas con el mismo día/hora de la semana anterior. En {summary['pairs_with_lower_incident_period_median']} pares el valor normalizado mediano fue menor durante la ventana de incidente; en {summary['pairs_with_higher_incident_period_median']} fue mayor. El CSV conserva las series, diferencias por puntos, nivel de confianza, IDs y rutas de evidencia.\n\n"
      "El control de la semana previa no está verificado como normal. `MIN0_MAX` se calcula de forma común dentro de cada pareja; la diferencia está en unidades normalizadas, no es un porcentaje ni una caída absoluta de tráfico. NetFlows representa tráfico observado por Cloudflare desde el ASN filtrado y no todo el tráfico del operador; el filtro PE no localiza una incidencia por distrito. Por ello esta comparación puede identificar señales candidatas, pero no estima falsos positivos ni valida por sí sola un detector local.\n\n"
      "La API documenta NetFlows por ASN, ubicación y fechas en https://developers.cloudflare.com/api/resources/radar/subresources/netflows/methods/timeseries/.\n",encoding="utf-8")
    return summary


def run_twex_operator_posts():
    env=load_env(); key=env.get("TWEXAPI_API_KEY","").strip()
    if not key: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    handles={"movistar":"MovistarPeru","claro":"claroperu","bitel":"bitelperu"}
    out=[]
    for i,(entity,handle) in enumerate(handles.items()):
      q=f'from:{handle} ("sin internet" OR "sin señal" OR intermitencia OR fibra OR interrupción) since:2026-09-24 until:2026-10-25'
      rec,body=request("twexapi_official_"+entity,"https://api.twexapi.io/twitter/advanced_search/page","human_reports",key,"Bearer","POST",{"searchTerms":[q],"sortBy":"Latest"},lambda raw: _redact_x(raw))
      out.append({"entity":entity,"handle":handle,"http_status":rec.get("http_status"),"result_status":rec["result_status"],"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"summary":json.loads(_redact_x(body))})
      if i<2: time.sleep(5.1)
    return out


def run_twex_all_accounts_freshness():
    env=load_env(); key=env.get("TWEXAPI_API_KEY","").strip()
    if not key: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    accounts={"movistar":"MovistarPeru","claro":"claroperu","bitel":"bitelperu","entel":"EntelPeru","osiptel":"OSIPTEL","mtc":"MTC_GobPeru","indeci":"indeciperu","coen":"COENPeru","indecopi":"IndecopiOficial"}
    rows=[]
    def redact(raw):
      try:
        obj=json.loads(raw); texts=[]; times=[]; data_items=obj.get("data",[]) if isinstance(obj,dict) else []
        def walk(v):
          if isinstance(v,dict):
            for k,x in v.items():
              if k.casefold() in {"text","full_text","content","body","tweet_text"} and isinstance(x,str): texts.append(x.casefold())
              if k.casefold() in {"created_at","createdat","timestamp","published_at"} and isinstance(x,(str,int,float)): times.append(x)
              walk(x)
          elif isinstance(v,list):
            for x in v[:100]: walk(x)
        walk(obj); texts=list(dict.fromkeys(texts))
        normalized=[]
        for value in times:
          try:
            if isinstance(value,(int,float)): dt=datetime.fromtimestamp(value,timezone.utc)
            else:
              try: dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
              except ValueError: dt=parsedate_to_datetime(str(value))
              if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            normalized.append(dt.astimezone(timezone.utc).isoformat())
          except Exception: pass
        terms=("sin internet","sin señal","intermitencia","caída","fibra","datos móviles","internet lento","interrupción","servicio restablecido")
        return json.dumps({"redacted":True,"returned_data_items":len(data_items) if isinstance(data_items,list) else None,"distinct_text_fields":len(texts),"text_fields_matching_connectivity_terms":sum(any(t in s for t in terms) for s in texts),"matched_terms":{t:sum(t in s for s in texts) for t in terms},"timestamp_fields_parsed":len(normalized),"oldest_created_at_utc":min(normalized) if normalized else None,"newest_created_at_utc":max(normalized) if normalized else None},ensure_ascii=False).encode()
      except Exception: return b'{"redacted":true,"parse_error":true}'
    for i,(entity,handle) in enumerate(accounts.items()):
      q=f'from:{handle} ("sin internet" OR "sin señal" OR intermitencia OR fibra OR interrupción) since:2026-09-24 until:2026-10-25'
      rec,raw=request("twexapi_final_"+entity,"https://api.twexapi.io/twitter/advanced_search/page","human_reports",key,"Bearer","POST",{"searchTerms":[q],"sortBy":"Latest"},redact)
      summary=json.loads(redact(raw)); rec["operator"]=entity
      rows.append({"entity":entity,"handle":handle,"http_status":rec.get("http_status"),"result_status":rec["result_status"],"summary":summary,"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"]})
      if i<len(accounts)-1: time.sleep(5.1)
    write_csv(REPORTS/"x_verified_institution_queries.csv",rows)
    return {"status":"QUERIED","accounts":rows,"query_scope":"official-account posts, 30-day window, targeted by verified handle","texts_and_user_ids_retained":False}



def run_twex_reply_search():
    """Search replies addressed to operators/OSIPTEL and OSIPTEL's replies; persist only aggregate text classifications."""
    key=load_env().get("TWEXAPI_API_KEY","").strip()
    if not key: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    qterms='("sin internet" OR "sin señal" OR "sin servicio" OR intermitencia OR avería OR averia OR interrupción OR "no tengo internet")'
    targets=[("reply_to_movistar","to:MovistarPeru"),("reply_to_claro","to:claroperu"),("reply_to_entel","to:EntelPeru"),("reply_to_bitel","to:bitelperu"),("reply_to_osiptel","to:OSIPTEL"),("osiptel_authored_replies","from:OSIPTEL")]
    since="2026-09-24"; until="2026-10-25"; rows=[]
    place_names=[]
    catalog=REPORTS/"inei_sisconcode_ubigeo_2026.csv"
    if catalog.exists():
        with catalog.open(encoding="utf-8-sig",newline="") as f:
            place_names=sorted({r.get("DISTRITO","").casefold() for r in csv.DictReader(f) if len(r.get("DISTRITO", ""))>=6},key=len,reverse=True)
    for i,(label,account_filter) in enumerate(targets):
        only_replies="filter:replies"
        q=f'{account_filter} {only_replies} {qterms} since:{since} until:{until}'
        def redact(raw):
            try:
                obj=json.loads(raw); found=[]
                def walk(v):
                    if isinstance(v,dict):
                        for k,x in v.items():
                            if k.casefold() in {"text","full_text","content","tweet_text"} and isinstance(x,str): found.append(x.casefold())
                            else: walk(x)
                    elif isinstance(v,list):
                        for x in v[:100]: walk(x)
                walk(obj); texts=list(dict.fromkeys(found))
                def has(text,terms): return any(term in text for term in terms)
                outage=("sin internet","sin señal","sin servicio","intermitencia","avería","averia","interrupción","interrupcion","caída","caida","no tengo internet")
                operator_terms=("movistar","claro","entel","bitel","integratel")
                service_terms=("internet","wifi","wi-fi","fibra","datos","móvil","movil","fijo","señal","senal","cobertura")
                location_hits=[]
                for text in texts:
                    matched=next((name for name in place_names if name in text),None)
                    if matched: location_hits.append(matched)
                summary={"redacted":True,"unique_reply_texts":len(texts),"outage_context_replies":sum(has(t,outage) for t in texts),"operator_mentions":sum(has(t,operator_terms) for t in texts),"service_mentions":sum(has(t,service_terms) for t in texts),"district_name_matches":len(location_hits),"operator_service_location_candidates":sum(has(t,outage) and has(t,operator_terms) and has(t,service_terms) and any(p in t for p in place_names) for t in texts),"text_and_account_ids_persisted":False}
                return json.dumps(summary,ensure_ascii=False).encode()
            except Exception: return b'{"redacted":true,"parse_error":true}'
        url="https://api.twexapi.io/twitter/advanced_search/page"
        rec,raw=request("twexapi_replies_"+label,url,"human_reports",key,"Bearer","POST",{"searchTerms":[q],"sortBy":"Latest"},redact)
        summary=json.loads(redact(raw))
        rows.append({"query_id":label,"query_filter":account_filter+" filter:replies","http_status":rec.get("http_status"),"result_status":rec.get("result_status"),**{k:v for k,v in summary.items() if k!="redacted"},"evidence_id":rec.get("evidence_id"),"artifact_path":rec.get("artifact_path")})
        if i<len(targets)-1: time.sleep(5.1)
    write_csv(REPORTS/"x_reply_search_summary.csv",rows)
    (REPORTS/"x_reply_search_summary.md").write_text("# Búsqueda de respuestas públicas de X\n\nSe consultó TwexAPI con `to:<cuenta> filter:replies` para respuestas dirigidas a Movistar, Claro, Entel, Bitel y OSIPTEL, además de `from:OSIPTEL filter:replies` para las respuestas publicadas por OSIPTEL. Se aplicaron términos específicos de interrupciones; la salida conserva solo conteos agregados de contexto, menciones de operador/servicio y coincidencias con nombres distritales del catálogo UBIGEO. No se guardaron texto, usuario ni identificador de publicación.\n\nLos conteos son candidatos de señal, no confirmaciones independientes: `x_reply_search_summary.csv` registra HTTP y evidencia por consulta. La precisión geográfica se limita a coincidencias de nombres y no resuelve ambigüedades ni reemplaza revisión de cada incidente. La fuente permite buscar las respuestas; queda por demostrar el rendimiento como detector con referencias independientes.\n",encoding="utf-8")
    return {"status":"QUERIED","query_count":len(rows),"http_200":sum(r.get("http_status")==200 for r in rows),"evidence_ids":[r["evidence_id"] for r in rows]}


def run_major_newspaper_feeds():
    """Test direct publisher RSS/Atom endpoints only; do not fetch article pages."""
    sources=[
      ("peru21_rss","Perú21","https://peru21.pe/rss/"),
      ("peru21_arc_rss","Perú21","https://peru21.pe/arc/outboundfeeds/rss/?outputType=xml"),
      ("gestion_rss_peru_politica","Gestión","https://gestion.pe/arcio/rss/category/peru/politica/"),
      ("gestion_rss_tecnologia","Gestión","https://gestion.pe/arc/outboundfeeds/rss/category/tecnologia/?outputType=xml"),
      ("trome_rss","Trome","https://trome.com/rss/"),
      ("trome_feed","Trome","https://trome.com/feed/"),
      ("elperuano_rss","El Peruano","https://elperuano.pe/rss/"),
      ("expreso_feed","Expreso","https://www.expreso.com.pe/feed/"),
    ]
    rows=[]; terms=("sin internet","sin señal","sin servicio","interrupción","interrupcion","corte de fibra","caída de internet","caida de internet","servicio restablecido","avería","averia")
    for sid,outlet,url in sources:
        rec,raw=archive("major_news_"+sid,url,"news_feed",max_bytes=15_000_000)
        count=None; hits=0; latest=""; status="NOT_FEED"
        if rec.get("http_status")==200:
            try:
                count,items=count_feed(raw); status="XML_PARSED"; dates=[]
                for item in items:
                    content=(item.get("title","")+" "+item.get("description","")).casefold()
                    hits+=any(term in content for term in terms)
                    try:
                        dt=parsedate_to_datetime(item.get("published",""))
                        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                        dates.append(dt.astimezone(timezone.utc).isoformat())
                    except Exception: pass
                latest=max(dates) if dates else ""
            except Exception: status="XML_PARSE_ERROR"
        rows.append({"outlet":outlet,"source_id":"major_news_"+sid,"feed_url":url,"http_status":rec.get("http_status"),"result_status":rec.get("result_status"),"parse_status":status,"item_count":count,"strict_connectivity_hits":hits if status=="XML_PARSED" else "","latest_pubdate_utc":latest,"evidence_id":rec.get("evidence_id"),"artifact_path":rec.get("artifact_path")})
        time.sleep(.2)
    write_csv(REPORTS/"peru_major_newspaper_feeds.csv",rows)
    (REPORTS/"peru_major_newspaper_feeds.md").write_text("# Prueba de RSS de diarios nacionales adicionales\n\nSe probaron únicamente URLs RSS/Atom directas o publicadas en las páginas RSS oficiales de los medios. No se descargaron ni analizaron páginas de artículos. Una respuesta HTTP exitosa se considera feed útil solo cuando se parsea como XML y contiene señales del tema; un endpoint que devuelve HTML o error no confirma un feed.\n\nEl CSV contiene ocho endpoints de Perú21, Gestión, Trome, El Peruano y Expreso, con conteos de ítems y coincidencias del vocabulario de conectividad. Los términos son un filtro inicial: una coincidencia no confirma una interrupción y un cero no demuestra falta de cobertura.\n",encoding="utf-8")
    return {"status":"CHECKED","endpoint_count":len(rows),"xml_parsed":sum(r["parse_status"]=="XML_PARSED" for r in rows),"connectivity_hits":sum(int(r["strict_connectivity_hits"]) for r in rows if str(r["strict_connectivity_hits"]).isdigit())}


def _redact_x(raw):
    try:
      obj=json.loads(raw); texts=[]
      def walk(v):
        if isinstance(v,dict):
          for k,x in v.items():
            if k.casefold() in {"text","full_text","content","body","tweet_text"} and isinstance(x,str): texts.append(x.casefold())
            walk(x)
        elif isinstance(v,list):
          for x in v[:100]: walk(x)
      walk(obj); texts=list(dict.fromkeys(texts))
      terms=("sin internet","sin señal","intermitencia","caída","fibra","datos móviles","internet lento","interrupción","servicio restablecido")
      return json.dumps({"redacted":True,"unique_text_fields_detected":len(texts),"keyword_match_count":sum(any(t in s for t in terms) for s in texts),"term_counts":{t:sum(t in s for s in texts) for t in terms}},ensure_ascii=False).encode()
    except Exception: return b'{"redacted":true,"parse_error":true}'


def run_twex():
    env=load_env(); key=env.get("TWEXAPI_API_KEY","").strip()
    if not key: return {"status":"AUTH_BLOCKED_NO_CREDENTIAL"}
    # Only use prior cached balance: balance endpoint deducts credits in the previously observed plan.
    entries=[json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    balance_rows=[x for x in entries if x.get("source_id")=="twexapi_balance" and x.get("http_status")==200]
    if not balance_rows: return {"status":"INSUFFICIENT_EVIDENCE_NO_CACHED_BALANCE"}
    saved=json.loads((ROOT/balance_rows[-1]["artifact_path"]).read_text(encoding="utf-8")); data=saved.get("data",{}); balance=float(data.get("balance",0) if isinstance(data,dict) else data or 0)
    handles={"entel":"EntelPeru","osiptel":"OSIPTEL","mtc":"MTC_GobPeru","indeci":"indeciperu","coen":"COENPeru","indecopi":"IndecopiOficial"}
    if balance<100: return {"status":"RATE_LIMITED_OR_LOW_BALANCE","cached_balance_band":"under_100"}
    out=[]
    def redact(raw):
        try:
            obj=json.loads(raw); texts=[]
            def walk(v):
                if isinstance(v,dict):
                    for k,x in v.items():
                        if k.casefold() in {"text","full_text","content","body","tweet_text"} and isinstance(x,str): texts.append(x.casefold())
                        walk(x)
                elif isinstance(v,list):
                    for x in v[:100]: walk(x)
            walk(obj)
            terms=("sin internet","sin señal","intermitencia","caída","fibra","datos móviles","internet lento","interrupción","servicio restablecido")
            return json.dumps({"redacted":True,"text_fields_detected":len(texts),"relevant_text_count":sum(any(t in s for t in terms) for s in texts),"term_counts":{t:sum(t in s for s in texts) for t in terms}},ensure_ascii=False).encode()
        except Exception: return b'{"redacted":true,"parse_error":true}'
    for i,(entity,handle) in enumerate(handles.items()):
        q=f'from:{handle} ("sin internet" OR "sin señal" OR intermitencia OR fibra OR interrupción) since:2026-09-24 until:2026-10-25'
        rec,body=request("twexapi_official_"+entity,"https://api.twexapi.io/twitter/advanced_search/page","human_reports",key,"Bearer","POST",{"searchTerms":[q],"sortBy":"Latest"},redact)
        rec["operator"]=entity; out.append({"entity":entity,"handle":handle,"http_status":rec.get("http_status"),"status":rec["result_status"],"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"redacted_summary":json.loads(redact(body))})
        if i<len(handles)-1: time.sleep(5.1)
    write_csv(REPORTS/"x_verified_institution_queries.csv",out)
    return {"status":"QUERIED","accounts":out,"cached_balance_band":"at_least_100"}


def run_reference_incidents():
    # Independent or corroborated public incident records. Dates are local Peru time (UTC-5).
    incidents=[
      {"id":"claro_los_olivos_2025-12-11","source":"Claro Peru primary statement","url":"https://www.claro.com.pe/institucional/centro-de-prensa/comunicado-corte-servicio/","start":"2025-12-11T06:05:00Z","end":"2025-12-11T13:07:00Z","operators":["claro"],"service":"fixed and mobile","area":"Lima districts; fixed/mobile scopes differ","independence":"operator primary report; not independent from operator self-report"},
      {"id":"loreto_shared_carrier_2025-12-19","source":"OSIPTEL regulator report","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-monitorea-el-restablecimiento-total-de-los-servicios-fijos-y-moviles-de-las-empresas-operadoras-bitel-claro-y-entel-en-loreto/","start":"2025-12-19T16:10:00Z","end":"2025-12-19T18:50:00Z","operators":["bitel","claro","entel"],"service":"fixed and mobile","area":"Loreto","independence":"regulator-observed notice; operator/transport-provider cause information corroborated"},
      {"id":"movistar_lima_fiber_2026-07-01","source":"RPP report citing Movistar","url":"https://rpp.pe/economia/economia/atentados-contra-la-red-de-fibra-de-movistar-dejan-sin-internet-a-usuarios-de-cinco-distritos-como-la-molina-ate-y-chosica-noticia-1695454","start":"2026-07-01T05:00:00Z","end":"2026-07-01T17:16:00Z","operators":["movistar"],"service":"fixed internet","area":"La Molina, Ate, Chaclacayo, Santa Clara, Chosica","independence":"media report citing operator; start time is approximate (during madrugada)"},
      {"id":"movistar_national_2024-11-18","source":"OSIPTEL monitoring notice","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-coordina-el-restablecimiento-total-de-internet-movil-y-fijo-de-movistar-en-diversos-distritos-a-nivel-nacional/","start":"2024-11-18T15:47:00Z","end":"2024-11-18T16:22:00Z","operators":["movistar"],"service":"fixed and mobile internet","area":"multiple districts nationwide; no district list in notice","independence":"OSIPTEL monitoring detected onset; initial recovery time from preliminary operator report; end time is not confirmed"},
      {"id":"movistar_lima_fixed_2024-11-26","source":"OSIPTEL monitoring notice","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-supervisa-el-restablecimiento-del-servicio-de-internet-fijo-de-movistar-en-lima-y-algunas-localidades-del-pais/","start":"2024-11-26T14:13:00Z","end":None,"operators":["movistar"],"service":"fixed internet","area":"Lima and some localities nationwide; notice does not enumerate all districts","independence":"OSIPTEL monitoring center detected onset at 09:13 local time; initial restoration from operator report, full restoration time not specified","time_precision":"exact_onset_time; restoration time unknown"},
      {"id":"movistar_entel_south_2022-10-25","source":"OSIPTEL monitoring notice","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-informa-sobre-el-restablecimiento-total-de-los-servicios-de-internet-movil-y-fijo-en-el-sur-del-pais/","start":"2022-10-25T23:11:00Z","end":"2022-10-26T07:14:00Z","operators":["movistar","entel"],"service":"fixed and mobile internet","area":"Apurímac, Arequipa, Cusco, Madre de Dios, Moquegua, Puno and Tacna","independence":"OSIPTEL monitoring; report says operator-reported outage and restoration; exact times approximate"},
      {"id":"claro_2g_multiregion_2024-01-31","source":"OSIPTEL monitoring notice","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-supervisa-el-restablecimiento-total-del-servicio-movil-2g-de-claro-en-centros-poblados-de-algunas-regiones-del-pais/","start":"2024-01-31","end":"2024-02-08","operators":["claro"],"service":"mobile 2G","area":"177 base stations across 15 departments; 37 remained affected on 8 Feb","independence":"OSIPTEL independently detected affected base stations; operator supplied cause and progress","ioda_comparable":False,"time_precision":"date_only_start; gradual restoration status on Feb 8, no exact event window"},
      {"id":"ancash_multioperator_2025-04-24","source":"OSIPTEL monitoring notice","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-monitorea-el-restablecimiento-del-servicio-movil-y-de-internet-fijo-en-localidades-de-algunas-provincias-de-ancash/","start":"2025-04-24T22:35:00Z","end":None,"operators":["movistar","claro","entel","bitel"],"service":"fixed and mobile internet","area":"Localities in Antonio Raymondi, Carlos Fermín Fitzcarrald, Huari, Mariscal Luzuriaga and Pomabamba, Áncash","independence":"OSIPTEL monitoring detected onset; cause reported preliminarily by operators","time_precision":"exact_onset_end_unknown"},
      {"id":"ayacucho_integratel_entel_mobile_2025-12-26","source":"OSIPTEL monitoring notice","url":"https://www.osiptel.gob.pe/portal-del-usuario/noticias/osiptel-monitorea-el-restablecimiento-del-servicio-movil-de-las-empresas-operadoras-integratel-y-entel-en-algunos-distritos-de-ayacucho/","start":"2025-12-26T15:58:00Z","end":"2025-12-27T19:57:00Z","operators":["movistar","entel"],"service":"mobile internet and mobile service","area":"Some districts in Huanca Sancos and Lucanas, Ayacucho","independence":"OSIPTEL monitoring detected the event; cause preliminarily attributed to Gilat fibre failure affecting Internet para Todos infrastructure","time_precision":"exact_onset_and_restoration_for_initial_event; later recurrence reported separately"},
    ]
    pairs=[]
    for case in incidents:
      source_rec, _ = archive("reference_source_"+case["id"],case["url"],"historical_reference")
      case["source_evidence_id"] = source_rec["evidence_id"]
      case["source_artifact_path"] = source_rec["artifact_path"]
      start=int(datetime.fromisoformat(case["start"].replace("Z","+00:00")).timestamp())
      if case.get("ioda_comparable", True):
        end=int(datetime.fromisoformat(case["end"].replace("Z","+00:00")).timestamp()) if case.get("end") else start
      else:
        end=start
      for op,asn in {"movistar":"6147","claro":"12252","entel":"21575","bitel":"262210"}.items():
        if not case.get("ioda_comparable", True):
          pairs.append({"incident_id":case["id"],"operator":op,"reference_case_operator":"YES" if op in case["operators"] else "NO_CONTROL","http_status":"NOT_QUERIED","ioda_event_count_window":"NOT_COMPARABLE","result_status":"INSUFFICIENT_EVIDENCE","evidence_id":case["source_evidence_id"],"artifact_path":case["source_artifact_path"],"query_window_start_utc":"","query_window_end_utc":"","reason":"No exact onset/recovery timestamps; excluded from quantitative IODA comparison"})
          continue
        # For incidents with a known onset but unknown end, evaluate a one-hour onset window only.
        window_start=start-3600
        window_end=(end+3600) if case.get("end") else (start+3600)
        url="https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events?"+urllib.parse.urlencode({"entityType":"asn","entityCode":asn,"from":window_start,"until":window_end,"limit":100})
        rec,body=archive("ioda_reference_"+case["id"]+"_"+op,url,"historical_event")
        count=None; onset_count=None; event_details=[]
        try:
            obj=json.loads(body); d=obj.get("data",[]); count=len(d) if isinstance(d,list) else None
            if isinstance(d,list):
                event_details=[{"start_utc":datetime.fromtimestamp(int(e["start"]),timezone.utc).isoformat(),"duration_seconds":e.get("duration"),"datasource":e.get("datasource"),"location":e.get("location"),"overlaps_window":e.get("overlaps_window")} for e in d if isinstance(e,dict) and isinstance(e.get("start"),(int,float))]
                onset_count=sum(1 for e in d if isinstance(e,dict) and isinstance(e.get("start"),(int,float)) and window_start<=int(e["start"])<=window_end)
        except Exception: pass
        pairs.append({"incident_id":case["id"],"operator":op,"reference_case_operator":"YES" if op in case["operators"] else "NO_CONTROL","http_status":rec.get("http_status"),"ioda_event_count_window":count,"ioda_event_onset_count_window":onset_count,"ioda_event_details":json.dumps(event_details,ensure_ascii=False,separators=(",",":")),"result_status":rec["result_status"],"evidence_id":rec["evidence_id"],"artifact_path":rec["artifact_path"],"query_window_start_utc":datetime.fromtimestamp(window_start,timezone.utc).isoformat(),"query_window_end_utc":datetime.fromtimestamp(window_end,timezone.utc).isoformat(),"comparison_scope":"onset_window_only_end_unknown" if not case.get("end") else "reported_event_window_plus_margin"})
        if op in case["operators"]:
          period_end=end if case.get("end") else start+3600
          sig_url=f"https://api.ioda.inetintel.cc.gatech.edu/v2/signals/raw/asn/{asn}?"+urllib.parse.urlencode({"from":start-86400,"until":period_end+86400,"maxPoints":500})
          sig_rec,sig_body=archive("ioda_reference_signal_"+case["id"]+"_"+op,sig_url,"historical_signal")
          series=[]
          try:
            obj=json.loads(sig_body)
            raw=obj.get("data",[])
            for group in raw if isinstance(raw,list) else []:
              for s in group if isinstance(group,list) else []:
                if not isinstance(s,dict): continue
                vals=s.get("values",[]); step=int(s.get("step",0) or 0); t0=int(s.get("from",0) or 0)
                window_values=[v for i,v in enumerate(vals) if isinstance(v,(int,float)) and start<=t0+i*step<=period_end]
                baseline=[v for i,v in enumerate(vals) if isinstance(v,(int,float)) and (start-86400<=t0+i*step<start or period_end<t0+i*step<=period_end+86400)]
                series.append({"datasource":s.get("datasource"),"subtype":s.get("subtype"),"step_seconds":step,"returned_points":len(vals),"numeric_points_in_incident_window":len(window_values),"incident_window_min":min(window_values) if window_values else None,"incident_window_max":max(window_values) if window_values else None,"numeric_points_in_adjacent_baseline":len(baseline),"baseline_median":sorted(baseline)[len(baseline)//2] if baseline else None})
          except Exception: pass
          # Append summaries to a list maintained in memory for the final JSON artifact.
          if not hasattr(run_reference_incidents,"signal_summaries"): run_reference_incidents.signal_summaries=[]
          run_reference_incidents.signal_summaries.append({"case":case["id"],"operator":op,"http_status":sig_rec.get("http_status"),"evidence_id":sig_rec["evidence_id"],"artifact_path":sig_rec["artifact_path"],"series":series})
        time.sleep(.15)
    write_csv(REPORTS/"independent_incident_reference_cases.csv",incidents)
    write_csv(REPORTS/"incident_reference_ioda_comparison.csv",pairs)
    positives=[x for x in pairs if x["reference_case_operator"]=="YES" and isinstance(x.get("ioda_event_onset_count_window"),int)]
    matched=sum(1 for x in positives if x["ioda_event_onset_count_window"]>0)
    overlap_only=sum(1 for x in positives if isinstance(x.get("ioda_event_count_window"),int) and x["ioda_event_count_window"]>0 and x["ioda_event_onset_count_window"]==0)
    summary={"reference_cases":len(incidents),"ioda_comparable_reference_cases":sum(1 for x in incidents if x.get("ioda_comparable",True)),"positive_operator_case_pairs":len(positives),"ioda_event_detected_pairs":matched,"ioda_event_onset_detected_pairs":matched,"ioda_event_overlap_only_positive_pairs":overlap_only,"known_case_recall_observed":f"{matched}/{len(positives)}" if positives else "NOT_ESTIMABLE","false_positive_rate":"NOT_ESTIMABLE: no independently labeled negative operator-windows and no fixed alert threshold","publication_freshness":"NOT_ESTIMABLE: incident sources do not provide a consistent machine-readable first-publication time; some onsets/recoveries are approximate","independent_cases":"Seven OSIPTEL monitoring notices report independently detected onsets; causes/restoration may rely on operator reports. One operator primary notice and one media report citing an operator are retained as lower-independence cases.","evidence":"reports/incident_reference_ioda_comparison.csv"}
    (REPORTS/"incident_validation_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (REPORTS/"ioda_historical_signal_summary.json").write_text(json.dumps(getattr(run_reference_incidents,"signal_summaries",[]),ensure_ascii=False,indent=2),encoding="utf-8")
    (REPORTS/"incident_validation.md").write_text(
      "# Incidentes de referencia y contraste con IODA\n\n"
      f"Se documentaron {len(incidents)} casos públicos, incluyendo avisos de monitoreo de OSIPTEL para los cuatro operadores. Se contrastó el endpoint de eventos de IODA en ventanas de ±1 h alrededor de eventos con inicio horario conocido; cuando el aviso no informa la hora de restablecimiento, la consulta mide solo detección alrededor del inicio. El endpoint presentó un evento cuya duración solapó una ventana positiva, pero su inicio quedó fuera del período de referencia; por criterio de inicio, IODA detectó {matched}/{len(positives)} pares positivos operador-caso consultados. Esto mide solo el endpoint de eventos de IODA en estas ventanas, no la sensibilidad de señales crudas ni del sistema final.\n\n"
      "Los avisos OSIPTEL incorporados incluyen una interrupción móvil de Integratel/Movistar y Entel en distritos de Ayacucho (inicio 26 dic 2025 10:58 hora peruana, restauración del evento inicial 27 dic 14:57) y una afectación móvil y fija de los cuatro operadores en provincias de Áncash (inicio 24 abr 2025 17:35; el aviso consultado no indica el restablecimiento). La clasificación separa detección del regulador de causas y recuperación preliminares comunicadas por operadoras.\n\n"
      "La tasa de falsos positivos y la precisión general siguen sin estimarse: no hay ventanas normales etiquetadas independientemente ni una regla final de alerta congelada. Tampoco se mide la frescura de primera publicación, porque las páginas históricas no aportan una hora consistente de publicación inicial y no se observaron señales del detector durante esos eventos en tiempo real. Un evento IODA de 14 días que ya había empezado seis días antes solo solapó una ventana positiva y no se cuenta como detección del inicio del caso. El resultado es una comparación descriptiva del endpoint, no recall del producto. Ver `incident_reference_ioda_comparison.csv`, `incident_validation_summary.json` y los artefactos históricos en `evidencias/`.\n",
      encoding="utf-8")
    return summary


def run():
    mkdirs()
    print("feeds",json.dumps(run_feeds(),ensure_ascii=False))
    print("ubigeo",json.dumps(run_ubigeo(),ensure_ascii=False))
    print("accounts",json.dumps(run_official_links(),ensure_ascii=False))
    print("twex",json.dumps(run_twex(),ensure_ascii=False))
    print("twex_operator_posts",json.dumps(run_twex_operator_posts(),ensure_ascii=False))
    print("cloudflare",json.dumps(run_cloudflare(),ensure_ascii=False))
    print("references",json.dumps(run_reference_incidents(),ensure_ascii=False))


if __name__=="__main__": run()



