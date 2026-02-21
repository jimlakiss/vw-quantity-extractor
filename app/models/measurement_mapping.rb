# app/models/measurement_mapping.rb
class MeasurementMapping < ApplicationRecord
  has_many :component_measurement_mappings, dependent: :destroy

  validates :mapping_key, presence: true, uniqueness: true

  # ── Source field palette ──
  # Every possible raw measurement an object can have.
  # These appear in the mapping panel dropdowns.

  PARENT_SOURCES = {
    "Dimensions" => %w[uvw.u uvw.v uvw.w],
    "Wall API" => %w[wall.length wall.height wall.thickness wall.gross wall.net wall.length_pts],
    "PIO Dims" => %w[pd.line_len pd.width pd.height pd.depth pd.dia pd.vol_pio pd.shaft_w pd.shaft_d],
    "Areas" => %w[areas.area_2d areas.perim_2d areas.vol_bbox],
    "EAP" => %w[eap.path_length],
    "3D Raw" => %w[raw3d.x raw3d.y raw3d.z],
    "3D Sorted" => %w[dims3d.d1 dims3d.d2 dims3d.d3],
    "Calculated" => %w[calc.l_x_h calc.l_x_w calc.l_x_w_x_h calc.perim_x_h calc.gross_x_thick calc.area_x_thick],
    "Circular Geometry" => %w[calc.circumference calc.curved_area calc.circle_area calc.circle_vol],
    "Fixed" => %w[fixed_1 null],
  }.freeze

  COMPONENT_SOURCES = {
    "Component" => %w[comp.thickness comp.top_offset comp.bottom_offset],
    "Parent Inherit" => %w[parent.length parent.width parent.height parent.perimeter],
    "Comp Calculated" => %w[calc.eff_height calc.comp_wall_area calc.comp_volume],
  }.freeze

  ALL_SOURCES = PARENT_SOURCES.values.flatten + COMPONENT_SOURCES.values.flatten

  # ── Hierarchy lookup ──
  # Walks up the class hierarchy, then falls through to wildcards.
  #
  #   find_mapping("Structure-Beam-Bearer-LVL-200x45", 24, nil)
  #   tries: "Structure-Beam-Bearer-LVL-200x45|24|"
  #          "Structure-Beam-Bearer-LVL|24|"
  #          "Structure-Beam-Bearer|24|"
  #          "Structure-Beam|24|"
  #          "Structure|24|"
  #          "*|24|"
  #          "*|24|*"
  #
  def self.find_mapping(vw_class, vw_type, pio)
    pio_str = pio.to_s.presence || ""
    parts = vw_class.to_s.split("-")

    # Exact → walk up hierarchy
    parts.length.downto(1) do |depth|
      pattern = parts[0...depth].join("-")
      found = find_by(mapping_key: "#{pattern}|#{vw_type}|#{pio_str}")
      return found if found
    end

    # Wildcard: any class, this type + pio
    found = find_by(mapping_key: "*|#{vw_type}|#{pio_str}")
    return found if found

    # Wildcard: any class, this type, any pio
    find_by(mapping_key: "*|#{vw_type}|*")
  end

  # ── Build mapping key ──
  def self.build_key(class_pattern, vw_type, pio)
    "#{class_pattern}|#{vw_type}|#{pio.to_s.presence || ''}"
  end
end