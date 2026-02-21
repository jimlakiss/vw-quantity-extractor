
# iQs API Discovery Script V1.1
# ═══════════════════════════════════════════════════════════════════
# V1.1 CHANGES:
#   - Type-guarded: only call functions on types they're designed for
#   - No WallFootPrint (creates geometry — side effect)
#   - 3D calls only on known 3D types (24, 25, 68, 71, 84, 86)
#   - Component quantity calls only on walls (68), slabs (71), roofs (84)
#   - Wrapped problem calls in extra guards
#
# Output: discovery_results_YYYYMMDD_HHMMSS.json
# Read-only. No object modification.
# ═══════════════════════════════════════════════════════════════════

import vs, json, os
from datetime import datetime

EXPORT_DIR = "/Users/jameslakiss/Documents/Develop/iQs/10 VW Integration/JSONL_Exports"
MAX_PER_TYPE = 3

# Known 3D object types (safe to call ObjVolume, Centroid3D, etc.)
TYPES_3D = {24, 25, 34, 38, 40, 68, 71, 83, 84, 86, 89, 95,
            508, 509, 510, 511, 512, 513, 516, 517, 518, 519, 520, 521, 522}

# Types with wall components (safe for ComponentArea/Volume)
TYPES_WITH_COMPS = {68, 71, 84, 89}

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


# ══════════════════════════════════════════════════════════════════
# SECTION 1: UNIVERSAL 2D — safe on all objects
# ══════════════════════════════════════════════════════════════════

def discover_2d(h):
    d = {}
    d["HLength"] = raw(sc(vs.HLength, h))
    d["HHeight"] = raw(sc(vs.HHeight, h))
    d["HWidth"]  = raw(sc(vs.HWidth, h))
    d["HPerim"]  = raw(sc(vs.HPerim, h))
    d["HArea"]   = raw(sc(vs.HArea, h))
    d["GetBBox"] = raw(sc(vs.GetBBox, h))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 2: 3D CALLS — only on known 3D types
# ══════════════════════════════════════════════════════════════════

def discover_3d(h):
    d = {}
    d["Get3DInfo"]           = raw(sc(vs.Get3DInfo, h))
    d["ObjVolume"]           = raw(sc(vs.ObjVolume, h))
    d["ObjSurfaceArea"]      = raw(sc(vs.ObjSurfaceArea, h))
    d["ObjSurfAreaInWorldC"] = raw(sc(vs.ObjSurfAreaInWorldC, h))
    d["Get3DCntr"]           = raw(sc(vs.Get3DCntr, h))
    d["Centroid3D"]          = raw(sc(vs.Centroid3D, h))
    d["ObjArea"]             = raw(sc(vs.ObjArea, h))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 3: COMPONENT IDENTITY — safe on anything with components
# ══════════════════════════════════════════════════════════════════

def get_comp_count(h):
    res = sc(vs.GetNumberOfComponents, h)
    if isinstance(res, tuple) and len(res) >= 2:
        return int(res[1] or 0)
    elif isinstance(res, (int, float)):
        return int(res or 0)
    return 0

def discover_comp_identity(h, t):
    """Component identity fields — safe on all types with components."""
    n = get_comp_count(h)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}
        c["GetComponentName"]     = raw(sc(vs.GetComponentName, h, i))
        c["GetComponentClass"]    = raw(sc(vs.GetComponentClass, h, i))
        c["GetComponentWidth"]    = raw(sc(vs.GetComponentWidth, h, i))
        c["GetComponentFunction"] = raw(sc(vs.GetComponentFunction, h, i))
        c["GetComponentMaterial"] = raw(sc(vs.GetComponentMaterial, h, i))
        c["GetComponentTexture"]  = raw(sc(vs.GetComponentTexture, h, i))
        d["components"].append(c)

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 4: COMPONENT QUANTITIES — ONLY on walls/slabs/roofs
# These calls need valid 3D geometry per component.
# ══════════════════════════════════════════════════════════════════

def discover_comp_quantities(h, t):
    """Per-component area/volume. ONLY for types 68, 71, 84."""
    n = get_comp_count(h)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}
        c["name"] = raw(sc(vs.GetComponentName, h, i))

        # ── THE KEY QUANTITY CALLS ──
        # ComponentArea: "area of one side, minus any holes"
        c["ComponentArea"]         = raw(sc(vs.ComponentArea, h, i))
        # GetComponentArea: (variant naming)
        c["GetComponentArea"]      = raw(sc(vs.GetComponentArea, h, i))
        # GetComponentNetArea: "net area of a component"
        c["GetComponentNetArea"]   = raw(sc(vs.GetComponentNetArea, h, i))
        # ComponentVolume: "3D volume, minus any holes"
        c["ComponentVolume"]       = raw(sc(vs.ComponentVolume, h, i))
        # GetComponentVolume: (variant naming)
        c["GetComponentVolume"]    = raw(sc(vs.GetComponentVolume, h, i))
        # GetComponentNetVolume: "net volume of a component"
        c["GetComponentNetVolume"] = raw(sc(vs.GetComponentNetVolume, h, i))

        d["components"].append(c)

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 5: WALL-SPECIFIC COMPONENT CALLS (type 68 only)
# ══════════════════════════════════════════════════════════════════

