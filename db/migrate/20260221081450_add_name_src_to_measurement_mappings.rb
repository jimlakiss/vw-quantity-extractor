class AddNameSrcToMeasurementMappings < ActiveRecord::Migration[8.1]
  def change
    add_column :measurement_mappings, :name_src, :string
  end
end
