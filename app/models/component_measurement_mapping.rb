# app/models/component_measurement_mapping.rb
class ComponentMeasurementMapping < ApplicationRecord
  belongs_to :measurement_mapping

  validates :component_class, presence: true
  validates :component_class, uniqueness: { scope: [:measurement_mapping_id, :component_index] }
  validates :component_index, presence: true
end