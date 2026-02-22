# -*- coding: utf-8 -*-
# iQs — Slab Component Areas + Net Volumes (robust)
# Version: 1.2
#
# What it tries (in order):
#   AREA:
#     1) vs.GetComponentNetArea(h, i)
#     2) vs.ComponentArea( vs.GetComponents(h), i )
#     3) vs.GetComponentArea(h, i)
#   VOLUME:
#     1) vs.GetComponentNetVolume(h, i)
#     2) vs.ComponentVolume( vs.GetComponents(h), i )
#     3) vs.GetComponentVolume(h, i)   (if available)
#
# Notes on units:
# - Vectorworks returns values in the document's internal units.
# - This script ALSO provides convenience conversions assuming the document is in millimetres:
#     area_mm2 -> area_m2 (÷ 1e6)
#     vol_mm3  -> vol_m3  (÷ 1e9)
#   If your document units are NOT mm, treat the *_mm2/*_mm3 fields as "raw" and ignore conversions.
#
# How to run in Vectorworks:
#   Tools > Plug-ins > Run Script...
#   Select a Slab (PIO) and run.
#
# Output:
# - Shows a dialog with per-component area + volume (and implied thickness)
# - Writes JSON next to the active .vwx (or to your user folder if file not saved)

import vs, os, json
from datetime import datetime

def unwrap(ret):
    """
    Normalize VW Python returns to (ok, value).
    Common patterns:
      - value
      - (value,)
      - (ok, value) where ok is bool or 0/1
    """
    if isinstance(ret, (list, tuple)):
        if len(ret) == 2:
            ok = ret[0]
            val = ret[1]
            if isinstance(ok, bool):
                return ok, val
            if isinstance(ok, (int, float)) and ok in (0, 1):
                return bool(ok), val
            return True, ret  # unknown 2-tuple
        if len(ret) == 1:
            return True, ret[0]
    return True, ret

def active_file_dir():
    try:
        ok, fp = unwrap(vs.GetFPathName())
        fp = str(fp) if fp else ""
    except Exception:
        fp = ""
    if fp and os.path.isfile(fp):
        return os.path.dirname(fp)
    # fallback to user folder
    try:
        ok, p = unwrap(vs.GetFolderPath(-2))
        p = str(p) if p else ""
        if p:
            return p
    except Exception:
        pass
    return os.path.expanduser("~")

def first_selected():
    return vs.FSActLayer()

def component_area(h, i):
    # 1) Net area
    if hasattr(vs, "GetComponentNetArea"):
        try:
            ok, a = unwrap(vs.GetComponentNetArea(h, i))
            if ok and a is not None:
                return True, float(a), "GetComponentNetArea"
        except Exception:
            pass

    # 2) ComponentArea(GetComponents(h), i)
    if hasattr(vs, "GetComponents") and hasattr(vs, "ComponentArea"):
        try:
            okc, c = unwrap(vs.GetComponents(h))
            if c:
                ok, a = unwrap(vs.ComponentArea(c, i))
                if a is not None:
                    return True, float(a), "ComponentArea(GetComponents)"
        except Exception:
            pass

    # 3) GetComponentArea
    if hasattr(vs, "GetComponentArea"):
        try:
            ok, a = unwrap(vs.GetComponentArea(h, i))
            if a is not None:
                return True, float(a), "GetComponentArea"
        except Exception:
            pass

    return False, None, "none"

def component_volume(h, i):
    # 1) Net volume
    if hasattr(vs, "GetComponentNetVolume"):
        try:
            ok, v = unwrap(vs.GetComponentNetVolume(h, i))
            if ok and v is not None:
                return True, float(v), "GetComponentNetVolume"
        except Exception:
            pass

    # 2) ComponentVolume(GetComponents(h), i)
    if hasattr(vs, "GetComponents") and hasattr(vs, "ComponentVolume"):
        try:
            okc, c = unwrap(vs.GetComponents(h))
            if c:
                ok, v = unwrap(vs.ComponentVolume(c, i))
                if v is not None:
                    return True, float(v), "ComponentVolume(GetComponents)"
        except Exception:
            pass

    # 3) GetComponentVolume (if available)
    if hasattr(vs, "GetComponentVolume"):
        try:
            ok, v = unwrap(vs.GetComponentVolume(h, i))
            if v is not None:
                return True, float(v), "GetComponentVolume"
        except Exception:
            pass

    return False, None, "none"

