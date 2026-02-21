# iQs VW Exporter V2.7 - Per-Component Quantities (Verified API)
# ═══════════════════════════════════════════════════════════════
# V2.7 adds per-component area/volume/length using VERIFIED API calls:
#   GetComponentNetArea(h, i)       → mm² (one face, minus openings)
#   GetComponentNetVolume(h, i)     → mm³ (minus openings)
#   GetWallCompStartPts(h, i)      → per-component start (left,center,right)
#   GetWallCompEndPts(h, i)        → per-component end (left,center,right)
#   GetWallCornerHeights(h)        → (startTop, startBot, endTop, endBot)
#   GetWallOverallHeights(h)       → (top, bottom)
#   GetCoreWallComponent(h)        → integer index
#   HLength(h)                     → wall centreline length (mm)
#
# All signatures verified against VW_Superfile_ObjectTypes_Callables Excel.
# Units: VW native mm/mm²/mm³. Converted to m/m²/m³ in output.
# ═══════════════════════════════════════════════════════════════
import vs, json, os, time, uuid, math, re
import urllib.request, urllib.error
from datetime import datetime
CFG = {
    "scope":"ALL","status_every_n":500,"limit_objects":0,
    "file_prefix":"vw_qdump","write_jsonl":True,"write_debug":True,"promote_user_fields":True,"promote_max_fields":5000,
    "probe_mode":"safe",  # off|safe (captures lots w/ try/except)
    "probe_store_errors":True,
    "export_dir":"/Users/jameslakiss/Documents/Develop/iQs/10 VW Integration/JSONL_Exports",
    "wall_types":[68],"slab_types":[71],"roof_types":[84],
    "sentinel":1.0e50,"debug_first_n":40,
    "uuid_rec":"iQs_Object","uuid_fld":"uuid",
    "iqs_url":"http://localhost:3000/vw_imports",
}
CLASS_LUT = {}
def build_class_lookup():
    global CLASS_LUT; CLASS_LUT = {}
    n = sc(vs.ClassNum, default=0) or 0
    for i in range(1, n+1):
        cn = sc(vs.ClassList, i)
        if not cn: continue
        raw = sc(vs.Name2Index, cn)
        idx = raw
        if isinstance(raw,(list,tuple)):
            idx = next((v for v in raw if isinstance(v,int) and not isinstance(v,bool)), None)
        if isinstance(idx, int):
            CLASS_LUT[idx] = cn; CLASS_LUT[str(idx)] = cn
def resolve_class(val):
    if val is None: return None
    if isinstance(val, str) and not val.isdigit(): return val
    r = CLASS_LUT.get(val) or CLASS_LUT.get(str(val))
    if r: return r
    try: return CLASS_LUT.get(int(val)) or val
    except: return val
