# db/migrate/YYYYMMDDHHMMSS_create_vw_imports_and_objects.rb
class CreateVwImportsAndObjects < ActiveRecord::Migration[7.1]
  def change
    create_table :vw_imports do |t|
      t.string   :project,           null: false
      t.string   :exporter_version,  default: "2.6"
      t.datetime :exported_at
      t.integer  :object_count,      default: 0
      t.string   :jsonl_path
      t.string   :status,            default: "received"
      t.timestamps
    end

    create_table :vw_objects do |t|
      t.references :vw_import,       null: false, foreign_key: true, index: true
      t.string   :vw_class
      t.string   :layer
      t.integer  :vw_type
      t.string   :pio
      t.integer  :uvw_length    # mm
      t.integer  :uvw_width     # mm
      t.integer  :uvw_height    # mm
      t.decimal  :area,    precision: 12, scale: 4  # m² — primary area
      t.decimal  :area_plan,     precision: 12, scale: 4  # m² — floor/roof plan area (from VW area_2d)
      t.decimal  :area_vertical, precision: 12, scale: 4  # m² — wall face / elevation area
      t.integer  :perimeter                                # mm — plan perimeter (from VW perim_2d)
      t.decimal  :volume,  precision: 12, scale: 6  # m³
      t.string   :material
      t.jsonb    :components,  default: []
      t.jsonb    :raw_json,    default: {}
      t.string   :zone,        default: "unmatched"
      t.string   :iqs_uuid
      t.timestamps
    end

    add_index :vw_objects, :vw_class
    add_index :vw_objects, :zone
    add_index :vw_imports, :project, unique: true
  end
end