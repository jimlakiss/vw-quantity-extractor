# iQs API Discovery Script V1.0
# ═══════════════════════════════════════════════════════════════════
# Purpose: Call every CONFIRMED quantity-related API on real objects
#          and dump raw return values + types to JSON.
#
# Covers every object type observed in your VW files:
#   Type 68:  Walls (34 objects)
#   Type 84:  CSG Solids (9 objects)  — roof_types in config
#   Type 71:  Slab/Floor/RoofFace (1 object)
#   Type 86:  Plug-in Objects (387 objects)
#             - FramingMember (316)
#             - Drilled Footing (34)
#             - Door (14)
#             - WinDoor 6.0 (13)
#             - Slab PIO (5)
#             - StructuralMember (3)
#             - Extrude Along Path (2)
#   Type 24:  Extrudes (127 objects)
#   Type  5:  Polygons (280 objects)
#   Type 21:  Polylines (96 objects)
#   Type  2:  Lines (257 objects)
#   Type 25:  3D Polygons (1 object)
#   Type  6:  Arcs (4 objects)
#   Type 17:  2D Loci (1 object)
#
# Every API call listed here is status=OK in the ping report.
# NO guessing, NO probing for calls that might not exist.
#
# Output: discovery_results_YYYYMMDD_HHMMSS.json
# This script does NOT modify any objects. Read-only.
# ═══════════════════════════════════════════════════════════════════

import vs, json, os, math
from datetime import datetime

EXPORT_DIR = "/Users/jameslakiss/Documents/Develop/iQs/10 VW Integration/JSONL_Exports"
MAX_PER_TYPE = 3  # Max objects to probe per (type, pio, class) combo

# ── Safe call wrapper ──
def sc(fn, *a, default=None):
    try:
        return fn(*a)
    except:
        return default

hv = lambda a: hasattr(vs, a)

def raw(val):
    """Convert VW return value to JSON-safe format."""
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
# SECTION 1: UNIVERSAL CALLS — work on any object handle
# ══════════════════════════════════════════════════════════════════

