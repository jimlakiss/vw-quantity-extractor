# iQs VW → Rails Integration

## The Workflow

```
VectorWorks                    Rails
┌──────────┐    HTTP POST    ┌──────────────────┐
│ Draw     │                 │ POST /vw_imports  │
│ element  │───► Run V2.6 ──►│                   │
│          │    exporter     │ VwImportProcessor │
└──────────┘                 │ creates records   │
                             └────────┬──────────┘
                                      │
                                      ▼
                             ┌──────────────────┐
                             │ GET /vw_imports/7 │
                             │                   │
                             │ Landing Page      │
                             │ Zone 1: Matched   │
                             │ Zone 2: Unmatched │
                             └──────────────────┘
```

Draw it. Run the script. It's there.

## Setup

### 1. Rails side (one-time)

Copy these 8 files into your Rails app:

```
db/migrate/create_vw_imports_and_objects.rb   ← migration (rename with timestamp)
app/models/vw_import.rb                       ← import record
app/models/vw_object.rb                       ← individual object + zone classification
app/services/vw_import_processor.rb           ← quantity extraction from JSON payload
app/controllers/vw_imports_controller.rb      ← handles POST from VW + serves HTML pages
app/views/vw_imports/index.html.erb           ← list of all imports
app/views/vw_imports/show.html.erb            ← the two-zone landing page
config/routes_addition.rb                     ← one line to add to your routes.rb
```

Add to your `config/routes.rb`:

```ruby
resources :vw_imports, only: [:index, :show, :create]
```

Run the migration:

```bash
rails db:migrate
rails server
```

### 2. VectorWorks side

Replace `iqs_vw_exporter_V2.5.py` with `iqs_vw_exporter_V2.6.py`.

The only config is in `CFG`:

```python
"iqs_url": "http://localhost:3000/vw_imports",
```

Change this if Rails runs on a different host/port. Set to `""` to disable pushing (keeps local JSONL-only behaviour).

### 3. Use it

1. Draw something in VectorWorks
2. Run the V2.6 exporter script
3. VW dialog shows: `✓ iQs: import #7 → http://localhost:3000/vw_imports/7`
4. Click that URL — your quantities are there

If Rails isn't running, the exporter still saves JSONL locally. No breakage.

## What changed (V2.5 → V2.6)

Five patches, 48 lines changed, nothing else touched:

1. `import urllib.request, urllib.error` — stdlib HTTP, no dependencies
2. `CFG["iqs_url"]` — where to POST
3. `ST["records"]` — accumulates sanitized objects during harvest
4. In `harvest()` — collects each sanitized record
5. `iqs_push()` — POSTs the payload after file close, graceful fallback

The exporter still writes JSONL to disk exactly as before. The HTTP push is additive.

## All files (9 total)

| # | File | What it does |
|---|------|--------------|
| 1 | `iqs_vw_exporter_V2.6.py` | VW script — exports objects → writes JSONL → POSTs to Rails |
| 2 | `db/migrate/create_vw_imports_and_objects.rb` | Creates `vw_imports` and `vw_objects` tables |
| 3 | `app/models/vw_import.rb` | Import record — project name, timestamp, status, has_many objects |
| 4 | `app/models/vw_object.rb` | Individual object — dimensions, zone classification constants |
| 5 | `app/services/vw_import_processor.rb` | Receives the JSON payload, extracts quantities, bulk-inserts objects |
| 6 | `app/controllers/vw_imports_controller.rb` | One controller: `create` (POST from VW), `index` + `show` (HTML) |
| 7 | `app/views/vw_imports/index.html.erb` | Lists all imports — the project picker |
| 8 | `app/views/vw_imports/show.html.erb` | The two-zone landing page with class groupings |
| 9 | `config/routes_addition.rb` | One line to add to routes.rb |