class AddNameDescriptionToVwObjects < ActiveRecord::Migration[8.1]
  def change
    add_column :vw_objects, :name, :string
    add_column :vw_objects, :description, :string
    add_column :vw_objects, :ifc_entity, :string
    add_column :vw_objects, :style_name, :string
  end
end
