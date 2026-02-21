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

ActiveRecord::Schema[8.1].define(version: 2026_02_21_081450) do
  create_table "component_measurement_mappings", force: :cascade do |t|
    t.string "area_src"
    t.string "component_class", null: false
    t.integer "component_index", default: 0, null: false
    t.string "confidence", default: "auto"
    t.string "count_src", default: "fixed_1"
    t.datetime "created_at", null: false
    t.string "height_src"
    t.string "length_src"
    t.integer "measurement_mapping_id", null: false
    t.text "notes"
    t.string "perimeter_src"
    t.datetime "updated_at", null: false
    t.string "volume_src"
    t.string "wall_area_src"
    t.string "width_src"
    t.index ["measurement_mapping_id", "component_class", "component_index"], name: "idx_comp_mappings_parent_class_idx", unique: true
    t.index ["measurement_mapping_id"], name: "index_component_measurement_mappings_on_measurement_mapping_id"
  end

  create_table "measurement_mappings", force: :cascade do |t|
    t.string "area_src"
    t.integer "class_depth", default: 0
    t.string "class_pattern"
    t.string "confidence", default: "auto"
    t.string "count_src", default: "fixed_1"
    t.datetime "created_at", null: false
    t.string "height_src"
    t.string "length_src"
    t.string "mapping_key", null: false
    t.string "name_src"
    t.text "notes"
    t.string "perimeter_src"
    t.string "pio"
    t.datetime "updated_at", null: false
    t.string "volume_src"
    t.integer "vw_type"
    t.string "wall_area_src"
    t.string "width_src"
    t.index ["class_depth"], name: "index_measurement_mappings_on_class_depth"
    t.index ["mapping_key"], name: "index_measurement_mappings_on_mapping_key", unique: true
    t.index ["vw_type", "pio"], name: "index_measurement_mappings_on_vw_type_and_pio"
  end

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
    t.string "description"
    t.string "ifc_entity"
    t.string "iqs_uuid"
    t.string "layer"
    t.string "material"
    t.string "name"
    t.integer "perimeter"
    t.string "pio"
    t.json "raw_json", default: {}
    t.string "style_name"
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

  add_foreign_key "component_measurement_mappings", "measurement_mappings"
  add_foreign_key "vw_objects", "vw_imports"
end
