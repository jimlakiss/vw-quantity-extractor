# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2026_02_15_000002) do
  create_table "vw_imports", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.datetime "exported_at"
    t.string "exporter_version", default: "2.6"
    t.string "jsonl_path"
    t.integer "object_count", default: 0
    t.string "project", null: false
    t.string "status", default: "received"
    t.datetime "updated_at", null: false
    t.index ["project"], name: "index_vw_imports_on_project", unique: true
  end

  create_table "vw_objects", force: :cascade do |t|
    t.decimal "area", precision: 12, scale: 4
    t.decimal "area_plan", precision: 12, scale: 4
    t.decimal "area_vertical", precision: 12, scale: 4
    t.json "components", default: []
    t.datetime "created_at", null: false
    t.string "iqs_uuid"
    t.string "layer"
    t.string "material"
    t.integer "perimeter"
    t.string "pio"
    t.json "raw_json", default: {}
    t.datetime "updated_at", null: false
    t.integer "uvw_height"
    t.integer "uvw_length"
    t.integer "uvw_width"
    t.decimal "volume", precision: 12, scale: 6
    t.string "vw_class"
    t.integer "vw_import_id", null: false
    t.integer "vw_type"
    t.string "zone", default: "unmatched"
    t.index ["vw_class"], name: "index_vw_objects_on_vw_class"
    t.index ["vw_import_id"], name: "index_vw_objects_on_vw_import_id"
    t.index ["zone"], name: "index_vw_objects_on_zone"
  end

  add_foreign_key "vw_objects", "vw_imports"
end
