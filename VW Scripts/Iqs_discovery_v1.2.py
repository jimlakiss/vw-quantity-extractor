# iQs API Discovery Script V1.2
# ═══════════════════════════════════════════════════════════════════
# Every function signature verified against VW_Superfile Excel.
#
# KEY LEARNINGS from V1.0/1.1 failures:
#   ComponentArea(c, index)   → c = CRITERIA string, NOT handle
#   ComponentVolume(c, index) → c = CRITERIA string, NOT handle
#   WallArea_Gross(c)         → c = CRITERIA string, NOT handle
#   WallArea_Net(c)           → c = CRITERIA string, NOT handle
#   WallAverageHeight(c)      → c = CRITERIA string, NOT handle
#   ObjVolume(solidObject)    → SOLID objects only (type 95, 516-522)
#   ObjSurfaceArea(solid)     → SOLID objects only
#   Centroid3D(object)        → 3D objects only, returns (BOOL,x,y,z)
#   GetCustomObjectInfo()     → NO parameters (self-reference for PIOs)
#   HAreaN(handle)            → 2D objects only
#
# HANDLE-BASED component quantity calls (what we actually want):
#   GetComponentArea(object, componentIndex)       → REAL
#   GetComponentNetArea(object, componentIndex)     → REAL
#   GetComponentVolume(object, componentIndex)      → REAL (no doc)
#   GetComponentNetVolume(object, componentIndex)   → REAL
#
# Output: discovery_results_YYYYMMDD_HHMMSS.json
# Read-only. No object modification.
# ═══════════════════════════════════════════════════════════════════

import vs, json, os
from datetime import datetime

EXPORT_DIR = "/Users/jameslakiss/Documents/Develop/iQs/10 VW Integration/JSONL_Exports"
MAX_PER_TYPE = 3

# Solid types — safe for ObjVolume, ObjSurfaceArea
SOLID_TYPES = {95, 516, 517, 518, 519, 520, 521, 522}

def sc(fn, *a, default=None):
    try:
        return fn(*a)
    except:
        return default

hv = lambda a: hasattr(vs, a)

def raw(val):
    if val is None: return None
    if isinstance(val, bool): return val
    if isinstance(val, (int, float)): return val
    if isinstance(val, str): return val
    if isinstance(val, (list, tuple)):
        return [raw(v) for v in val]
    try:
        if "Handle" in type(val).__name__:
            return "__HANDLE__"
    except: pass
    try: return float(val)
    except: pass
    try: return str(val)
    except: return repr(val)


def get_comp_count(h):
    # Signature: (BOOLEAN, numComponents) = vs.GetNumberOfComponents(object)
    res = sc(vs.GetNumberOfComponents, h)
    if isinstance(res, tuple) and len(res) >= 2:
        return int(res[1] or 0)
    elif isinstance(res, (int, float)):
        return int(res or 0)
    return 0


# ══════════════════════════════════════════════════════════════════
# SECTION 1: 2D DIMENSION CALLS
# All take (h) handle. Safe on any object.
# ══════════════════════════════════════════════════════════════════

def discover_2d(h):
    d = {}
    # REAL = vs.HLength(h)
    d["HLength"] = raw(sc(vs.HLength, h))
    # REAL = vs.HHeight(h) — "2D height"
    d["HHeight"] = raw(sc(vs.HHeight, h))
    # REAL = vs.HWidth(h) — "2D width"
    d["HWidth"]  = raw(sc(vs.HWidth, h))
    # REAL = vs.HPerim(h)
    d["HPerim"]  = raw(sc(vs.HPerim, h))
    # REAL = vs.HArea(h) — "obsolete, use ObjArea"
    d["HArea"]   = raw(sc(vs.HArea, h))
    # REAL = vs.ObjArea(h) — "current Area Units"
    d["ObjArea"] = raw(sc(vs.ObjArea, h))
    # (p1, p2) = vs.GetBBox(h)
    d["GetBBox"] = raw(sc(vs.GetBBox, h))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 2: 3D DIMENSION CALLS
# Get3DInfo takes any handle but may return zeros for 2D.
# ObjVolume/ObjSurfaceArea only for SOLID types.
# ══════════════════════════════════════════════════════════════════

