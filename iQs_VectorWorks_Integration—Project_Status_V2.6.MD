# iQs VectorWorks Integration — Project Status

**Last updated:** 2026-02-22
**Current extractor:** V2.16
**Current ERB:** show.html.erb (V2.12 features + V2.16 slab fix attempt)

---

## 1. SYSTEM OVERVIEW

A VectorWorks → Rails pipeline for quantity surveying (QS):

```
VectorWorks → Python Exporter → JSONL file → HTTP POST → Rails API
                                                           ↓
                                              VwImportProcessor → Postgres
                                                           ↓
                                              Staging UI (show.html.erb)
                                              - Mapping Panel (assign UoM sources)
                                              - Data Rows (resolved quantities)
                                              - Component sub-rows
```

### Key Principle
VW's geometry engine (`GetComponentNetArea`, `GetComponentNetVolume`) handles complex geometry — wall openings, peaked/raked walls, slab edge offsets. These API values are PRIMARY. Never calculate area from height × length; treat area and volume as direct measurements.

---

## 2. FILE LOCATIONS

### Extractor (runs inside VectorWorks)
- **Current:** `iqs_vw_exporter_V2.16.py`
- **Export dir:** `/Users/jameslakiss/Documents/Develop/iQs/10 VW Integration/JSONL_Exports`
- **Output:** `vw_qdump_all_YYYYMMDD_HHMMSS.jsonl` + `_debug.txt`
- **Posts to:** `http://localhost:3000/vw_imports`

### Rails Application
```
app/
  controllers/
    vw_imports_controller.rb          # index, show (staging), create (API)
    measurement_mappings_controller.rb # create/update mappings, sample_values
  models/
    vw_import.rb                      # has_many :vw_objects
    vw_object.rb                      # belongs_to :vw_import, zone classification
    measurement_mapping.rb            # hierarchy lookup, 8 UoM fields + name_src
    component_measurement_mapping.rb  # per-component 8 UoM fields
  services/
    vw_import_processor.rb            # JSONL → Postgres (build_row, quantities)
    mapping_resolver.rb               # source string → numeric value resolution
    measurement_mapping_seeds.rb      # seed data
  views/
    vw_imports/
      index.html.erb                  # import listing
      show.html.erb                   # THE BIG ONE — staging/mapping UI (~890 lines)
config/
  routes_addition.rb                  # resources :vw_imports, :measurement_mappings
db/
  migrate/                            # 6 migration files (see schema below)
```

---

## 3. DATABASE SCHEMA

### vw_imports
| Column | Type | Notes |
|--------|------|-------|
| project | string | UNIQUE, not null |
| exporter_version | string | "2.16" |
| exported_at | datetime | |
| object_count | integer | |
| jsonl_path | string | |
| status | string | received → processing → ready / error |

### vw_objects
| Column | Type | Notes |
|--------|------|-------|
| vw_import_id | FK | |
| vw_class | string | VW class hierarchy e.g. "Wall-Exterior-Timber-Frame" |
| layer | string | |
| vw_type | integer | 68=wall, 71=slab, 84=roof, 86=PIO, 24=extrude, etc. |
| pio | string | PIO name e.g. "Door", "FramingMember", "Slab" |
| name | string | Best available display name (from promote()) |
| description | string | Combined description string |
| ifc_entity | string | e.g. "IfcWall", "IfcSlab" |
| style_name | string | Plugin style name |
| uvw_length | integer | mm |
| uvw_width | integer | mm |
| uvw_height | integer | mm |
| area | decimal | m² — primary area |
| area_plan | decimal | m² — floor/roof plan (from VW area_2d) |
| area_vertical | decimal | m² — wall face |
| perimeter | integer | mm |
| volume | decimal | m³ |
| material | string | First component material |
| components | jsonb | Array of component dicts from extractor |
| raw_json | jsonb | ENTIRE extractor output for this object |
| zone | string | "matched" / "unmatched" / "annotation" |
| iqs_uuid | string | Persistent UUID across re-exports |

