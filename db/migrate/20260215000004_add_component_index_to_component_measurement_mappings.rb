# db/migrate/20260215000004_add_component_index_to_component_measurement_mappings.rb
class AddComponentIndexToComponentMeasurementMappings < ActiveRecord::Migration[7.1]
  def change
    add_column :component_measurement_mappings, :component_index, :integer, null: false, default: 0

    # Drop old unique index (class only) and add new one (class + index)
    remove_index :component_measurement_mappings,
                 name: "idx_comp_mappings_parent_class"

    add_index :component_measurement_mappings,
              [:measurement_mapping_id, :component_class, :component_index],
              unique: true,
              name: "idx_comp_mappings_parent_class_idx"
  end
end