def discover_3d(h, t):
    d = {}
    # (height, width, depth) = vs.Get3DInfo(h) — any object
    d["Get3DInfo"] = raw(sc(vs.Get3DInfo, h))

    # (p, zValue) = vs.Get3DCntr(h) — any object
    d["Get3DCntr"] = raw(sc(vs.Get3DCntr, h))

    # SOLID ONLY: REAL = vs.ObjVolume(solidObject)
    if t in SOLID_TYPES:
        d["ObjVolume"]           = raw(sc(vs.ObjVolume, h))
        d["ObjSurfaceArea"]      = raw(sc(vs.ObjSurfaceArea, h))
        d["ObjSurfAreaInWorldC"] = raw(sc(vs.ObjSurfAreaInWorldC, h))

    # (BOOLEAN, xCG, yCG, zCG) = vs.Centroid3D(object) — 3D only
    # Only safe on types we KNOW are 3D
    if t in (24, 68, 71, 84, 86, 89) or t in SOLID_TYPES:
        d["Centroid3D"] = raw(sc(vs.Centroid3D, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 3: PER-COMPONENT QUANTITIES (handle-based)
# These take (object, componentIndex) — handle, not criteria.
# Only call on types known to have 3D components: 68, 71, 84
# ══════════════════════════════════════════════════════════════════

def discover_comp_quantities(h, t):
    n = get_comp_count(h)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}

        # Identity (for context)
        # STRING = vs.GetComponentName(object, componentIndex)
        c["GetComponentName"]  = raw(sc(vs.GetComponentName, h, i))
        # (BOOLEAN, width) = vs.GetComponentWidth(object, componentIndex)
        c["GetComponentWidth"] = raw(sc(vs.GetComponentWidth, h, i))

        # ── HANDLE-BASED quantity calls ──

        # REAL = vs.GetComponentArea(object, componentIndex)
        # (no doc snippet but exists in API, status OK)
        c["GetComponentArea"]      = raw(sc(vs.GetComponentArea, h, i))

        # REAL = vs.GetComponentNetArea(object, componentIndex)
        c["GetComponentNetArea"]   = raw(sc(vs.GetComponentNetArea, h, i))

        # REAL = vs.GetComponentVolume(object, componentIndex)
        # (no doc snippet but exists in API, status OK)
        c["GetComponentVolume"]    = raw(sc(vs.GetComponentVolume, h, i))

        # REAL = vs.GetComponentNetVolume(object, componentIndex)
        c["GetComponentNetVolume"] = raw(sc(vs.GetComponentNetVolume, h, i))

        d["components"].append(c)

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 4: COMPONENT IDENTITY (all types with components)
# ══════════════════════════════════════════════════════════════════

def discover_comp_identity(h, t):
    n = get_comp_count(h)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}

        # STRING = vs.GetComponentName(object, componentIndex)
        c["GetComponentName"]     = raw(sc(vs.GetComponentName, h, i))
        # (BOOLEAN, componentClass) = vs.GetComponentClass(object, componentIndex)
        c["GetComponentClass"]    = raw(sc(vs.GetComponentClass, h, i))
        # (BOOLEAN, width) = vs.GetComponentWidth(object, componentIndex)
        c["GetComponentWidth"]    = raw(sc(vs.GetComponentWidth, h, i))
        # (BOOLEAN, func) = vs.GetComponentFunction(object, componentIndex)
        c["GetComponentFunction"] = raw(sc(vs.GetComponentFunction, h, i))
        # (BOOLEAN, material) = vs.GetComponentMaterial(object, componentIndex)
        c["GetComponentMaterial"] = raw(sc(vs.GetComponentMaterial, h, i))
        # (BOOLEAN, texture) = vs.GetComponentTexture(object, componentIndex)
        c["GetComponentTexture"]  = raw(sc(vs.GetComponentTexture, h, i))

        d["components"].append(c)

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 5: WALL-SPECIFIC COMPONENT DETAIL (type 68 only)
# ══════════════════════════════════════════════════════════════════

