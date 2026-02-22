# -*- coding: utf-8 -*-

# THIS WAS JL'S AMENDMENT FOR THE SLAB AREA NET ISSUE!

# iQs — Slab Component Areas (robust: NetArea / ComponentArea / GetComponentArea) 
# Version: 1.1
#
# What it tries (in order):
#   1) vs.GetComponentNetArea(h, i)        (best for slabs/walls/roofs; "net" area)
#   2) vs.ComponentArea(c, i) where c = vs.GetComponents(h)
#   3) vs.GetComponentArea(h, i)           (some object types; may return 0 for slabs)
#
# How to run in Vectorworks:
#   Tools > Plug-ins > Run Script...
#   Select a Slab (PIO) and run.
#
# Output:
# - Shows a dialog with component areas
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
            # Unknown 2-tuple: assume it's (value1, value2) and ok=true
            return True, ret
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
    h = vs.FSActLayer()
    return h

def component_area(h, i):
    """
    Returns (ok, area, method_name)
    """
    # 1) Net area
    if hasattr(vs, "GetComponentNetArea"):
        try:
            a = vs.GetComponentNetArea(h, i)
            ok, a = unwrap(a)
            if ok and a is not None:
                return True, float(a), "GetComponentNetArea"
        except Exception:
            pass

    # 2) ComponentArea(GetComponents(h), i)
    if hasattr(vs, "GetComponents") and hasattr(vs, "ComponentArea"):
        try:
            c = vs.GetComponents(h)
            okc, c = unwrap(c)
            if c:
                a = vs.ComponentArea(c, i)
                ok, a = unwrap(a)
                # ComponentArea returns REAL directly; treat any numeric as ok
                if a is not None:
                    return True, float(a), "ComponentArea(GetComponents)"
        except Exception:
            pass

    # 3) GetComponentArea (often not slab-friendly)
    if hasattr(vs, "GetComponentArea"):
        try:
            a = vs.GetComponentArea(h, i)
            ok, a = unwrap(a)
            if a is not None:
                return True, float(a), "GetComponentArea"
        except Exception:
            pass

    return False, None, "none"

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

        okA, area, method = component_area(h, i)

        row = {
            "component_index": i,
            "component_name": name,
            "component_class": cls,
            "component_material": mat,
            "component_area": area,
            "area_method": method
        }
        rows.append(row)

        disp_name = name if name else f"Component {i}"
        a_txt = f"{area:.6f}" if area is not None else "n/a"
        lines.append(f"{i:02d} | {disp_name} | area={a_txt} | via {method}")

    out_dir = active_file_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_fp = os.path.join(out_dir, f"slab_component_areas_{ts}.json")

    payload = {
        "tool": "iqs_slab_component_areas",
        "version": "1.1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "doc_path": str(unwrap(vs.GetFPathName())[1]) if hasattr(vs, "GetFPathName") else "",
        "component_count": n,
        "components": rows
    }

    try:
        with open(out_fp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        vs.AlrtDialog("Computed component areas, but failed to write JSON:\n\n" + str(e) +
                      "\n\nDialog output below:\n\n" + "\n".join(lines))
        return

    vs.AlrtDialog("Component areas computed.\n\n" +
                  "\n".join(lines) +
                  "\n\nJSON written to:\n" + out_fp)

if __name__ == "__main__":
    main()