def discover_universal(h):
    """Confirmed API calls that take (handle) and return dimensions."""
    d = {}

    # 2D measurements
    d["HLength"]   = raw(sc(vs.HLength, h))
    d["HHeight"]   = raw(sc(vs.HHeight, h))
    d["HWidth"]    = raw(sc(vs.HWidth, h))
    d["HPerim"]    = raw(sc(vs.HPerim, h))
    d["HArea"]     = raw(sc(vs.HArea, h))
    d["HAreaN"]    = raw(sc(vs.HAreaN, h))
    d["HPerimN"]   = raw(sc(vs.HPerimN, h))
    d["ObjArea"]   = raw(sc(vs.ObjArea, h))
    d["ObjAreaN"]  = raw(sc(vs.ObjAreaN, h))

    # 3D measurements
    d["ObjVolume"]            = raw(sc(vs.ObjVolume, h))
    d["ObjSurfaceArea"]       = raw(sc(vs.ObjSurfaceArea, h))
    d["ObjSurfAreaInWorldC"]  = raw(sc(vs.ObjSurfAreaInWorldC, h))

    # 3D info: returns (height, width, depth)
    d["Get3DInfo"] = raw(sc(vs.Get3DInfo, h))

    # Bounding box: returns (p1, p2)
    d["GetBBox"]   = raw(sc(vs.GetBBox, h))

    # 3D position
    d["Get3DCntr"]  = raw(sc(vs.Get3DCntr, h))
    d["Centroid3D"] = raw(sc(vs.Centroid3D, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 2: COMPONENT CALLS — walls, slabs, roofs, any with comps
# ══════════════════════════════════════════════════════════════════

def discover_components(h, t):
    """Per-component API calls. Component API is shared across
    walls, slabs, roofs — anything with GetNumberOfComponents."""
    res = sc(vs.GetNumberOfComponents, h)
    n = 0
    if isinstance(res, tuple) and len(res) >= 2:
        n = int(res[1] or 0)
    elif isinstance(res, (int, float)):
        n = int(res or 0)
    if n <= 0:
        return {"n_components": 0}

    d = {"n_components": n, "components": []}

    for i in range(1, n + 1):
        c = {"index": i}

        # ── Identity ──
        c["GetComponentName"]     = raw(sc(vs.GetComponentName, h, i))
        c["GetComponentClass"]    = raw(sc(vs.GetComponentClass, h, i))
        c["GetComponentWidth"]    = raw(sc(vs.GetComponentWidth, h, i))
        c["GetComponentFunction"] = raw(sc(vs.GetComponentFunction, h, i))
        c["GetComponentMaterial"] = raw(sc(vs.GetComponentMaterial, h, i))

        # ── QUANTITY CALLS — the core of what we need ──

        # ComponentArea: "area of one side, minus any holes in the 3D object"
        c["ComponentArea"]        = raw(sc(vs.ComponentArea, h, i))

        # GetComponentArea: (likely same as above, different naming convention)
        c["GetComponentArea"]     = raw(sc(vs.GetComponentArea, h, i))

        # GetComponentNetArea: "net area of a component"
        c["GetComponentNetArea"]  = raw(sc(vs.GetComponentNetArea, h, i))

        # ComponentVolume: "3D volume, minus any holes in the 3D object"
        c["ComponentVolume"]      = raw(sc(vs.ComponentVolume, h, i))

        # GetComponentVolume: (likely same as above)
        c["GetComponentVolume"]   = raw(sc(vs.GetComponentVolume, h, i))

        # GetComponentNetVolume: "net volume of a component"
        c["GetComponentNetVolume"]= raw(sc(vs.GetComponentNetVolume, h, i))

        # ── WALL-SPECIFIC COMPONENT CALLS ──
        if t == 68:
            # Offsets from wall top/bottom
            c["GetComponentWallTopOffset"]    = raw(sc(vs.GetComponentWallTopOffset, h, i))
            c["GetComponentWallBottomOffset"] = raw(sc(vs.GetComponentWallBottomOffset, h, i))

            # Peaks
            c["GetComponentFollowTopWallPeaks"]    = raw(sc(vs.GetComponentFollowTopWallPeaks, h, i))
            c["GetComponentFollowBottomWallPeaks"]  = raw(sc(vs.GetComponentFollowBottomWallPeaks, h, i))

            # Per-component start/end points (LEFT, CENTER, RIGHT of component)
            # This gives us per-component LENGTH!
            c["GetWallCompStartPts"] = raw(sc(vs.GetWallCompStartPts, h, i))
            c["GetWallCompEndPts"]   = raw(sc(vs.GetWallCompEndPts, h, i))

            # Bound info
            c["GetCompBoundOffset"]              = raw(sc(vs.GetCompBoundOffset, h, i))
            c["GetCompWallAssBound"]             = raw(sc(vs.GetCompWallAssBound, h, i))
            c["GetCompWallAssMod"]               = raw(sc(vs.GetCompWallAssMod, h, i))
            c["GetComponentAutoBoundEdgeOffset"] = raw(sc(vs.GetComponentAutoBoundEdgeOffset, h, i))
            c["GetComponentManualEdgeOffset"]    = raw(sc(vs.GetComponentManualEdgeOffset, h, i))

        # ── Texture ──
        c["GetComponentTexture"] = raw(sc(vs.GetComponentTexture, h, i))

        d["components"].append(c)

    # ── Wall-level component info ──
    if t == 68:
        d["GetCoreWallComponent"]  = raw(sc(vs.GetCoreWallComponent, h))
        d["GetTaperedComponent"]   = raw(sc(vs.GetTaperedComponent, h))

    # ── Slab-level component info ──
    if t == 71:
        d["GetDatumSlabComponent"] = raw(sc(vs.GetDatumSlabComponent, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 3: WALL-SPECIFIC CALLS (type 68)
# ══════════════════════════════════════════════════════════════════

def discover_wall(h):
    """All confirmed wall-specific API calls."""
    d = {}

    # ── Height calls (multiple variants!) ──
    d["WallHeight"]             = raw(sc(vs.WallHeight, h))
    d["GetWallHeight"]          = raw(sc(vs.GetWallHeight, h))
    d["GetWallCornerHeights"]   = raw(sc(vs.GetWallCornerHeights, h))
    d["GetWallOverallHeights"]  = raw(sc(vs.GetWallOverallHeights, h))

    # ── Width / Thickness ──
    d["WallWidth"]              = raw(sc(vs.WallWidth, h))
    d["GetWallThickness"]       = raw(sc(vs.GetWallThickness, h))

    # ── Area (dedicated wall area calls) ──
    d["WallArea_Gross"]         = raw(sc(vs.WallArea_Gross, h))
    d["WallArea_Net"]           = raw(sc(vs.WallArea_Net, h))

    # ── FootPrint (returns polyline handle — we measure it) ──
    fp_h = sc(vs.WallFootPrint, h)
    d["WallFootPrint_exists"]   = fp_h is not None
    if fp_h:
        d["WallFootPrint_HLength"] = raw(sc(vs.HLength, fp_h))
        d["WallFootPrint_HPerim"]  = raw(sc(vs.HPerim, fp_h))
        d["WallFootPrint_HArea"]   = raw(sc(vs.HArea, fp_h))

    # ── Peaks ──
    d["GetNumWallPeaks"]        = raw(sc(vs.GetNumWallPeaks, h))
    np = sc(vs.GetNumWallPeaks, h)
    if isinstance(np, int) and np > 0:
        peaks = []
        for i in range(1, np + 1):
            peaks.append(raw(sc(vs.GetWallPeak, h, i)))
        d["peaks"] = peaks

    # ── Breaks ──
    d["GetNumOfWallBreaks"]     = raw(sc(vs.GetNumOfWallBreaks, h))

    # ── Caps ──
    d["GetWallCaps"]            = raw(sc(vs.GetWallCaps, h))
    d["GetWallCapsOffsets"]     = raw(sc(vs.GetWallCapsOffsets, h))

    # ── Layer/height links ──
    d["GetLayerDeltaZOffset"]       = raw(sc(vs.GetLayerDeltaZOffset, h))
    d["GetLinkHeightToLayerDeltaZ"] = raw(sc(vs.GetLinkHeightToLayerDeltaZ, h))

    # ── Style ──
    d["GetWallStyle"]           = raw(sc(vs.GetWallStyle, h))
    d["GetWallPathType"]        = raw(sc(vs.GetWallPathType, h))
    d["IsCurtainWall"]          = raw(sc(vs.IsCurtainWall, h))

    # ── Existing OVR indices we use (cross-check) ──
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
# SECTION 4: SLAB/FLOOR CALLS (type 71)
# ══════════════════════════════════════════════════════════════════

def discover_slab(h):
    """Slab-specific API calls."""
    d = {}
    d["GetSlabHeight"]          = raw(sc(vs.GetSlabHeight, h))
    d["GetSlabStyle"]           = raw(sc(vs.GetSlabStyle, h))
    d["GetDatumSlabComponent"]  = raw(sc(vs.GetDatumSlabComponent, h))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 5: ROOF / CSG SOLID CALLS (type 83, 84)
# ══════════════════════════════════════════════════════════════════

def discover_roof(h, t):
    """Roof and CSG Solid API calls."""
    d = {}

    if t in (83, 84):
        d["GetRoofAttributes"] = raw(sc(vs.GetRoofAttributes, h))
        d["GetRoofVertices"]   = raw(sc(vs.GetRoofVertices, h))
        d["GetRoofStyle"]      = raw(sc(vs.GetRoofStyle, h))
        d["GetDatumRoofComp"]  = raw(sc(vs.GetDatumRoofComp, h))
        d["GetNumRoofElements"]= raw(sc(vs.GetNumRoofElements, h))

        # Edge info
        nv = sc(vs.GetRoofVertices, h)
        if isinstance(nv, int) and nv > 0:
            edges = []
            for i in range(1, min(nv + 1, 10)):  # cap at 10
                edges.append({"i": i, "GetRoofEdge": raw(sc(vs.GetRoofEdge, h, i))})
            d["edges"] = edges

    # Roof face specific
    d["GetRoofFaceAttrib"] = raw(sc(vs.GetRoofFaceAttrib, h))
    d["GetRoofFaceCoords"] = raw(sc(vs.GetRoofFaceCoords, h))

    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 6: EXTRUDE CALLS (type 24)
# ══════════════════════════════════════════════════════════════════

def discover_extrude(h):
    """Extrude-specific calls. Type 24 = plain extrude."""
    d = {}
    # FIn3D: first component of a 3D object (the profile)
    fi = sc(vs.FIn3D, h)
    d["FIn3D_exists"] = fi is not None
    if fi:
        d["FIn3D_HArea"]   = raw(sc(vs.HArea, fi))
        d["FIn3D_HPerim"]  = raw(sc(vs.HPerim, fi))
        d["FIn3D_HLength"] = raw(sc(vs.HLength, fi))
    return d


# ══════════════════════════════════════════════════════════════════
# SECTION 7: PLUG-IN OBJECT CALLS (type 86)
# ══════════════════════════════════════════════════════════════════

def discover_pio(h, pio_name):
    """Plug-in object specific calls — path, profile, PIO params."""
    d = {"pio_name": pio_name}

    # Path objects (EAP, framing, etc.)
    ph = sc(vs.GetCustomObjectPath, h)
    d["GetCustomObjectPath_exists"] = ph is not None
    if ph:
        d["path_HLength"] = raw(sc(vs.HLength, ph))
        d["path_HPerim"]  = raw(sc(vs.HPerim, ph))
        d["path_HArea"]   = raw(sc(vs.HArea, ph))
        d["path_ObjArea"]  = raw(sc(vs.ObjArea, ph))
        d["path_Get3DInfo"]= raw(sc(vs.Get3DInfo, ph))

    # Second path (some PIOs have two paths)
    sh = sc(vs.GetCustomObjSecPath, h)
    d["GetCustomObjSecPath_exists"] = sh is not None
    if sh:
        d["secpath_HLength"] = raw(sc(vs.HLength, sh))

    # Profile group
    pg = sc(vs.GetCustomObjectProfileGroup, h)
    d["GetCustomObjectProfileGroup_exists"] = pg is not None
    if pg:
        d["profile_HArea"]  = raw(sc(vs.HArea, pg))
        d["profile_HPerim"] = raw(sc(vs.HPerim, pg))
        d["profile_Get3DInfo"] = raw(sc(vs.Get3DInfo, pg))

    # Wall hole group (doors, windows)
    wh = sc(vs.GetCustomObjectWallHoleGroup, h)
    d["GetCustomObjectWallHoleGroup_exists"] = wh is not None
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
# SECTION 8: MATERIAL-BASED QUANTITIES
# ══════════════════════════════════════════════════════════════════

def discover_material_quantities(h):
    """GetMaterialArea / GetMaterialVolume — area and volume BY material."""
    d = {}

    # Get component materials to test with
    res = sc(vs.GetNumberOfComponents, h)
    n = 0
    if isinstance(res, tuple) and len(res) >= 2:
        n = int(res[1] or 0)
    elif isinstance(res, (int, float)):
        n = int(res or 0)

    if n <= 0:
        d["note"] = "no components to test material calls on"
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
# SECTION 9: 2D SHAPES — Polygon, Polyline, Line, Arc
# ══════════════════════════════════════════════════════════════════

def discover_2d_shape(h, t):
    """2D shape specific calls — vertex info."""
    d = {}

    # Vertex count
    nv = sc(vs.GetVertNum, h)
    d["GetVertNum"] = raw(nv)

    # First and last vertex to check if closed
    if isinstance(nv, (int, float)) and nv and int(nv) > 0:
        nvi = int(nv)
        if hv("GetPolylineVertex"):
            d["first_vertex"] = raw(sc(vs.GetPolylineVertex, h, 1))
            d["last_vertex"]  = raw(sc(vs.GetPolylineVertex, h, nvi))

    return d


# ══════════════════════════════════════════════════════════════════
# MAIN HARVESTER
# ══════════════════════════════════════════════════════════════════

results = []
seen = {}

def harvest(h):
    if not h:
        return

    t = sc(vs.GetTypeN, h)
    cls = sc(vs.GetClass, h) or ""

    # Get PIO name if applicable
    pio_name = None
    pr = sc(vs.GetParametricRecord, h)
    if pr:
        pio_name = sc(vs.GetName, pr)

    # Limit: MAX_PER_TYPE per (type, pio, class)
    key = f"{t}|{pio_name or ''}|{cls}"
    seen[key] = seen.get(key, 0) + 1
    if seen[key] > MAX_PER_TYPE:
        return

    obj = {
        "type_n":  t,
        "class":   cls,
        "name":    sc(vs.GetName, h),
        "pio":     pio_name,
        "layer":   None,
    }
    lh = sc(vs.GetLayer, h)
    if lh:
        obj["layer"] = sc(vs.GetName, lh)

    # ── UNIVERSAL (every object) ──
    obj["universal"] = discover_universal(h)

    # ── WALLS (type 68) ──
    if t == 68:
        obj["wall"]        = discover_wall(h)
        obj["components"]  = discover_components(h, t)
        obj["materials"]   = discover_material_quantities(h)

    # ── SLABS (type 71) ──
    elif t == 71:
        obj["slab"]        = discover_slab(h)
        obj["components"]  = discover_components(h, t)
        obj["materials"]   = discover_material_quantities(h)

    # ── ROOFS / CSG SOLIDS (type 83, 84) ──
    elif t in (83, 84):
        obj["roof"]        = discover_roof(h, t)
        obj["components"]  = discover_components(h, t)
        obj["materials"]   = discover_material_quantities(h)

    # ── EXTRUDES (type 24) ──
    elif t == 24:
        obj["extrude"]     = discover_extrude(h)

    # ── PLUG-IN OBJECTS (type 86) ──
    elif t == 86:
        obj["pio_detail"]  = discover_pio(h, pio_name)
        # PIOs can also have components (e.g. Slab PIO)
        comp_check = sc(vs.GetNumberOfComponents, h)
        has_comps = False
        if isinstance(comp_check, tuple) and len(comp_check) >= 2:
            has_comps = int(comp_check[1] or 0) > 0
        elif isinstance(comp_check, (int, float)):
            has_comps = int(comp_check or 0) > 0
        if has_comps:
            obj["components"] = discover_components(h, t)
            obj["materials"]  = discover_material_quantities(h)

    # ── 2D SHAPES (type 2, 5, 6, 21, 25) ──
    elif t in (2, 5, 6, 21, 25):
        obj["shape_2d"]    = discover_2d_shape(h, t)

    # ── ANY OTHER with components ──
    else:
        comp_check = sc(vs.GetNumberOfComponents, h)
        has_comps = False
        if isinstance(comp_check, tuple) and len(comp_check) >= 2:
            has_comps = int(comp_check[1] or 0) > 0
        elif isinstance(comp_check, (int, float)):
            has_comps = int(comp_check or 0) > 0
        if has_comps:
            obj["components"] = discover_components(h, t)

    results.append(obj)

def run():
    vs.ForEachObject(harvest, "ALL")

    # ── Build summary ──
    type_summary = {}
    for obj in results:
        key = f"type_{obj['type_n']}_{obj.get('pio') or 'none'}"
        type_summary[key] = type_summary.get(key, 0) + 1

    # ── Write ──
    os.makedirs(EXPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = os.path.join(EXPORT_DIR, f"discovery_results_{ts}.json")

    with open(fp, "w", encoding="utf-8") as f:
        json.dump({
            "discovery_version": "1.0",
            "timestamp": ts,
            "objects_probed": len(results),
            "type_summary": type_summary,
            "objects": results,
        }, f, indent=2, ensure_ascii=False)

    # ── Quick console summary ──
    msg = f"Discovery V1.0 complete.\n"
    msg += f"Objects probed: {len(results)}\n\n"
    for k, v in sorted(type_summary.items()):
        msg += f"  {k}: {v}\n"
    msg += f"\nFile: {fp}"
    vs.AlrtDialog(msg)

run()