def discover_wall_comp_detail(h):
    n = get_comp_count(h)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}
        c["name"] = raw(sc(vs.GetComponentName, h, i))

        # (BOOLEAN, offsetFromWallTop) = vs.GetComponentWallTopOffset(object, componentIndex)
        c["GetComponentWallTopOffset"]    = raw(sc(vs.GetComponentWallTopOffset, h, i))
        # (BOOLEAN, offsetFromWallBottom) = vs.GetComponentWallBottomOffset(object, componentIndex)
        c["GetComponentWallBottomOffset"] = raw(sc(vs.GetComponentWallBottomOffset, h, i))

        # (BOOLEAN, followTopWallPeaks) = vs.GetComponentFollowTopWallPeaks(object, componentIndex)
        c["GetComponentFollowTopWallPeaks"]    = raw(sc(vs.GetComponentFollowTopWallPeaks, h, i))
        # (BOOLEAN, followBottomWallPeaks) = vs.GetComponentFollowBottomWallPeaks(object, componentIndex)
        c["GetComponentFollowBottomWallPeaks"] = raw(sc(vs.GetComponentFollowBottomWallPeaks, h, i))

        # (leftPoint, centerPoint, rightPoint) = vs.GetWallCompStartPts(wall, componentIndex)
        c["GetWallCompStartPts"] = raw(sc(vs.GetWallCompStartPts, h, i))
        # (leftPoint, centerPoint, rightPoint) = vs.GetWallCompEndPts(wall, componentIndex)
        c["GetWallCompEndPts"]   = raw(sc(vs.GetWallCompEndPts, h, i))

        # (BOOLEAN, boundOffset) = vs.GetCompBoundOffset(object, componentIndex)
        c["GetCompBoundOffset"]              = raw(sc(vs.GetCompBoundOffset, h, i))
        # (BOOLEAN, wallAssociatedBound) = vs.GetCompWallAssBound(object, componentIndex)
        c["GetCompWallAssBound"]             = raw(sc(vs.GetCompWallAssBound, h, i))
        # (BOOLEAN, wallAssociatedModification) = vs.GetCompWallAssMod(object, componentIndex)
        c["GetCompWallAssMod"]               = raw(sc(vs.GetCompWallAssMod, h, i))
        # (BOOLEAN, autoBoundEdgeOffset) = vs.GetComponentAutoBoundEdgeOffset(object, componentIndex)
        c["GetComponentAutoBoundEdgeOffset"] = raw(sc(vs.GetComponentAutoBoundEdgeOffset, h, i))
        # (BOOLEAN, manualEdgeOffset) = vs.GetComponentManualEdgeOffset(object, componentIndex)
        c["GetComponentManualEdgeOffset"]    = raw(sc(vs.GetComponentManualEdgeOffset, h, i))

        d["components"].append(c)

    # INTEGER = vs.GetCoreWallComponent(object)
    d["GetCoreWallComponent"] = raw(sc(vs.GetCoreWallComponent, h))
    # INTEGER = vs.GetTaperedComponent(object)
    d["GetTaperedComponent"]  = raw(sc(vs.GetTaperedComponent, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 6: WALL-LEVEL CALLS (type 68)
# All take wall handle except where noted.
# ══════════════════════════════════════════════════════════════════

def discover_wall(h):
    d = {}

    # (startHt, endHt) = vs.WallHeight(wallHd)
    d["WallHeight"]            = raw(sc(vs.WallHeight, h))
    # GetWallHeight — no doc, presumably same as WallHeight
    d["GetWallHeight"]         = raw(sc(vs.GetWallHeight, h))
    # (startHeightTop, startHeightBottom, endHeightTop, endHeightBottom) = vs.GetWallCornerHeights(theWall)
    d["GetWallCornerHeights"]  = raw(sc(vs.GetWallCornerHeights, h))
    # (overallHeightTop, overallHeightBottom) = vs.GetWallOverallHeights(theWall)
    d["GetWallOverallHeights"] = raw(sc(vs.GetWallOverallHeights, h))

    # REAL = vs.WallWidth(wallHd)
    d["WallWidth"]             = raw(sc(vs.WallWidth, h))
    # (BOOLEAN, thicknessDist) = vs.GetWallThickness(h)
    d["GetWallThickness"]      = raw(sc(vs.GetWallThickness, h))

    # NOTE: WallArea_Gross(c) and WallArea_Net(c) take CRITERIA, not handle.
    # We CANNOT call them per-object. Use OVR 608/611 instead.

    # INTEGER = vs.GetNumWallPeaks(h)
    d["GetNumWallPeaks"]       = raw(sc(vs.GetNumWallPeaks, h))
    # (BOOLEAN, numWallBreaks) = vs.GetNumOfWallBreaks(wallH)
    d["GetNumOfWallBreaks"]    = raw(sc(vs.GetNumOfWallBreaks, h))
    # (leftCap, rightCap, round) = vs.GetWallCaps(theWall)
    d["GetWallCaps"]           = raw(sc(vs.GetWallCaps, h))
    # (4 offsets) = vs.GetWallCapsOffsets(theWall)
    d["GetWallCapsOffsets"]    = raw(sc(vs.GetWallCapsOffsets, h))
    # REAL = vs.GetLayerDeltaZOffset(theWall)
    d["GetLayerDeltaZOffset"]       = raw(sc(vs.GetLayerDeltaZOffset, h))
    # BOOLEAN = vs.GetLinkHeightToLayerDeltaZ(theWall)
    d["GetLinkHeightToLayerDeltaZ"] = raw(sc(vs.GetLinkHeightToLayerDeltaZ, h))
    # STRING = vs.GetWallStyle(theWall)
    d["GetWallStyle"]          = raw(sc(vs.GetWallStyle, h))
    # INTEGER = vs.GetWallPathType(wall)
    d["GetWallPathType"]       = raw(sc(vs.GetWallPathType, h))
    # BOOLEAN = vs.IsCurtainWall(wall)
    d["IsCurtainWall"]         = raw(sc(vs.IsCurtainWall, h))

    # Cross-check: OVR indices (all take handle + index → REAL/INT)
    d["OVR_608_gross"]   = raw(sc(vs.GetObjectVariableReal, h, 608))
    d["OVR_611_net"]     = raw(sc(vs.GetObjectVariableReal, h, 611))
    d["OVR_612"]         = raw(sc(vs.GetObjectVariableReal, h, 612))
    d["OVR_615_height"]  = raw(sc(vs.GetObjectVariableReal, h, 615))
    d["OVR_218"]         = raw(sc(vs.GetObjectVariableReal, h, 218))
    d["OVR_622_n_comp"]  = raw(sc(vs.GetObjectVariableInt, h, 622))
    d["OVR_623_h_above"] = raw(sc(vs.GetObjectVariableReal, h, 623))
    d["OVR_624_h_below"] = raw(sc(vs.GetObjectVariableReal, h, 624))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 7: SLAB CALLS (type 71)
# ══════════════════════════════════════════════════════════════════

def discover_slab(h):
    d = {}
    # REAL = vs.GetSlabHeight(slab)
    d["GetSlabHeight"]         = raw(sc(vs.GetSlabHeight, h))
    # LONGINT = vs.GetSlabStyle(slab)
    d["GetSlabStyle"]          = raw(sc(vs.GetSlabStyle, h))
    # INTEGER = vs.GetDatumSlabComponent(object)
    d["GetDatumSlabComponent"] = raw(sc(vs.GetDatumSlabComponent, h))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 8: ROOF / CSG SOLID CALLS (type 83, 84)
# ══════════════════════════════════════════════════════════════════

def discover_roof(h):
    d = {}
    # (BOOLEAN, genGableWall, bearingInset, roofThick, miterType, vertMiter)
    d["GetRoofAttributes"]  = raw(sc(vs.GetRoofAttributes, h))
    # INTEGER = vs.GetRoofVertices(roofObject)
    d["GetRoofVertices"]    = raw(sc(vs.GetRoofVertices, h))
    # LONGINT = vs.GetRoofStyle(roof)
    d["GetRoofStyle"]       = raw(sc(vs.GetRoofStyle, h))
    # INTEGER = vs.GetDatumRoofComp(object)
    d["GetDatumRoofComp"]   = raw(sc(vs.GetDatumRoofComp, h))
    # INTEGER = vs.GetNumRoofElements(roofObject)
    d["GetNumRoofElements"] = raw(sc(vs.GetNumRoofElements, h))

    # (BOOLEAN, vertexPt, slope, projection, eaveHeight) = vs.GetRoofEdge(theRoof, index)
    nv = sc(vs.GetRoofVertices, h)
    if isinstance(nv, int) and nv > 0:
        edges = []
        for i in range(1, min(nv + 1, 6)):
            edges.append({"i": i, "GetRoofEdge": raw(sc(vs.GetRoofEdge, h, i))})
        d["edges"] = edges

    # (roofRise, roofRun, miterType, holeStyle, vertPart, thickness)
    d["GetRoofFaceAttrib"] = raw(sc(vs.GetRoofFaceAttrib, h))
    # (axis1, axis2, Zaxis, upslope)
    d["GetRoofFaceCoords"] = raw(sc(vs.GetRoofFaceCoords, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 9: EXTRUDE CALLS (type 24)
# ══════════════════════════════════════════════════════════════════

def discover_extrude(h):
    d = {}
    # HANDLE = vs.FIn3D(objectHd) — first child of 3D object
    fi = sc(vs.FIn3D, h)
    d["FIn3D_exists"] = fi is not None
    if fi:
        d["FIn3D_HArea"]   = raw(sc(vs.HArea, fi))
        d["FIn3D_HPerim"]  = raw(sc(vs.HPerim, fi))
        d["FIn3D_HLength"] = raw(sc(vs.HLength, fi))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 10: PLUG-IN OBJECT CALLS (type 86)
# ══════════════════════════════════════════════════════════════════

def discover_pio(h, pio_name):
    d = {"pio_name": pio_name}

    # HANDLE = vs.GetCustomObjectPath(objectHand)
    ph = sc(vs.GetCustomObjectPath, h)
    d["path_exists"] = ph is not None
    if ph:
        d["path_HLength"] = raw(sc(vs.HLength, ph))
        d["path_HPerim"]  = raw(sc(vs.HPerim, ph))
        d["path_HArea"]   = raw(sc(vs.HArea, ph))

    # HANDLE = vs.GetCustomObjSecPath(objectHand)
    sh = sc(vs.GetCustomObjSecPath, h)
    d["secpath_exists"] = sh is not None
    if sh:
        d["secpath_HLength"] = raw(sc(vs.HLength, sh))

    # HANDLE = vs.GetCustomObjectProfileGroup(objectHand)
    pg = sc(vs.GetCustomObjectProfileGroup, h)
    d["profile_exists"] = pg is not None
    if pg:
        d["profile_HArea"]  = raw(sc(vs.HArea, pg))
        d["profile_HPerim"] = raw(sc(vs.HPerim, pg))

    # HANDLE = vs.GetCustomObjectWallHoleGroup(objectHand)
    wh = sc(vs.GetCustomObjectWallHoleGroup, h)
    d["wallhole_exists"] = wh is not None
    if wh:
        d["wallhole_HArea"]  = raw(sc(vs.HArea, wh))
        d["wallhole_HPerim"] = raw(sc(vs.HPerim, wh))

    # NOTE: GetCustomObjectInfo() takes NO parameters — skipped

    # (x, y, z) = vs.GetSymLoc3D(objectHandle)
    d["GetSymLoc3D"] = raw(sc(vs.GetSymLoc3D, h))

    # STRING = vs.GetPluginStyle(hObject)
    d["GetPluginStyle"] = raw(sc(vs.GetPluginStyle, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 11: MATERIAL-BASED QUANTITIES
# REAL = vs.GetMaterialArea(h, material)
# REAL = vs.GetMaterialVolume(h, material)
# ══════════════════════════════════════════════════════════════════

def discover_material_quantities(h):
    d = {}
    n = get_comp_count(h)
    if n <= 0:
        return d

    materials = []
    for i in range(1, n + 1):
        # (BOOLEAN, material) = vs.GetComponentMaterial(object, componentIndex)
        mat_raw = sc(vs.GetComponentMaterial, h, i)
        mat_val = mat_raw
        if isinstance(mat_raw, tuple) and len(mat_raw) >= 2:
            mat_val = mat_raw[1]
        if mat_val is not None:
            materials.append({
                "comp_index": i,
                "material_raw": raw(mat_raw),
                "GetMaterialArea":   raw(sc(vs.GetMaterialArea, h, mat_val)),
                "GetMaterialVolume": raw(sc(vs.GetMaterialVolume, h, mat_val)),
            })
    d["by_material"] = materials
    return d


# ══════════════════════════════════════════════════════════════════
# MAIN HARVESTER
# ══════════════════════════════════════════════════════════════════

results = []
seen = {}
errors = []

def harvest(h):
    if not h:
        return

    t = sc(vs.GetTypeN, h)
    if t is None:
        return

    cls = sc(vs.GetClass, h) or ""

    pio_name = None
    # HANDLE = vs.GetParametricRecord(h)
    pr = sc(vs.GetParametricRecord, h)
    if pr:
        pio_name = sc(vs.GetName, pr)

    key = f"{t}|{pio_name or ''}|{cls}"
    seen[key] = seen.get(key, 0) + 1
    if seen[key] > MAX_PER_TYPE:
        return

    obj = {
        "type_n": t,
        "class":  cls,
        "name":   sc(vs.GetName, h),
        "pio":    pio_name,
    }
    lh = sc(vs.GetLayer, h)
    if lh:
        obj["layer"] = sc(vs.GetName, lh)

    try:
        # ── 2D: safe on all objects ──
        obj["dims_2d"] = discover_2d(h)

        # ── 3D: guarded by type ──
        if t in (24, 68, 71, 83, 84, 86, 89) or t in SOLID_TYPES:
            obj["dims_3d"] = discover_3d(h, t)

        # ── WALL (type 68) ──
        if t == 68:
            obj["wall"]             = discover_wall(h)
            obj["comp_identity"]    = discover_comp_identity(h, t)
            obj["comp_quantities"]  = discover_comp_quantities(h, t)
            obj["wall_comp_detail"] = discover_wall_comp_detail(h)
            obj["materials"]        = discover_material_quantities(h)

        # ── SLAB (type 71) ──
        elif t == 71:
            obj["slab"]             = discover_slab(h)
            obj["comp_identity"]    = discover_comp_identity(h, t)
            obj["comp_quantities"]  = discover_comp_quantities(h, t)
            obj["materials"]        = discover_material_quantities(h)

        # ── ROOF / CSG SOLID (type 83, 84) ──
        elif t in (83, 84):
            obj["roof"]             = discover_roof(h)
            obj["comp_identity"]    = discover_comp_identity(h, t)
            obj["comp_quantities"]  = discover_comp_quantities(h, t)
            obj["materials"]        = discover_material_quantities(h)

        # ── EXTRUDE (type 24) ──
        elif t == 24:
            obj["extrude"]          = discover_extrude(h)

        # ── PLUG-IN OBJECT (type 86) ──
        elif t == 86:
            obj["pio_detail"]       = discover_pio(h, pio_name)
            nc = get_comp_count(h)
            if nc > 0:
                obj["comp_identity"] = discover_comp_identity(h, t)
                # Only try quantity calls on PIOs that are known wall/slab-like
                if pio_name in ("Slab",):
                    obj["comp_quantities"] = discover_comp_quantities(h, t)
                    obj["materials"]       = discover_material_quantities(h)

        # ── 2D SHAPES ──
        elif t in (2, 5, 6, 21, 25):
            nv = sc(vs.GetVertNum, h)
            obj["vertex_count"] = raw(nv)

    except Exception as e:
        obj["harvest_error"] = repr(e)
        errors.append(f"type={t} class={cls} pio={pio_name} err={repr(e)}")

    results.append(obj)


def run():
    vs.ForEachObject(harvest, "ALL")

    type_summary = {}
    for obj in results:
        key = f"type_{obj['type_n']}_{obj.get('pio') or 'none'}"
        type_summary[key] = type_summary.get(key, 0) + 1

    os.makedirs(EXPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = os.path.join(EXPORT_DIR, f"discovery_results_{ts}.json")

    with open(fp, "w", encoding="utf-8") as f:
        json.dump({
            "discovery_version": "1.2",
            "timestamp": ts,
            "objects_probed": len(results),
            "errors": errors,
            "type_summary": type_summary,
            "objects": results,
        }, f, indent=2, ensure_ascii=False)

    msg = f"Discovery V1.2 complete.\n"
    msg += f"Objects probed: {len(results)}\n"
    msg += f"Errors: {len(errors)}\n\n"
    for k, v in sorted(type_summary.items()):
        msg += f"  {k}: {v}\n"
    msg += f"\nFile: {fp}"
    vs.AlrtDialog(msg)

run()