def mm2_to_m2(a_mm2):
    return a_mm2 / 1_000_000.0

def mm3_to_m3(v_mm3):
    return v_mm3 / 1_000_000_000.0

def implied_thickness_mm(area_mm2, vol_mm3):
    # thickness(mm) = volume(mm3) / area(mm2)
    if area_mm2 is None or vol_mm3 is None:
        return None
    if abs(area_mm2) < 1e-9:
        return None
    return vol_mm3 / area_mm2

def main():
    h = first_selected()
    if not h:
        vs.AlrtDialog("Select a Slab PIO first, then run this script.")
        return

    if not hasattr(vs, "GetNumberOfComponents"):
        vs.AlrtDialog("Missing API: vs.GetNumberOfComponents")
        return

    okN, n = unwrap(vs.GetNumberOfComponents(h))
    try:
        n = int(n)
    except Exception:
        n = 0

    if (not okN) or n <= 0:
        vs.AlrtDialog("No components found.\n\nMake sure the selected object is a Slab PIO with components.")
        return

    rows = []
    lines = []

    for i in range(1, n + 1):
        # Optional metadata
        name = ""
        cls  = ""
        mat  = ""

        if hasattr(vs, "GetComponentName"):
            ok, v = unwrap(vs.GetComponentName(h, i))
            if ok and v: name = str(v)

        if hasattr(vs, "GetComponentClass"):
            ok, v = unwrap(vs.GetComponentClass(h, i))
            if ok and v: cls = str(v)

        if hasattr(vs, "GetComponentMaterial"):
            ok, v = unwrap(vs.GetComponentMaterial(h, i))
            if ok and v: mat = str(v)

        okA, area_raw, area_method = component_area(h, i)
        okV, vol_raw,  vol_method  = component_volume(h, i)

        # Convenience conversions (assume mm)
        area_m2 = mm2_to_m2(area_raw) if area_raw is not None else None
        vol_m3  = mm3_to_m3(vol_raw)  if vol_raw  is not None else None
        t_mm    = implied_thickness_mm(area_raw, vol_raw)

        row = {
            "component_index": i,
            "component_name": name,
            "component_class": cls,
            "component_material": mat,

            "net_area_raw": area_raw,
            "net_area_method": area_method,
            "net_area_mm2": area_raw,
            "net_area_m2": area_m2,

            "net_volume_raw": vol_raw,
            "net_volume_method": vol_method,
            "net_volume_mm3": vol_raw,
            "net_volume_m3": vol_m3,

            "implied_thickness_mm": t_mm,
            "unit_assumption": "mm (for *_mm2/*_mm3 and *_m2/*_m3 conversions)"
        }
        rows.append(row)

        disp_name = name if name else f"Component {i}"
        a_txt = f"{area_m2:.6f} m²" if area_m2 is not None else "n/a"
        v_txt = f"{vol_m3:.6f} m³" if vol_m3 is not None else "n/a"
        t_txt = f"{t_mm:.2f} mm" if t_mm is not None else "n/a"
        lines.append(f"{i:02d} | {disp_name} | A={a_txt} ({area_method}) | V={v_txt} ({vol_method}) | t≈{t_txt}")

    out_dir = active_file_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_fp = os.path.join(out_dir, f"slab_component_area_volume_{ts}.json")

    payload = {
        "tool": "iqs_slab_component_areas",
        "version": "1.2",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "doc_path": str(unwrap(vs.GetFPathName())[1]) if hasattr(vs, "GetFPathName") else "",
        "component_count": n,
        "components": rows
    }

    try:
        with open(out_fp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        vs.AlrtDialog("Computed component quantities, but failed to write JSON:\n\n" + str(e) +
                      "\n\nDialog output below:\n\n" + "\n".join(lines))
        return

    vs.AlrtDialog("Component quantities computed.\n\n" +
                  "\n".join(lines) +
                  "\n\nJSON written to:\n" + out_fp)

if __name__ == "__main__":
    main()