### measurement_mappings
| Column | Type | Notes |
|--------|------|-------|
| mapping_key | string | UNIQUE — "ClassName\|type\|pio" or "*\|68\|" |
| class_pattern | string | "Wall-Exterior" or "*" |
| class_depth | integer | Hierarchy depth for specificity |
| vw_type | integer | |
| pio | string | |
| name_src | string | Display name source e.g. "vw_name", "wall.wall_style_api" |
| count_src..volume_src | string × 8 | Source field references |
| confidence | string | auto / reviewed / manual |

### component_measurement_mappings
Same 8 UoM source fields, keyed by `(measurement_mapping_id, component_class, component_index)`.

---

## 4. MAPPING SYSTEM

### Hierarchy Lookup Order
For class "Wall-Exterior-Timber-Frame-CSR5877", type 68:
1. `Wall-Exterior-Timber-Frame-CSR5877|68|` (exact)
2. `Wall-Exterior-Timber-Frame|68|` (parent)
3. `Wall-Exterior-Timber|68|` (grandparent)
4. `Wall-Exterior|68|`
5. `Wall|68|`
6. `*|68|` (wildcard)
7. `*|68|*` (wildcard + any PIO)

### Source Field Types
- **Raw fields:** `uvw.u`, `wall.length`, `areas.area_2d`, etc. (dot-notation into raw_json)
- **Component fields:** `comp.thickness`, `comp.net_area_m2`, `comp.net_volume_m3`
- **Parent inherit:** `parent.length`, `parent.width`, etc.
- **Calculated:** `calc.l_x_h`, `calc.comp_wall_area`, `calc.eff_height`, etc.
- **Fixed:** `fixed_1`, `null`

### 8 BOQ Fields (parent AND component level)
Count, Length, Width, Height, Perim, Area, V.Area (vertical/component area), Volume

### Display Name Sources
Dropdown in mapping panel. Options include:
- Direct: `vw_name` (GetName — OIP object name), `description`, `ifc_name`, `style_name`, `class`, etc.
- Wall sub-dict: `wall.wall_style_api`, `wall.wall_style`, etc.
- Slab sub-dict: `slab.slab_style`, etc.
- PIO params: `pio.xxx` (rich for doors/windows)
- Record fields: `rec.RecordName::FieldName`
- User fields: `uf.xxx`

### Name Promotion (promote() in extractor)
Priority chain for auto-name:
`ifc_name → description → style_name → wall_style_api → slab_style → labelText → vw_name`

---

## 5. EXTRACTOR INTERNALS

### Key Functions
| Function | Purpose |
|----------|---------|
| `sc(fn, *a)` | Safe call — try/except wrapper, returns raw VW result |
| `sf(val)` | Safe float — strips units, returns float > 0 or None |
| `sfz(val)` | Safe float allowing zero |
| `hv(api_name)` | Has VW API — `hasattr(vs, api_name)` |
| `cv(val)` | Clean value — strips whitespace, returns None for empty |
| `gc(api, key, transform)` | Get component field — calls `_unwrap_ok_val(sc(vs.API, h, i))` then transform |
| `_unwrap_ok_val(r)` | Normalizes VW returns `(ok, value)` from tuples/lists |
| `harvest(h)` | Main per-object extraction |
| `get_components_raw(h, t)` | Extracts all component data for types 68/71/84 |
| `promote(o)` | Builds name, description, user_fields from all sources |
| `plan_quantities(h, t, ...)` | Gets area_2d, perim_2d, len_2d from VW |

### VW API Return Pattern
VW Python API often returns `(ok_bool, value)` tuples. The `_unwrap_ok_val()` function handles this. **This was the source of the slab area bug** — `GetComponentNetArea` returns a tuple but the old code tried to `float()` the raw tuple.

