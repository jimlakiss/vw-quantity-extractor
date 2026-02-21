# iQs Rails Integration — V2.6 + Measurement Mapping

## Setup (fresh install)

```bash
rails db:migrate
rails db:seed          # loads 13 built-in measurement mappings
rails server
```

## Setup (existing install with data)

```bash
# Rename migration if needed:
mv db/migrate/20260215000003_create_measurement_mappings.rb db/migrate/20260215000003_create_measurement_mappings.rb

rails db:migrate       # creates measurement_mappings + component_measurement_mappings tables
rails db:seed          # loads built-in defaults
rails server
# Re-export from VectorWorks to refresh data
```

## Files (17 total)

### Models (4)
- `app/models/vw_import.rb` — import record (project, timestamp, object count)
- `app/models/vw_object.rb` — individual VW object with zone classification
- `app/models/measurement_mapping.rb` — UoM source mapping with hierarchy lookup
- `app/models/component_measurement_mapping.rb` — component-level UoM mapping

### Services (3)
- `app/services/vw_import_processor.rb` — ingests VW POST, builds vw_objects rows
- `app/services/mapping_resolver.rb` — resolves source field references to values
- `app/services/measurement_mapping_seeds.rb` — built-in default mappings

### Controllers (1)
- `app/controllers/vw_imports_controller.rb` — index, create (POST from VW), show (staging)

### Views (2)
- `app/views/vw_imports/index.html.erb` — import list
- `app/views/vw_imports/show.html.erb` — staging area with mapping status

### Migrations (4)
- `create_vw_imports_and_objects.rb` — core tables
- `add_unique_project_to_vw_imports.rb` — upsert support
- `add_area_and_perimeter_to_vw_objects.rb` — area_plan, area_vertical, perimeter
- `20260215000003_create_measurement_mappings.rb` — mapping tables

### Config
- `config/routes_addition.rb` — route definitions
- `db/seeds.rb` — seed runner

## Architecture

### Measurement Mapping System

Each VW class+type+pio combination maps to 8 UoM slots:
Count, Length, Width, Height, Perimeter, Area, WallArea, Volume

**Hierarchy lookup (most specific wins):**
```
"Structure-Beam-Bearer-LVL-200x45|24|"  ← exact class+type+pio
"Structure-Beam-Bearer-LVL|24|"          ← walk up class hierarchy
"Structure-Beam-Bearer|24|"
"Structure-Beam|24|"
"Structure|24|"
"*|24|"                                   ← wildcard by type
"*|24|*"                                  ← wildcard by type, any pio
```

**Mapping confidence levels:**
- REVIEWED — operator has confirmed mapping
- AUTO — exact class match found in mapping table
- AUTO* — wildcard match only (inheriting from type-level default)
- UNMAPPED — no mapping found, needs review

**Component mappings** inherit from parent and add:
- `parent.length`, `parent.height` — inherit resolved parent values
- `comp.thickness`, `comp.top_offset`, `comp.bottom_offset` — component-specific
- `calc.eff_height` — wall.height minus offsets
- `calc.comp_wall_area` — parent.length × eff_height
- `calc.comp_volume` — comp_wall_area × thickness

### Data flow
```
VectorWorks → exporter V2.6 → HTTP POST → Rails
  → vw_import_processor (stores raw data in vw_objects)
  → show action (finds mapping per class, resolves values)
  → staging view (displays resolved values with mapping status)
```

### Raw data preserved
The `raw_json` JSONB column on vw_objects stores everything the exporter sent.
Mappings read from raw_json — the resolved display values are computed at render
time, never stored. Change a mapping → all objects update instantly.