# db/migrate/20260215000003_create_measurement_mappings.rb
class CreateMeasurementMappings < ActiveRecord::Migration[7.1]
  def change
    create_table :measurement_mappings do |t|
      t.string  :mapping_key,    null: false  # "Wall-Interior|68|" or "*|68|*"
      t.string  :class_pattern                # "Wall-Interior" or "*"
      t.integer :class_depth,    default: 0   # number of segments for specificity
      t.integer :vw_type                      # VW object type (68, 71, 83, etc)
      t.string  :pio                          # PIO name or nil

      # The 8 UoM source assignments
      t.string  :count_src,      default: "fixed_1"
      t.string  :length_src
      t.string  :width_src
      t.string  :height_src
      t.string  :perimeter_src
      t.string  :area_src
      t.string  :wall_area_src
      t.string  :volume_src

      t.string  :confidence,     default: "auto"  # auto | reviewed | manual
      t.text    :notes                             # operator notes

      t.timestamps
    end

    add_index :measurement_mappings, :mapping_key, unique: true
    add_index :measurement_mappings, [:vw_type, :pio]
    add_index :measurement_mappings, :class_depth

    create_table :component_measurement_mappings do |t|
      t.references :measurement_mapping, null: false, foreign_key: true, index: true
      t.string  :component_class, null: false  # "Component-Timber Framing"

      t.string  :count_src,      default: "fixed_1"
      t.string  :length_src
      t.string  :width_src
      t.string  :height_src
      t.string  :perimeter_src
      t.string  :area_src
      t.string  :wall_area_src
      t.string  :volume_src

      t.string  :confidence,     default: "auto"
      t.text    :notes

      t.timestamps
    end

    add_index :component_measurement_mappings,
              [:measurement_mapping_id, :component_class],
              unique: true,
              name: "idx_comp_mappings_parent_class"
  end
end