### Component Data Flow
```
get_components_raw(h, t):
  for each component index 1..n:
    gc("GetComponentName", "name")           # → _unwrap_ok_val → cv
    gc("GetComponentWidth", "thickness", sf)  # → _unwrap_ok_val → sf
    gc("GetComponentClass", "class")          # custom unwrap + resolve
    gc("GetComponentNetArea", "net_area_mm2", sf)   # V2.16: now uses gc()
    gc("GetComponentNetVolume", "net_volume_mm3", sf) # V2.16: now uses gc()
    # Then derives net_area_m2 = net_area_mm2 / 1e6
```

---

## 6. CRITICAL OPEN BUG — SLAB COMPONENT AREAS

### The Problem
All slab components show the SAME area (base slab area, e.g. 10.5 m²) instead of per-component offset-adjusted areas (e.g. 10.5, 9.69, 9.69 m²).

### What We Know
1. **VW's API returns correct per-component areas** — proven by Jim's standalone test script (`iqs_slab_component_areas_v1_1.py`) which returned: Concrete=10,500,000 mm², Stone Screening=9,689,999 mm², Subgrade=9,689,999 mm². `GetComponentNetArea` DOES account for slab edge offsets.

2. **The extractor was NOT unwrapping the return value correctly.** The original code did:
   ```python
   na_mm2 = sc(vs.GetComponentNetArea, h, i)  # returns (True, 10500000.0)
   na = float(na_mm2)  # float((True, 10500000.0)) → TypeError → except: pass
   ```

3. **V2.16 fix attempt:** Changed to use `gc()` (same code path as thickness, class, material — all of which work). Also upgraded `_unwrap_ok_val()` to match Jim's proven `unwrap()` pattern.

4. **V2.16 has NOT yet been tested.** Diagnostic logging added:
   ```
   SLAB COMP AREA: comp=1 type=xxx raw=xxx → stored=xxx
   ```
   These lines appear in the `_debug.txt` file next to the JSONL export.

### What to Check After Export
In `_debug.txt`, search for `SLAB COMP AREA`. Three possible outcomes:
- **Raw values differ, stored differs** → extractor fixed, check Rails display
- **Raw values differ, stored same** → gc()/sf() still losing the value
- **Raw values all same** → VW behaves differently in batch vs standalone

### Possible Caching Issue
Re-exporting with the old buggy extractor writes broken data to JSONL. Rails imports that JSONL into Postgres. The UI reads Postgres. So even after fixing the extractor, you MUST:
1. Re-export from VW (creates new JSONL)
2. Re-import into Rails (Rails POSTs to /vw_imports which upserts by project name)

