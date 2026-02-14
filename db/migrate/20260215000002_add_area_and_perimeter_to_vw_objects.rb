# db/migrate/YYYYMMDDHHMMSS_add_area_and_perimeter_to_vw_objects.rb
#
# Adds plan area, perimeter, and vertical area columns.
# Separates: area (plan/floor) vs area_vertical (wall face / elevation area)

class AddAreaAndPerimeterToVwObjects < ActiveRecord::Migration[7.1]
  def change
    add_column :vw_objects, :area_plan,     :decimal, precision: 12, scale: 4  # m² — floor/roof plan area
    add_column :vw_objects, :area_vertical, :decimal, precision: 12, scale: 4  # m² — wall face / elevation area
    add_column :vw_objects, :perimeter,     :integer                            # mm — plan perimeter

    # Rename existing 'area' to clarify it's the primary area (whichever is most relevant)
    # Actually, keep 'area' as-is for backwards compat — it stays as the "main" area
    # area_plan and area_vertical are the new explicit ones
  end
end