def export_class_list(d):
    classes = []
    n = sc(vs.ClassNum, default=0) or 0
    for i in range(1, n+1):
        cn = sc(vs.ClassList, i);
        if not cn: continue
        c = {"name": cn, "local_idx": i}
        raw = sc(vs.Name2Index, cn)
        idx = raw
        if isinstance(raw,(list,tuple)):
            idx = next((v for v in raw if isinstance(v,int) and not isinstance(v,bool)), None)
        if isinstance(idx, int): c["idx"] = idx
        h = sc(vs.GetObject, cn)
        if h:
            if hv("GetObjectUuid"):
                u = sc(vs.GetObjectUuid, h)
                if isinstance(u,(list,tuple)): u = next((v for v in u if isinstance(v,str) and len(v)>8), None)
                if u: c["uuid"] = str(u)
            if hv("GetDescriptionText"):
                d2 = sc(vs.GetDescriptionText, h)
                if isinstance(d2,(list,tuple)): d2 = next((v for v in d2 if isinstance(v,str) and len(v)>2), None)
                if d2 and str(d2).strip(): c["desc"] = str(d2).strip()
        classes.append(c)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = os.path.join(d, f"vw_class_list_{ts}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump({"class_count": len(classes), "classes": classes}, f, indent=2, ensure_ascii=False)
    return fp, len(classes)
MAT_LUT = {}
hv = lambda a: hasattr(vs, a)
def _enum_materials():
    mats = []
    if not hv("BuildResourceList"): return mats
    for rtype in [97, 150]:
        try:
            raw = sc(vs.BuildResourceList, rtype, 0, '', 0)
            if not raw: continue
            lid, cnt = (raw[0], raw[1]) if isinstance(raw,(list,tuple)) and len(raw)>=2 else (raw, 0)
            cnt = int(cnt or 0)
            if cnt <= 0 or not lid: continue
            for i in range(1, cnt+1):
                nm = sc(vs.GetNameFromResourceList, lid, i)
                if isinstance(nm,(list,tuple)):
                    nm = next((v for v in nm if isinstance(v,str) and v.strip()), None)
                if not nm: continue
                idx_raw = sc(vs.Name2Index, nm)
                idx = idx_raw
                if isinstance(idx_raw,(list,tuple)):
                    idx = next((v for v in idx_raw if isinstance(v,int) and not isinstance(v,bool)), None)
                mats.append((nm, idx, i))
            if mats: break
        except: continue
    return mats
def build_material_lookup():
    global MAT_LUT; MAT_LUT = {}
    for nm, idx, _ in _enum_materials():
        if isinstance(idx, int):
            MAT_LUT[idx] = nm; MAT_LUT[str(idx)] = nm
            MAT_LUT[idx+1] = nm; MAT_LUT[str(idx+1)] = nm
def resolve_material(val):
    if val is None: return None
    if isinstance(val, str) and not val.isdigit() and val not in ("0",""):
        return val
    r = MAT_LUT.get(val) or MAT_LUT.get(str(val))
    if r: return r
    try:
        if hasattr(val,'__class__') and 'Handle' in type(val).__name__:
            nm = sc(vs.GetName, val)
            if nm and isinstance(nm,str) and nm.strip(): return nm.strip()
    except: pass
    try: return MAT_LUT.get(int(val)) or val
    except: return val
def export_material_list(d):
    mats = [{"name":nm,"local_idx":li,**({"idx":idx} if isinstance(idx,int) else {})} for nm,idx,li in _enum_materials()]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = os.path.join(d, f"vw_material_list_{ts}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump({"material_count":len(mats),"materials":mats}, f, indent=2, ensure_ascii=False)
    return fp, len(mats)
def sc(fn,*a,default=None):
    try: return fn(*a)
    except: return default
_UNIT_RE=re.compile(r'(mm|cm|m|in|ft|°|″|\'|")\s*$',re.IGNORECASE)
def _su(val):
    return _UNIT_RE.sub('',val).strip() if isinstance(val,str) else val
def sf(val,default=None):
    if val is None: return default
    try:
        f=float(_su(val))
        return f if f>0 else default
    except: return default
def sfz(val,default=None):
    if val is None: return default
    try: return float(_su(val))
    except: return default
def sr(fn,*a,default=None):
    raw=sc(fn,*a,default=default)
    v=unpack_real(raw)
    return v if v is not None and v>0 else default
def resolve_dir():
    d = CFG.get("export_dir","").strip()
    if d:
        os.makedirs(d, exist_ok=True)
        return d
    p=sc(vs.GetFPathName,default="")
    return os.path.dirname(p) if p else os.path.expanduser("~/Desktop")
def mk_paths(d):
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    b=f"{CFG['file_prefix']}_{CFG['scope'].lower()}_{ts}"
    return os.path.join(d,b+".jsonl"),os.path.join(d,b+"_debug.txt")
def get_bbox(h):
    bb=sc(vs.GetBBox,h)
    if not bb: return None
    try:
        (x1,y1),(x2,y2)=bb[0],bb[1]
        return {"x1":x1,"y1":y1,"x2":x2,"y2":y2,"width":abs(x2-x1),"height":abs(y2-y1),"cx":(x1+x2)/2,"cy":(y1+y2)/2}
    except: return {"raw":bb}
def layer_name(h):
    lh=sc(vs.GetLayer,h)
    if not lh: return None
    if hv("GetLName"):
        n=sc(vs.GetLName,lh)
        if n: return n
    return sc(vs.GetName,lh)
def unpack_pt(raw):
    if raw is None: return None
    if isinstance(raw, (list,tuple)) and len(raw)>=2 and isinstance(raw[0], bool):
        pt=raw[1]
        if isinstance(pt,(list,tuple)): return pt
        return None
    if isinstance(raw,(list,tuple)) and len(raw)>=2:
        try:
            float(raw[0]); return raw
        except: return None
    return None
def unpack_real(raw):
    if raw is None: return None
    if isinstance(raw,(list,tuple)):
        for v in raw:
            if isinstance(v,bool): continue
            try: return float(v)
            except: continue
        return None
    try: return float(raw)
    except: return None
def get_origin(h):
    r={}
    if hv("GetObjectVariablePoint"):
        pt=unpack_pt(sc(vs.GetObjectVariablePoint,h,7))
        if pt and len(pt)>=2:
            ox,oy=float(pt[0]),float(pt[1])
            if not is_sent(ox,oy):
                r["ox"],r["oy"]=ox,oy
                if len(pt)>=3:
                    try:
                        oz=float(pt[2])
                        if abs(oz)<CFG["sentinel"]: r["oz"]=oz
                    except: pass
    if hv("GetObjectVariableReal"):
        rot=unpack_real(sc(vs.GetObjectVariableReal,h,9))
        if rot is not None and abs(rot)<CFG["sentinel"]: r["rot"]=rot
    if "ox" not in r and hv("GetSymLoc"):
        pt=unpack_pt(sc(vs.GetSymLoc,h))
        if pt and len(pt)>=2:
            ox,oy=float(pt[0]),float(pt[1])
            if not is_sent(ox,oy): r["ox"],r["oy"]=ox,oy
    return r or None
def nrec(h):
    if hv("NumRecords"): return sc(vs.NumRecords,h,default=0) or 0
    if hv("GetNumRecords"): return sc(vs.GetNumRecords,h,default=0) or 0
    return 0
def get_recs(h):
    out=[]
    for i in range(1,nrec(h)+1):
        rh=sc(vs.GetRecord,h,i)
        if not rh: continue
        rn=sc(vs.GetName,rh)
        if not rn: continue
        ro={"record":rn,"fields":{}}
        nf=sc(vs.NumFields,rh,default=0) or 0
        for j in range(1,nf+1):
            fn=sc(vs.GetFldName,rh,j)
            if fn: ro["fields"][fn]=sc(vs.GetRField,h,rn,fn)
        out.append(ro)
    return out
def get_pio(h):
    pr=sc(vs.GetParametricRecord,h)
    if not pr: return None
    pn=sc(vs.GetName,pr)
    if not pn: return None
    nf=sc(vs.NumFields,pr,default=0) or 0
    flds={}
    for j in range(1,nf+1):
        fn=sc(vs.GetFldName,pr,j)
        if fn: flds[fn]=sc(vs.GetRField,h,pn,fn)
    return {"pio":pn,"fields":flds}
def ensure_record_format(rec, fld):
    try:
        vs.NewField(rec, fld, "", 4, 0)  # 4=Text
    except:
        pass
    return sc(vs.GetObject, rec)
def has_record_attached(h, rec_name):
    try:
        n = sc(vs.NumRecords, h, default=0) or 0
    except:
        n = 0
    for i in range(1, n+1):
        rh = sc(vs.GetRecord, h, i)
        if not rh:
            continue
        rn = sc(vs.GetName, rh)
        if rn == rec_name:
            return True
    return False
def ensure_uuid(h):
    rec,fld=CFG["uuid_rec"],CFG["uuid_fld"]
    ensure_record_format(rec, fld)
    if not has_record_attached(h, rec):
        try:
            sc(vs.SetRecord, h, rec)
        except:
            pass
    cur=sc(vs.GetRField, h, rec, fld)
    if cur and str(cur).strip():
        return str(cur).strip(),"existing"
    nid=str(uuid.uuid4())
    sc(vs.SetRField, h, rec, fld, nid)
    return nid,"assigned"
def cv(v):
    if v is None: return None
    s=str(v).strip()
    return None if s.lower() in ("","none","null","0") else s
def promote(obj):
    recs = obj.get("records") or []
    p = obj.get("pio_params") or {}
    for rec in recs:
        ff = rec.get("fields") or {}
        for key,slot in [("name","prm2_value"),("description","prm3_value"),("ifc_object_type","prm4_value"),("tag","prm7_value")]:
            val = cv(ff.get(slot))
            if val and not obj.get(key): obj[key] = val
    if not obj.get("name"):
        obj["name"] = cv(p.get("labelText")) or cv(obj.get("vw_name"))
    if not CFG.get("promote_user_fields", True): return
    uf = obj.setdefault("user_fields", {}); maxn = 5000; added = 0
    for k,v in (p.items() if isinstance(p,dict) else []):
        if added >= maxn: break
        uf[k] = v; added += 1
    for rec in recs:
        rn = rec.get("record",""); ff = rec.get("fields") or {}
        for k,v in (ff.items() if isinstance(ff,dict) else []):
            if added >= maxn: break
            if k: uf[f"{rn}::{k}"] = v; added += 1
def _pt_xy(p):
    if p is None:
        return None, None
    if isinstance(p, dict):
        x = p.get("x", p.get("X"))
        y = p.get("y", p.get("Y"))
        return x, y
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return p[0], p[1]
    return None, None
def _dist2(a, b):
    ax, ay = _pt_xy(a)
    bx, by = _pt_xy(b)
    if ax is None or ay is None or bx is None or by is None:
        return 0.0
    dx = float(ax) - float(bx)
    dy = float(ay) - float(by)
    return (dx*dx + dy*dy) ** 0.5
def _poly_area_perim(pts, closed):
    if not pts or len(pts) < 2:
        return None, None
    n = len(pts)
    per = 0.0
    for i in range(1, n):
        per += _dist2(pts[i-1], pts[i])
    if closed and n >= 3:
        per += _dist2(pts[-1], pts[0])
        area = 0.0
        for i in range(n):
            x1, y1 = _pt_xy(pts[i])
            x2, y2 = _pt_xy(pts[(i+1) % n])
            if x1 is None or y1 is None or x2 is None or y2 is None:
                continue
            area += float(x1) * float(y2) - float(x2) * float(y1)
        return abs(area) * 0.5, per
    return None, per
def obj_area(h):
    a=sf(sc(vs.ObjArea,h)) if hv("ObjArea") else None
    return a if a is not None else (sf(sc(vs.HArea,h)) if hv("HArea") else None)
def obj_perim(h):
    p=sf(sc(vs.ObjPerim,h)) if hv("ObjPerim") else None
    return p if p is not None else (sf(sc(vs.HPerim,h)) if hv("HPerim") else None)
def plan_quantities(h, t, pn, pts=None, closed=False):
    mA=mP=mL=None; area=obj_area(h); per=obj_perim(h)
    ln=sf(sc(vs.HLength,h)) if hv("HLength") else None
    if area is not None: mA="obj"
    if per is not None: mP="obj"
    if ln is not None: mL="hlen"
    if (area is None or per is None or ln is None) and t==86 and hv("GetCustomObjectPath"):
        ph=sc(vs.GetCustomObjectPath,h)
        if ph:
            if area is None: area=obj_area(ph); mA="pio_path" if area is not None else mA
            if per is None: per=obj_perim(ph); mP="pio_path" if per is not None else mP
            if ln is None and hv("HLength"):
                ln=sf(sc(vs.HLength,ph)); mL="pio_path" if ln is not None else mL
    if pts and isinstance(pts,list) and len(pts)>=2 and (area is None or per is None or ln is None):
        try: a2,p2=_poly_area_perim(pts, bool(closed))
        except: a2,p2=None,None
        if bool(closed):
            if area is None and a2 is not None: area=sf(a2); mA="pts"
            if per is None and p2 is not None: per=sf(p2); mP="pts"
        elif ln is None and p2 is not None: ln=sf(p2); mL="pts_len"
    if t==71 and pts and isinstance(pts,list) and len(pts)>=3:
        a2,p2=_poly_area_perim(pts,True)
        if a2 is not None: area=sf(a2); mA='pts'
        if p2 is not None: per=sf(p2); mP='pts'
    return area, per, ln, mA, mP, mL
def info3d(h):
    i=sc(vs.Get3DInfo,h)
    if not i: return {"raw":None,"dims":None,"vol":None}
    try:
        vals=[v for v in i if not isinstance(v,bool)] if isinstance(i,(list,tuple)) else []
        dims=[float(v) for v in vals[:3] if v is not None]
    except: return {"raw":str(i),"dims":None,"vol":None}
    if len(dims)<3: return {"raw":str(i),"dims":dims,"vol":None}
    ds=sorted(dims,reverse=True)
    v=ds[0]*ds[1]*ds[2] if all(d>0 for d in ds) else None
    return {"raw":list(dims),"dims":{"d1":ds[0],"d2":ds[1],"d3":ds[2]},"vol":v}
def wall_detail(h,t):
    if t not in CFG["wall_types"]: return None
    w={}
    w["height"]=sr(vs.GetObjectVariableReal,h,615)
    w["gross"]=sr(vs.GetObjectVariableReal,h,608)
    w["net"]=sr(vs.GetObjectVariableReal,h,611)
    w["var_612"]=sr(vs.GetObjectVariableReal,h,612)
    w["var_218"]=sr(vs.GetObjectVariableReal,h,218)
    w["h_above"]=sr(vs.GetObjectVariableReal,h,623)
    w["h_below"]=sr(vs.GetObjectVariableReal,h,624)
    w["length"] = (w["gross"]*1e6)/w["height"] if w.get("gross") and w.get("height") and w["height"]>0 else None
    w["thickness"] = None
    sent = CFG["sentinel"]

    # ── V2.7: Verified wall API calls ──

    # REAL = vs.HLength(h) → wall centreline length in mm
    if hv("HLength"):
        hl = sc(vs.HLength, h)
        if hl is not None:
            try:
                hl_f = float(hl)
                if hl_f > 0:
                    w["length_mm"] = hl_f
                    w["length_m"]  = hl_f / 1e3
            except: pass

    # (startHeightTop, startHeightBot, endHeightTop, endHeightBot) = vs.GetWallCornerHeights(theWall)
    if hv("GetWallCornerHeights"):
        ch = sc(vs.GetWallCornerHeights, h)
        if ch and isinstance(ch, (list,tuple)) and len(ch) >= 4:
            try:
                w["corner_heights"] = {
                    "start_top": float(ch[0]), "start_bot": float(ch[1]),
                    "end_top":   float(ch[2]), "end_bot":   float(ch[3]),
                }
                # Calculate start/end heights
                w["height_start_mm"] = float(ch[0]) - float(ch[1])
                w["height_end_mm"]   = float(ch[2]) - float(ch[3])
            except: pass

    # (overallHeightTop, overallHeightBottom) = vs.GetWallOverallHeights(theWall)
    if hv("GetWallOverallHeights"):
        oh = sc(vs.GetWallOverallHeights, h)
        if oh and isinstance(oh, (list,tuple)) and len(oh) >= 2:
            try:
                w["overall_top_mm"]    = float(oh[0])
                w["overall_bottom_mm"] = float(oh[1])
                w["overall_height_mm"] = float(oh[0]) - float(oh[1])
            except: pass

    # REAL = vs.WallWidth(wallHd) → total thickness in mm
    if hv("WallWidth"):
        ww = sc(vs.WallWidth, h)
        if ww is not None:
            try:
                ww_f = float(ww)
                if ww_f > 0: w["wall_width_mm"] = ww_f
            except: pass

    # (BOOLEAN, thicknessDist) = vs.GetWallThickness(h) → mm
    if hv("GetWallThickness"):
        gt = sc(vs.GetWallThickness, h)
        if gt and isinstance(gt, (list,tuple)) and len(gt) >= 2:
            try:
                if gt[0]: w["wall_thickness_mm"] = float(gt[1])
            except: pass

    # STRING = vs.GetWallStyle(theWall)
    if hv("GetWallStyle"):
        ws = sc(vs.GetWallStyle, h)
        if ws and isinstance(ws, str) and ws.strip():
            w["wall_style_api"] = ws.strip()

    # INTEGER = vs.GetCoreWallComponent(object) → which component is structural
    if hv("GetCoreWallComponent"):
        cc = sc(vs.GetCoreWallComponent, h)
        if cc is not None:
            try: w["core_component_idx"] = int(cc)
            except: pass

    # INTEGER = vs.GetNumWallPeaks(h)
    if hv("GetNumWallPeaks"):
        np = sc(vs.GetNumWallPeaks, h)
        if np is not None:
            try: w["n_peaks"] = int(np)
            except: pass

    # (BOOLEAN, numWallBreaks) = vs.GetNumOfWallBreaks(wallH)
    if hv("GetNumOfWallBreaks"):
        nb = sc(vs.GetNumOfWallBreaks, h)
        if nb and isinstance(nb, (list,tuple)) and len(nb) >= 2:
            try:
                if nb[0]: w["n_breaks"] = int(nb[1])
            except: pass

    # Openings deduction (gross - net)
    if w.get("gross") and w.get("net"):
        w["openings"] = w["gross"] - w["net"]
        w["openings_m2"] = w["openings"]

    # ── Legacy fields retained ──
    if hv("GetObjectVariablePoint"):
        for var,key in [(60,"start"),(61,"end")]:
            pt=unpack_pt(sc(vs.GetObjectVariablePoint,h,var))
            if pt and len(pt)>=2:
                px,py=float(pt[0]),float(pt[1])
                if abs(px)<sent and abs(py)<sent: w[key]={"x":px,"y":py}
    if w.get("start") and w.get("end"):
        w["length_pts"]=math.hypot(w["end"]["x"]-w["start"]["x"],w["end"]["y"]-w["start"]["y"])
    if hv("GetObjectVariableString"):
        raw=sc(vs.GetObjectVariableString,h,695)
        w["style"]=next((v for v in raw if isinstance(v,str)),None) if isinstance(raw,(list,tuple)) else raw
    if hv("GetObjectVariableInt"):
        def ui(fn,*a):
            raw=sc(fn,*a)
            if isinstance(raw,(list,tuple)):
                for v in raw:
                    if isinstance(v,int) and not isinstance(v,bool): return v
                return None
            return raw
        w["n_comp"]=ui(vs.GetObjectVariableInt,h,622)
        w["cap_l"]=ui(vs.GetObjectVariableInt,h,620)
        w["cap_r"]=ui(vs.GetObjectVariableInt,h,621)
    return w
def pio_dims(pn,pp):
    if not pn or not pp: return None
    d={"pio_type":pn}
    if pn=="FramingMember":
        d["width"]=sf(pp.get("width")); d["height"]=sf(pp.get("height"))
        d["line_len"]=sf(pp.get("LineLength")); d["line_len_real"]=sf(pp.get("LineLengthReal"))
        d["vol_pio"]=sf(pp.get("volume")); d["use"]=pp.get("structuralUse")
        d["member_type"]=pp.get("type"); d["material"]=pp.get("Material")
    elif pn=="Door":
        d["dw"]=sf(pp.get("DoorWidth")); d["dh"]=sf(pp.get("DoorHeight"))
        d["dt"]=sf(pp.get("DoorThickness")); d["config"]=pp.get("Config")
        d["id"]=(pp.get("IDPrefix","") or "")+(pp.get("IDLabel","") or "")
    elif pn=="WinDoor 6.0":
        d["w"]=sf(pp.get("Width")) or sf(pp.get("DoorWidth"))
        d["h"]=sf(pp.get("Height")) or sf(pp.get("DoorHeight"))
    elif pn=="Drilled Footing":
        d["dia"]=sf(pp.get("Diameter"))
        td,bd=sfz(pp.get("Top datum")),sfz(pp.get("Bearing datum"))
        if td is not None and bd is not None: d["depth"]=abs(td-bd)
        d["bell_w"]=sf(pp.get("Bell width")); d["bell_h"]=sf(pp.get("Bell height"))
    elif pn=="Slab":
        d["h_offset"]=sf(pp.get("Height")); d["style"]=pp.get("Style")
    elif pn=="Column2":
        d["shaft_w"]=sf(pp.get("Shaft Width")); d["shaft_d"]=sf(pp.get("Shaft Depth"))
        d["dia"]=sf(pp.get("Diameter")); d["height"]=sf(pp.get("OA Height")) or sf(pp.get("NewHeight"))
        d["struct_type"]=pp.get("Struct Type"); d["shaft_type"]=pp.get("Shaft Type")
        d["struct_w"]=sf(pp.get("Struct Width")); d["struct_d"]=sf(pp.get("Struct Depth"))
    else:
        for k in ("Width","width","Height","height","Length","length","Depth","depth","Thickness","thickness","Diameter","LineLength"):
            v=sf(pp.get(k))
            if v: d[k.lower()]=v
    return {k:v for k,v in d.items() if v is not None}
def eap_path_length(h):
    try:
        ph = sc(vs.GetCustomObjectPath, h)
        if ph:
            ln = sc(vs.HLength, ph)
            if ln and ln > 0:
                return float(ln)
    except:
        pass
    return None
def calc_uvw(t,pn,wd,pd,dims3d,bb2d,raw3d=None):
    u={"u":None,"v":None,"w":None,"m":None}
    if t in CFG["wall_types"] and wd:
        # V2.7: prefer HLength (verified mm) over calculated length
        wall_len = wd.get("length_m") or (wd.get("length_mm",0)/1e3 if wd.get("length_mm") else None) or wd.get("length")
        wall_h   = wd.get("overall_height_mm") or wd.get("height")
        wall_t   = wd.get("wall_width_mm") or wd.get("wall_thickness_mm") or wd.get("thickness")
        u["u"],u["v"],u["w"],u["m"]=wall_len,wall_h,wall_t,"wall_api"
        if wd.get("length_mm"): u["l"]=wd["length_mm"]; u["m_l"]="wall_hlength"
        return u
    if pd:
        pt=pd.get("pio_type")
        if pt=="FramingMember":
            u["u"]=pd.get("line_len") or pd.get("line_len_real"); u["v"]=pd.get("height"); u["w"]=pd.get("width"); u["m"]="pio_frame"
            return u
        if pt=="Door":
            u["u"],u["v"],u["w"],u["m"]=pd.get("dw"),pd.get("dh"),pd.get("dt"),"pio_door"
            return u
        if pt=="Drilled Footing":
            u["u"],u["v"],u["w"],u["m"]=pd.get("dia"),pd.get("dia"),pd.get("depth"),"pio_foot"
            return u
        if pt=="Column2":
            sw=pd.get("shaft_w") or pd.get("dia"); sd=pd.get("shaft_d") or sw
            u["u"],u["v"],u["w"],u["m"]=sw,sd,pd.get("height"),"pio_col"
            return u
    # ── Generic 3D bbox: Z=height, max(X,Y)=length, min(X,Y)=width ──
    if raw3d and len(raw3d)==3:
        try:
            rx,ry,rz=[abs(float(v)) for v in raw3d]
            if rx>0 or ry>0 or rz>0:
                u["u"],u["v"],u["w"],u["m"]=max(rx,ry),rz,min(rx,ry),"bbox3d"
                return u
        except: pass
    # Fallback: sorted dims (legacy, no axis info)
    if dims3d:
        d1,d2,d3=dims3d.get("d1"),dims3d.get("d2"),dims3d.get("d3")
        if d1 and d2 and d3:
            u["u"],u["v"],u["w"],u["m"]=d1,d2,d3,"bbox3d_sorted"
            return u
    if bb2d:
        bw,bh=bb2d.get("width"),bb2d.get("height")
        if bw and bh:
            u["u"],u["v"],u["w"],u["m"]=max(bw,bh),min(bw,bh),None,"bbox2d"
    return u
def qa_flags(obj,wd,uvw,areas):
    fl=[]
    if wd:
        dl = wd.get("length")
        dims = (areas or {}).get("dims_3d") or {}
        d1, d2 = dims.get("d1"), dims.get("d2")
        if dl and d1:
            best = d1 if abs(dl-d1) < abs(dl-(d2 or 0)) else d2
            if best and best > 0:
                r = dl / best
                if r < 0.85 or r > 1.15:
                    fl.append(f"wall_len:{dl:.0f} vs bbox:{best:.0f} r={r:.2f}")
        ct = wd.get("thickness",0) or 0
        d3 = dims.get("d3",0) or 0
        if ct > 0 and d3 > 0 and abs(ct - d3) > 10:
            fl.append(f"wall_thick:comp={ct:.0f} vs d3={d3:.0f}")
    if uvw.get("u") and uvw.get("v") and uvw.get("w"):
        uv=uvw["u"]*uvw["v"]*uvw["w"]
        bv=(areas or {}).get("vol_bbox")
        if bv and bv>0:
            r=uv/bv
            if r<0.8 or r>1.2: fl.append(f"uvw_vol:{uv:.0f} vs bbox:{bv:.0f} r={r:.2f}")
    return fl or None
def is_sent(x,y):
    try: return abs(float(x))>=CFG["sentinel"] or abs(float(y))>=CFG["sentinel"]
    except: return True
def dst(a,b): return math.hypot(a["x"]-b["x"],a["y"]-b["y"])
def poly_area(pts):
    if not pts or len(pts)<3: return 0.0
    a2,n=0.0,len(pts)
    for i in range(n):
        x1,y1=pts[i]["x"],pts[i]["y"]
        x2,y2=pts[(i+1)%n]["x"],pts[(i+1)%n]["y"]
        a2+=x1*y2-x2*y1
    return abs(a2)*0.5
def poly_per(pts,cl=True):
    if not pts or len(pts)<2: return 0.0
    p=sum(dst(pts[i],pts[i+1]) for i in range(len(pts)-1))
    if cl: p+=dst(pts[-1],pts[0])
    return p
def get_pts(h):
    for api in [("GetPolylineVertex",2),("GetPolyPt",2)]:
        fn=api[0]
        if not (hv("GetVertNum") and hv(fn)): continue
        n=sc(vs.GetVertNum,h)
        if not n or n<=0: continue
        gf=getattr(vs,fn)
        pts,ok=[],True
        for i in range(1,n+1):
            v=sc(gf,h,i)
            if not v or len(v)<2: ok=False; break
            x,y=v[0],v[1]
            if is_sent(x,y): ok=False; break
            pts.append({"x":float(x),"y":float(y)})
        if ok and len(pts)>=2:
            cl=(dst(pts[0],pts[-1])<1e-9)
            if cl and len(pts)>=3: pts=pts[:-1]
            return pts,fn,cl
    return None,None,None
ST={"t0":time.time(),"seen":0,"exp":0,"err":0,"jfp":None,"dfp":None,"dbg":[],"records":[]}
def dbg(m):
    if ST["dfp"]: ST["dfp"].write(m+"\n")
def emit(o):
    ST["jfp"].write(json.dumps(o,ensure_ascii=False)+"\n")
    if ST["exp"]%200==0: ST["jfp"].flush()
def obj_material(h):
    try:
        nm = None
        if hv("GetObjMaterialName"):
            raw = sc(vs.GetObjMaterialName, h)
            if isinstance(raw,(list,tuple)):
                nm = next((v for v in raw if isinstance(v,str) and v.strip()), None)
            elif isinstance(raw,str):
                nm = raw
            nm = cv(nm)
        mh = sc(vs.GetObjMaterialHandle, h) if hv("GetObjMaterialHandle") else None
        if isinstance(mh,(list,tuple)):
            mh = next((v for v in mh if not isinstance(v,bool)), None)
        if not nm and mh:
            nm = resolve_material(mh)
            if nm == mh: nm = None
        mid = None
        if nm:
            ri = sc(vs.Name2Index, nm)
            if isinstance(ri,(list,tuple)):
                mid = next((v for v in ri if isinstance(v,int) and not isinstance(v,bool)), None)
            elif isinstance(ri, int):
                mid = ri
        if nm or mid:
            r = {"name": nm}
            if mid is not None: r["idx"] = mid
            return r
    except: pass
    return None
def get_components_raw(h, t):
    if not hv("GetNumberOfComponents"):
        return None
    res = sc(vs.GetNumberOfComponents, h)
    ok = True
    n = 0
    if isinstance(res, tuple):
        if len(res) >= 2:
            ok = bool(res[0])
            n = res[1]
        elif len(res) == 1:
            n = res[0]
    else:
        n = res
    try:
        n = int(n or 0)
    except:
        n = 0
    if (not ok) or n <= 0:
        return None
    def _unwrap_ok_val(r):
        if isinstance(r, tuple):
            if len(r) >= 2:
                return bool(r[0]), r[1]
            if len(r) == 1:
                return True, r[0]
            return False, None
        return True, r
    comps = []
    for i in range(1, n + 1):
        c = {"i": i}
        def gc(api, key, transform=cv):
            if not hv(api): return
            ok2, v = _unwrap_ok_val(sc(getattr(vs, api), h, i))
            if ok2 and v is not None: c[key] = transform(v)
        gc("GetComponentName", "name")
        gc("GetComponentWidth", "thickness", sf)
        gc("GetComponentFunction", "function")
        gc("GetComponentTexture", "texture", _json_sanitize)
        if hv("GetComponentClass"):
            ok2, v = _unwrap_ok_val(sc(vs.GetComponentClass, h, i))
            if ok2:
                raw_cls = cv(v)
                c["class"] = resolve_class(raw_cls)
                if raw_cls != c["class"]: c["class_idx"] = raw_cls
        if hv("GetComponentMaterial"):
            ok2, v = _unwrap_ok_val(sc(vs.GetComponentMaterial, h, i))
            if ok2 and v is not None:
                raw_mat=_json_sanitize(v); resolved=resolve_material(raw_mat)
                if resolved==raw_mat and isinstance(raw_mat,int) and raw_mat>0:
                    for a in ["Index2Name","GetMaterialName"]:
                        if not hv(a): continue
                        nm=sc(getattr(vs,a),raw_mat)
                        if isinstance(nm,(list,tuple)): nm=next((x for x in nm if isinstance(x,str) and x.strip()),None)
                        if nm and isinstance(nm,str) and nm.strip(): resolved=nm.strip(); break
                c["material"]=resolved
                if raw_mat!=resolved: c["material_idx"]=raw_mat
        if t == 68:
            gc("GetComponentWallTopOffset", "top_offset", lambda v: sfz(v, default=0.0))
            gc("GetComponentWallBottomOffset", "bottom_offset", lambda v: sfz(v, default=0.0))
            gc("GetComponentFollowTopWallPeaks", "follow_top_peaks", bool)
            gc("GetComponentFollowBottomWallPeaks", "follow_bottom_peaks", bool)

        # ── V2.7: Per-component QUANTITIES (verified API calls) ──
        # Only on types with 3D components: walls(68), slabs(71), roofs(84)
        if t in (68, 71, 84):
            # REAL = vs.GetComponentNetArea(object, componentIndex) → mm²
            if hv("GetComponentNetArea"):
                na_mm2 = sc(vs.GetComponentNetArea, h, i)
                if na_mm2 is not None:
                    try:
                        na = float(na_mm2)
                        if na > 0:
                            c["net_area_mm2"] = na
                            c["net_area_m2"]  = na / 1e6
                    except: pass

            # REAL = vs.GetComponentNetVolume(object, componentIndex) → mm³
            if hv("GetComponentNetVolume"):
                nv_mm3 = sc(vs.GetComponentNetVolume, h, i)
                if nv_mm3 is not None:
                    try:
                        nv = float(nv_mm3)
                        if nv > 0:
                            c["net_volume_mm3"] = nv
                            c["net_volume_m3"]  = nv / 1e9
                    except: pass

        # ── V2.7: Per-component start/end points (walls only) ──
        # Gives per-component LENGTH from centre-line distance
        if t == 68:
            # (leftPoint, centerPoint, rightPoint) = vs.GetWallCompStartPts(wall, componentIndex)
            if hv("GetWallCompStartPts") and hv("GetWallCompEndPts"):
                sp = sc(vs.GetWallCompStartPts, h, i)
                ep = sc(vs.GetWallCompEndPts, h, i)
                if sp and ep and isinstance(sp, (list,tuple)) and isinstance(ep, (list,tuple)):
                    try:
                        # Centre points are at index [1]
                        sx, sy = float(sp[1][0]), float(sp[1][1])
                        ex, ey = float(ep[1][0]), float(ep[1][1])
                        comp_len = math.hypot(ex - sx, ey - sy)
                        if comp_len > 0:
                            c["length_mm"] = comp_len
                            c["length_m"]  = comp_len / 1e3
                    except: pass

            # Back-calculate effective height from area/length
            if c.get("net_area_mm2") and c.get("length_mm") and c["length_mm"] > 0:
                c["eff_height_mm"] = c["net_area_mm2"] / c["length_mm"]

        comps.append(c)
    return comps
def harvest(h):
    ST["seen"] += 1
    if not h:
        return
    t = sc(vs.GetTypeN, h)
    o = {"type":t,"vw_name":sc(vs.GetName,h),"class":sc(vs.GetClass,h),"layer":layer_name(h)}
    mat=obj_material(h)
    if mat is not None: o["material"]=mat
    try:
        if CFG["limit_objects"] and ST["exp"] >= CFG["limit_objects"]:
            return
        uid, us = ensure_uuid(h)
        o["iqs_uuid"] = uid
        o["uuid_src"] = us
        o["origin"] = get_origin(h)
        o["bbox"] = get_bbox(h)
        pts, src_kind, closed = get_pts(h)
        if pts and len(pts) >= 2:
            o["geom_2d"] = {"pts": pts, "src": src_kind, "closed": closed}
        area2d, per2d, len2d, mA, mP, mL = plan_quantities(h, t, o.get("pio"), pts, closed)
        i3 = info3d(h)
        ar = {"area_2d":area2d,"perim_2d":per2d,"len_2d":len2d,"m_area_2d":mA,"m_perim_2d":mP,"m_len_2d":mL,"dims_3d":i3["dims"],"vol_bbox":i3["vol"],"raw_3d":i3["raw"]}
        o["areas"] = ar
        o["records"] = get_recs(h)
        pd = get_pio(h)
        if pd:
            o["pio"] = pd["pio"]
            o["pio_params"] = pd["fields"]
        if o.get("pio") == "Extrude Along Path":
            pl = eap_path_length(h)
            if pl is not None:
                o.setdefault("eap",{})["path_length"]=pl; o.setdefault("areas",{})["len_path"]=pl
        wd = wall_detail(h, t)
        if wd:
            o["wall"] = wd
        comps = get_components_raw(h, t)
        if comps:
            o["components"] = comps
            classes_used = []
            if o.get("class"):
                classes_used.append(o["class"])
            for cc in comps:
                ccls = cc.get("class")
                if ccls and ccls not in classes_used:
                    classes_used.append(ccls)
            if classes_used:
                o["classes_used"] = classes_used
        if pd:
            pdm = pio_dims(pd["pio"], pd["fields"])
            if pdm:
                o["pio_dims"] = pdm
        if t in CFG["wall_types"] and o.get("wall"):
            comp_thick = sum(c.get("thickness",0) for c in (o.get("components") or []))
            d3 = ((o.get("areas") or {}).get("dims_3d") or {}).get("d3")
            # V2.7: prefer verified WallWidth API
            api_thick = o["wall"].get("wall_width_mm") or o["wall"].get("wall_thickness_mm")
            if api_thick and api_thick > 0:
                o["wall"]["thickness"] = api_thick
                o["wall"]["thickness_src"] = "wall_api"
            elif comp_thick > 0:
                o["wall"]["thickness"] = comp_thick
                o["wall"]["thickness_src"] = "comp_sum"
            elif d3 and d3 > 0:
                o["wall"]["thickness"] = d3
                o["wall"]["thickness_src"] = "bbox_d3"
        dims3d = (o.get("areas") or {}).get("dims_3d")
        raw3d  = (o.get("areas") or {}).get("raw_3d")
        bb2d = o.get("bbox")
        pn = o.get("pio")
        wd = o.get("wall")
        pdm = o.get("pio_dims")
        o["uvw"] = calc_uvw(t, pn, wd, pdm, dims3d, bb2d, raw3d)
        if o.get("pio") == "Extrude Along Path":
            pl = (o.get("areas") or {}).get("len_path") or eap_path_length(h)
            if pl is not None:
                o.setdefault("areas",{})["len_path"]=pl; o.setdefault("eap",{})["path_length"]=pl
                # calc_uvw already set v=Z(height), w=min(X,Y)(width) from raw3d
                # Just override u with actual path length (may differ from bbox for curved paths)
                o["uvw"]["u"] = pl; o["uvw"]["l"] = pl; o["uvw"]["m_l"] = "eap_path"
        probe_common(h, o)
        promote(o)
    except Exception as e:
        ST["err"] += 1
        o["export_error"] = repr(e)
        dbg(f"ERR {ST['seen']}: {repr(e)}")
    try:
        _san = _json_sanitize(o)
        ST["jfp"].write(json.dumps(_san) + "\n")
        ST["records"].append(_san)
        ST["exp"] += 1
        if ST["exp"] % 200 == 0:
            ST["jfp"].flush()
        if len(ST["dbg"]) < CFG["debug_first_n"]:
            uvw = o.get("uvw") or {}
            fl = o.get("flags") or None
            ST["dbg"].append(f"#{ST['exp']}: t={t} {o.get('class','')} U={uvw.get('u')} V={uvw.get('v')} W={uvw.get('w')} m={uvw.get('m')} fl={fl}")
        if ST["exp"] % CFG["status_every_n"] == 0:
            vs.Message(f"Exported {ST['exp']} (seen {ST['seen']})...")
    except Exception as e2:
        ST["err"] += 1
        dbg(f"WRITE_ERR {ST['seen']}: {repr(e2)}")
def build_criteria():
    scp = CFG.get("scope", "ALL")
    if scp == "SEL":
        return "SEL=TRUE"
    if scp == "ACTIVE_LAYER":
        try:
            lyr = sc(vs.ActLayer)
            lname = sc(vs.GetName, lyr) if lyr else None
            if lname:
                return f"(L='{lname}')"
        except:
            pass
        return "INVIEWPORT" if False else "ALL"
    return "ALL"
def _json_sanitize(v, _d=0):
    if _d > 6:
        try: return str(v)
        except: return None
    if v is None or isinstance(v, (bool, int, float, str)): return v
    if isinstance(v, (tuple, list)): return [_json_sanitize(x, _d+1) for x in v]
    if isinstance(v, dict): return {str(k): _json_sanitize(val, _d+1) for k,val in v.items()}
    try:
        if "Handle" in type(v).__name__: return int(v)
    except: pass
    try: return float(v)
    except: pass
    try: return str(v)
    except: return None
def probe_common(h, o):
    mode = (CFG.get("probe_mode") or "off").lower()
    if mode == "off": return
    probe,errs = {},{}
    def put(k,fn,*a):
        try: probe[k]=_json_sanitize(sc(fn,*a))
        except Exception as e:
            if CFG.get("probe_store_errors",True): errs[k]=repr(e)
    if hv("GetName"): put("GetName",vs.GetName,h)
    if hv("GetTypeN"): put("GetTypeN",vs.GetTypeN,h)
    if hv("GetClass"): put("GetClass",vs.GetClass,h)
    if hv("GetLayer"):
        try:
            lyr=sc(vs.GetLayer,h); probe["GetLayer_h"]=_json_sanitize(lyr)
            if lyr and hv("GetName"): probe["GetLayer_name"]=sc(vs.GetName,lyr)
        except Exception as e:
            if CFG.get("probe_store_errors",True): errs["GetLayer"]=repr(e)
    for k,fn in [("GetBBox","GetBBox"),("Get3DInfo","Get3DInfo"),("HArea","HArea"),("HLength","HLength"),("GetCustomObjectInfo","GetCustomObjectInfo"),("GetCustomObjectPath","GetCustomObjectPath")]:
        if hv(fn): put(k,getattr(vs,fn),h)
    o["probe"]=probe
    if errs: o["probe_errors"]=errs
def iqs_push(jsonl_path):
    """POST export to iQs Rails. Falls back gracefully if Rails isn't running."""
    url = CFG.get("iqs_url","").strip()
    if not url:
        dbg("iqs_push: no url configured, skipping"); return None
    # Derive project name from VW filename
    project = "Unknown"
    try:
        fp = sc(vs.GetFPathName, default="")
        if fp: project = os.path.splitext(os.path.basename(fp))[0]
    except: pass
    payload = json.dumps({
        "vw_import": {
            "project": project, "exporter_version": "2.7",
            "exported_at": datetime.now().isoformat(),
            "object_count": ST["exp"], "jsonl_path": jsonl_path,
            "objects": ST["records"],
        }
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type":"application/json", "X-IQS-Exporter":"2.7"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode("utf-8"))
        iid = result.get("id","?")
        dbg(f"iqs_push: OK → import #{iid} ({ST['exp']} objects)")
        return iid
    except urllib.error.URLError as e:
        dbg(f"iqs_push: FAILED — {repr(e)} (is Rails running?)"); return None
    except Exception as e:
        dbg(f"iqs_push: ERROR — {repr(e)}"); return None

def run():
    d=resolve_dir(); jp,dp=mk_paths(d)
    ST["jfp"]=open(jp,"w",encoding="utf-8"); ST["dfp"]=open(dp,"w",encoding="utf-8")
    build_class_lookup()
    dbg(f"Class lookup: {len(CLASS_LUT)//2} classes mapped")
    build_material_lookup()
    dbg(f"Material lookup: {len(MAT_LUT)//4} materials mapped (idx+offset)")
    try:
        cfp, cn = export_class_list(d)
        dbg(f"Class list: {cn} classes → {cfp}")
    except Exception as e:
        dbg(f"Class list export failed: {repr(e)}")
        cfp = None
    try:
        mfp, mn = export_material_list(d)
        dbg(f"Material list: {mn} materials → {mfp}")
    except Exception as e:
        dbg(f"Material list export failed: {repr(e)}")
        mfp = None
    ensure_record_format(CFG["uuid_rec"], CFG["uuid_fld"])
    c = build_criteria()
    dbg("=== iQs VW Exporter V2.7 ==="); dbg(f"Criteria: {c}"); dbg(f"Export dir: {d}")
    vs.Message(f"Starting export ({c})...")
    vs.ForEachObject(harvest,c)
    ST["jfp"].close()
    dbg("\n=== SUMMARY ==="); dbg(f"Seen:{ST['seen']} Exp:{ST['exp']} Err:{ST['err']}")
    for ln in ST["dbg"]: dbg("  "+ln)
    # ── Push to iQs ──
    iid = iqs_push(jp)
    ST["dfp"].close()
    el=time.time()-ST["t0"]
    msg=f"Done.\nSeen:{ST['seen']}\nExported:{ST['exp']}\nErrors:{ST['err']}\nSec:{el:.2f}\nJSONL:{jp}\nDEBUG:{dp}"
    if cfp: msg+=f"\nCLASSES:{cfp}"
    if mfp: msg+=f"\nMATERIALS:{mfp}"
    if iid: msg+=f"\n\n✓ iQs: import #{iid}\n  → http://localhost:3000/vw_imports/{iid}"
    else: msg+=f"\n\niQs: offline (JSONL saved locally)"
    vs.AlrtDialog(msg)
run()