### Offset Polygon Geometry (REMOVED — not needed)
We tried manual offset calculation (A' = A₀ − P₀·d + π·d²) but this was unnecessary since VW handles offsets natively. All `offset_area_m2`, `offset_volume_m3`, `offset_perim_mm` fields have been removed from V2.16.

---

## 7. VERIFIED VW API CALLS

### Per-Object
| API | Returns | Notes |
|-----|---------|-------|
| `GetName(h)` | string | OIP object name (user-assigned) |
| `GetClass(h)` | string/int | Class name or index |
| `GetTypeN(h)` | int | 68=wall, 71=slab, 84=roof, 86=PIO, 24=extrude |
| `ObjArea(h)` | float | Plan area mm² |
| `ObjPerim(h)` | float | Plan perimeter mm |
| `HLength(h)` | float | Centreline length mm |
| `Get3DInfo(h)` | tuple | 3D bounding box dimensions |
| `GetDescriptionText(h)` | string | User description |
| `IFC_GetIFCEntity(h)` | string | e.g. "IfcWall" |
| `IFC_GetIFCName(h)` | string | User IFC name |
| `GetPluginStyle(h)` | string | Style name |

### Per-Component (types 68, 71, 84)
| API | Returns | Notes |
|-----|---------|-------|
| `GetNumberOfComponents(h)` | (ok, int) | Component count |
| `GetComponentName(h, i)` | (ok, string) | Component name |
| `GetComponentClass(h, i)` | (ok, string/int) | Component class |
| `GetComponentWidth(h, i)` | (ok, float) | Thickness mm |
| `GetComponentNetArea(h, i)` | (ok, float) | Net area mm² — **handles openings + offsets** |
| `GetComponentNetVolume(h, i)` | (ok, float) | Net volume mm³ |
| `GetComponentMaterial(h, i)` | (ok, string/int) | Material |

### Wall-Only
| API | Returns | Notes |
|-----|---------|-------|
| `GetWallCompStartPts(h, i)` | (left, center, right) | Per-component start points |
| `GetWallCompEndPts(h, i)` | (left, center, right) | Per-component end points |
| `GetWallCornerHeights(h)` | (startTop, startBot, endTop, endBot) | For raked/peaked |
| `GetWallOverallHeights(h)` | (top, bottom) | Overall heights |
| `GetComponentWallTopOffset(h, i)` | float | Top offset mm (negative = shorter) |
| `GetComponentWallBottomOffset(h, i)` | float | Bottom offset mm |
| `GetComponentFollowTopWallPeaks(h, i)` | bool | |
| `GetComponentFollowBottomWallPeaks(h, i)` | bool | |

### Slab-Only (type 71)
| API | Returns | Notes |
|-----|---------|-------|
| `GetSlabHeight(h)` | float | Slab elevation mm |
| `GetDatumSlabComponent(h)` | int | Datum component index |
| `GetSlabStyle(h)` | int | Style index (resolve via Index2Name) |
| `GetComponentAutoBoundEdgeOffset(h, i)` | float | Auto edge offset mm |
| `GetComponentManualEdgeOffset(h, i)` | float | Manual edge offset mm |

---

## 8. KEY GEOMETRY LEARNINGS

### Peaked/Raked Walls
- `GetComponentNetArea` returns CORRECT area for peaked/raked walls with openings
- Heights are displayed as start/end pairs (not single values)
- Effective height = area ÷ length (it's an AVERAGE, not real geometry)
- **Never calculate area FROM height** — area is the primary quantity

### Slab Edge Offsets
- `GetComponentNetArea` handles edge offsets natively — returns different areas per component
- Edge offsets stored for info display: `auto_edge_offset`, `manual_edge_offset`
- No manual polygon offset calculation needed

### Wall T-Junctions
- Centreline measurement works for most situations
- T-junctions: continuous components aren't automatically split at junctions (VW limitation)

### Component Filtering
- Components displayed where: `class.present? || name.present?`
- Ghost roof component (overall roof area appearing as component) — not reliably detectable, detection code removed

---

## 9. UI FEATURES (show.html.erb)

### Layout
- **Summary bar:** Reviewed / Auto-exact / Auto-wildcard / Unmapped counts
- **Per-class groups:** Collapsible panels sorted by confidence (unmapped first)
- **Left panel:** Available Raw Values table + Component info
- **Right panel:** UoM Assignment dropdowns (8 fields) + Component Mappings
- **Data rows:** One row per object, resolved quantities in columns
- **Component sub-rows:** One per component layer, indented

### Mapping Panel Features
- **Display Name selector:** Always shows "OIP Name (GetName)" option + all text fields from wall/slab/pio/record sub-dicts
- **8 BOQ field dropdowns:** Grouped by category (Dimensions, Wall API, PIO Dims, Areas, Calculated, etc.)
- **Component section:** Collapsible, shows all 8 fields per component with defaults
- **Save button:** POSTs to /measurement_mappings (exact class match)
- **Save * button:** POSTs wildcard mapping (any class, this type)

### Component Defaults
| Field | Default |
|-------|---------|
| Count | fixed_1 |
| Width | comp.thickness |
| V.Area | comp.net_area_m2 |
| Volume | comp.net_volume_m3 |
| Length, Height, Perim, Area | nil (unset) |

---

## 10. DATA FLOW DETAIL

### Export (VW → JSONL)
1. `run()` → iterate all objects matching criteria
2. `harvest(h)` per object → builds dict with type, class, areas, wall/slab detail, components
3. `get_components_raw(h, t)` → per-component quantities via `gc()` and `_unwrap_ok_val()`
4. `promote(o)` → builds name, description, user_fields
5. Writes JSONL line + debug line
6. HTTP POSTs entire payload to Rails

### Import (Rails)
1. `VwImportsController#create` → `VwImportProcessor.new(data).call`
2. Processor upserts `VwImport` (by project name), deletes old objects
3. `build_row()` per object → extracts UVW, wall, pio_dims, classifies zone
4. `VwObject.insert_all!` → bulk insert
5. **Components stored as JSONB array** — whatever extractor provides goes straight to Postgres

### Display (Staging UI)
1. `show` action groups objects by `vw_class`, finds mapping via hierarchy
2. ERB iterates groups → panels
3. For each object: `MappingResolver.new(obj, mapping).resolve` → `{count:, length:, width:, ...}`
4. For each component: reads from `obj.components` JSONB array
5. Component quantities: either MappingResolver (if mapping exists) or direct from component data

---

## 11. VERSION HISTORY

| Version | Key Changes |
|---------|-------------|
| V2.0–2.4 | Basic export, UVW mapping, tuple fix, unit stripping, footing/column dims |
| V2.5 | Material idx+1 offset fix, class-based filtering |
| V2.6 | HTTP POST to Rails, component display, EAP path length |
| V2.7 | API discovery — verified GetComponentNetArea/Volume/StartPts/EndPts |
| V2.8 | Integrated verified API calls, raked wall height pairs |
| V2.9 | Slab support (GetSlabHeight, edge offsets), object identification (IFC, description, tags, style) |
| V2.12 | Restored 8 BOQ component fields, name_sources enrichment, promote() wall/slab styles |
| V2.16 | **Slab area bug fix attempt** — gc() for NetArea/NetVolume, upgraded _unwrap_ok_val(), diagnostic logging |

---

## 12. NEXT STEPS / OUTSTANDING

1. **Slab area bug** — V2.16 needs testing. Check `_debug.txt` for `SLAB COMP AREA` lines. If areas still wrong, diagnostic output tells us exactly where the problem is.

2. **Ghost roof component** — VW reports overall roof plan area as a component. Not reliably detectable. Low priority.

3. **PIO object names (GetName)** — The `vw_name` field (from `vs.GetName(h)`) captures the user-assigned OIP name for any object including PIO objects like "Strip Footing SF1.4c". This is now always available in the Display Name dropdown as "OIP Name (GetName)". Needs testing to confirm it shows per-object names in data rows.

4. **BOQ export** — Staging area shows quantities but no export to actual BOQ format yet.

5. **T-junction splitting** — VW limitation where continuous wall components don't split at T-junctions.

---

## 13. DEVELOPMENT NOTES

### VW Python API Gotchas
- Returns vary: sometimes raw float, sometimes `(ok, value)` tuple, sometimes `(value,)` single-element tuple
- Always use `_unwrap_ok_val()` before consuming any VW return
- `hasattr(vs, "FunctionName")` checks if API exists — prevents crashes from speculative calls
- Some functions take criteria strings not object handles (discovered the hard way)
- VW crashes if you call non-existent functions — always guard with `hv()`

### Rails Notes
- `components` column is JSONB — stores raw array from extractor
- `raw_json` column is JSONB — stores ENTIRE object dict for ad-hoc access
- Upsert by project name: re-importing same project replaces all objects
- No authentication on API endpoint (localhost development)

### Mapping Persistence
- Mappings are GLOBAL (not per-import) — survive re-exports
- Hierarchy lookup means one wildcard `*|68|` covers all wall classes
- Specific class mappings override wildcards automatically
- Component mappings keyed by `(parent_mapping_id, component_class, component_index)`

### Jim's Test Files
- `/Users/jameslakiss/Documents/Develop/iQs/10 VW Integration/Test VW Files/Test_2.vwx` — 3-component slab with edge offsets
- Standalone test script: `iqs_slab_component_areas_v1_1.py` — proves GetComponentNetArea returns correct per-component areas