def discover_wall_comp_detail(h):
    """Wall-only per-component calls: offsets, peaks, start/end pts."""
    n = get_comp_count(h)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}
        c["name"] = raw(sc(vs.GetComponentName, h, i))

        # Offsets
        c["GetComponentWallTopOffset"]    = raw(sc(vs.GetComponentWallTopOffset, h, i))
        c["GetComponentWallBottomOffset"] = raw(sc(vs.GetComponentWallBottomOffset, h, i))

        # Peaks
        c["GetComponentFollowTopWallPeaks"]   = raw(sc(vs.GetComponentFollowTopWallPeaks, h, i))
        c["GetComponentFollowBottomWallPeaks"] = raw(sc(vs.GetComponentFollowBottomWallPeaks, h, i))

        # Per-component start/end points (LEFT, CENTER, RIGHT)
        c["GetWallCompStartPts"] = raw(sc(vs.GetWallCompStartPts, h, i))
        c["GetWallCompEndPts"]   = raw(sc(vs.GetWallCompEndPts, h, i))

        # Bound info
        c["GetCompBoundOffset"]              = raw(sc(vs.GetCompBoundOffset, h, i))
        c["GetCompWallAssBound"]             = raw(sc(vs.GetCompWallAssBound, h, i))
        c["GetCompWallAssMod"]               = raw(sc(vs.GetCompWallAssMod, h, i))
        c["GetComponentAutoBoundEdgeOffset"] = raw(sc(vs.GetComponentAutoBoundEdgeOffset, h, i))
        c["GetComponentManualEdgeOffset"]    = raw(sc(vs.GetComponentManualEdgeOffset, h, i))

        d["components"].append(c)

    # Wall-level component info
    d["GetCoreWallComponent"] = raw(sc(vs.GetCoreWallComponent, h))
    d["GetTaperedComponent"]  = raw(sc(vs.GetTaperedComponent, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 6: WALL-LEVEL CALLS (type 68)
# ══════════════════════════════════════════════════════════════════

def discover_wall(h):
    d = {}

    # Height variants
    d["WallHeight"]            = raw(sc(vs.WallHeight, h))
    d["GetWallHeight"]         = raw(sc(vs.GetWallHeight, h))
    d["GetWallCornerHeights"]  = raw(sc(vs.GetWallCornerHeights, h))
    d["GetWallOverallHeights"] = raw(sc(vs.GetWallOverallHeights, h))

    # Width / Thickness
    d["WallWidth"]             = raw(sc(vs.WallWidth, h))
    d["GetWallThickness"]      = raw(sc(vs.GetWallThickness, h))

    # Area (dedicated wall area calls)
    d["WallArea_Gross"]        = raw(sc(vs.WallArea_Gross, h))
    d["WallArea_Net"]          = raw(sc(vs.WallArea_Net, h))

    # NOTE: WallFootPrint CREATES a polyline — skipped (side effect)

    # Peaks
    d["GetNumWallPeaks"]       = raw(sc(vs.GetNumWallPeaks, h))

    # Breaks
    d["GetNumOfWallBreaks"]    = raw(sc(vs.GetNumOfWallBreaks, h))

    # Caps
    d["GetWallCaps"]           = raw(sc(vs.GetWallCaps, h))
    d["GetWallCapsOffsets"]    = raw(sc(vs.GetWallCapsOffsets, h))

    # Layer links
    d["GetLayerDeltaZOffset"]       = raw(sc(vs.GetLayerDeltaZOffset, h))
    d["GetLinkHeightToLayerDeltaZ"] = raw(sc(vs.GetLinkHeightToLayerDeltaZ, h))

    # Style
    d["GetWallStyle"]          = raw(sc(vs.GetWallStyle, h))
    d["GetWallPathType"]       = raw(sc(vs.GetWallPathType, h))
    d["IsCurtainWall"]         = raw(sc(vs.IsCurtainWall, h))

    # Cross-check: existing OVR indices
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
    d["GetSlabHeight"]         = raw(sc(vs.GetSlabHeight, h))
    d["GetSlabStyle"]          = raw(sc(vs.GetSlabStyle, h))
    d["GetDatumSlabComponent"] = raw(sc(vs.GetDatumSlabComponent, h))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 8: ROOF / CSG SOLID CALLS (type 83, 84)
# ══════════════════════════════════════════════════════════════════

def discover_roof(h, t):
    d = {}
    d["GetRoofAttributes"]  = raw(sc(vs.GetRoofAttributes, h))
    d["GetRoofVertices"]    = raw(sc(vs.GetRoofVertices, h))
    d["GetRoofStyle"]       = raw(sc(vs.GetRoofStyle, h))
    d["GetDatumRoofComp"]   = raw(sc(vs.GetDatumRoofComp, h))
    d["GetNumRoofElements"] = raw(sc(vs.GetNumRoofElements, h))

    nv = sc(vs.GetRoofVertices, h)
    if isinstance(nv, int) and nv > 0:
        edges = []
        for i in range(1, min(nv + 1, 10)):
            edges.append({"i": i, "GetRoofEdge": raw(sc(vs.GetRoofEdge, h, i))})
        d["edges"] = edges

    d["GetRoofFaceAttrib"] = raw(sc(vs.GetRoofFaceAttrib, h))
    d["GetRoofFaceCoords"] = raw(sc(vs.GetRoofFaceCoords, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 9: EXTRUDE CALLS (type 24)
# ══════════════════════════════════════════════════════════════════

def discover_extrude(h):
    d = {}
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

    # Path
    ph = sc(vs.GetCustomObjectPath, h)
    d["path_exists"] = ph is not None
    if ph:
        d["path_HLength"]  = raw(sc(vs.HLength, ph))
        d["path_HPerim"]   = raw(sc(vs.HPerim, ph))
        d["path_HArea"]    = raw(sc(vs.HArea, ph))

    # Second path
    sh = sc(vs.GetCustomObjSecPath, h)
    d["secpath_exists"] = sh is not None
    if sh:
        d["secpath_HLength"] = raw(sc(vs.HLength, sh))

    # Profile group
    pg = sc(vs.GetCustomObjectProfileGroup, h)
    d["profile_exists"] = pg is not None
    if pg:
        d["profile_HArea"]  = raw(sc(vs.HArea, pg))
        d["profile_HPerim"] = raw(sc(vs.HPerim, pg))

    # Wall hole group (doors, windows)
    wh = sc(vs.GetCustomObjectWallHoleGroup, h)
    d["wallhole_exists"] = wh is not None
    if wh:
        d["wallhole_HArea"]  = raw(sc(vs.HArea, wh))
        d["wallhole_HPerim"] = raw(sc(vs.HPerim, wh))

    # PIO info
    d["GetCustomObjectInfo"] = raw(sc(vs.GetCustomObjectInfo, h))

    # 3D location
    d["GetSymLoc3D"] = raw(sc(vs.GetSymLoc3D, h))

    # Style
    d["GetPluginStyle"] = raw(sc(vs.GetPluginStyle, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 11: MATERIAL-BASED QUANTITIES
# ══════════════════════════════════════════════════════════════════

def discover_material_quantities(h):
    d = {}
    n = get_comp_count(h)
    if n <= 0:
        return d

    materials = []
    for i in range(1, n + 1):
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
# MAIN HARVESTER — type-guarded dispatch
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
        # ── 2D calls: safe on everything ──
        obj["dims_2d"] = discover_2d(h)

        # ── 3D calls: only on 3D types ──
        if t in TYPES_3D:
            obj["dims_3d"] = discover_3d(h)

        # ── TYPE-SPECIFIC ──

        if t == 68:  # Wall
            obj["wall"]              = discover_wall(h)
            obj["comp_identity"]     = discover_comp_identity(h, t)
            obj["comp_quantities"]   = discover_comp_quantities(h, t)
            obj["wall_comp_detail"]  = discover_wall_comp_detail(h)
            obj["materials"]         = discover_material_quantities(h)

        elif t == 71:  # Slab
            obj["slab"]              = discover_slab(h)
            obj["comp_identity"]     = discover_comp_identity(h, t)
            obj["comp_quantities"]   = discover_comp_quantities(h, t)
            obj["materials"]         = discover_material_quantities(h)

        elif t in (83, 84):  # Roof / CSG Solid
            obj["roof"]              = discover_roof(h, t)
            obj["comp_identity"]     = discover_comp_identity(h, t)
            obj["comp_quantities"]   = discover_comp_quantities(h, t)
            obj["materials"]         = discover_material_quantities(h)

        elif t == 24:  # Extrude
            obj["extrude"]           = discover_extrude(h)

        elif t == 86:  # Plug-in Object
            obj["pio_detail"]        = discover_pio(h, pio_name)
            # Some PIOs have components (e.g. Slab PIO)
            if get_comp_count(h) > 0:
                obj["comp_identity"] = discover_comp_identity(h, t)
                # Only try quantities on PIO if it's a slab/wall-like PIO
                if pio_name in ("Slab", "Wall"):
                    obj["comp_quantities"] = discover_comp_quantities(h, t)

        # ── 2D shapes: just vertex info ──
        elif t in (2, 5, 6, 21, 25):
            nv = sc(vs.GetVertNum, h)
            obj["vertex_count"] = raw(nv)

    except Exception as e:
        obj["harvest_error"] = repr(e)
        errors.append(f"type={t} class={cls} err={repr(e)}")

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
            "discovery_version": "1.1",
            "timestamp": ts,
            "objects_probed": len(results),
            "errors": errors,
            "type_summary": type_summary,
            "objects": results,
        }, f, indent=2, ensure_ascii=False)

    msg = f"Discovery V1.1 complete.\n"
    msg += f"Objects probed: {len(results)}\n"
    msg += f"Errors: {len(errors)}\n\n"
    for k, v in sorted(type_summary.items()):
        msg += f"  {k}: {v}\n"
    msg += f"\nFile: {fp}"
    vs.AlrtDialog(msg)

run()