# db/migrate/YYYYMMDDHHMMSS_add_unique_project_to_vw_imports.rb
#
# Run this if you've already migrated the original.
# If starting fresh, the main migration already includes it.

class AddUniqueProjectToVwImports < ActiveRecord::Migration[7.1]
  def change
    add_index :vw_imports, :project, unique: true
  end
end