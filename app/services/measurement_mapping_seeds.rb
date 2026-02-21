# app/services/measurement_mapping_seeds.rb
#
# Built-in default mappings that ship with iQs.
# Run once: MeasurementMappingSeeds.seed!
# Safe to re-run — skips existing keys.

class MeasurementMappingSeeds
  DEFAULTS = [
    # ── Walls (type 68) ──
    { class_pattern: "*", vw_type: 68, pio: nil,
      length_src: "wall.length", width_src: "wall.thickness", height_src: "wall.height",
      wall_area_src: "wall.gross", volume_src: "calc.gross_x_thick" },

    # ── Roof Faces (type 71) ──
    { class_pattern: "*", vw_type: 71, pio: nil,
      perimeter_src: "areas.perim_2d", area_src: "areas.area_2d" },

    # ── Slabs (type 83) ──
    { class_pattern: "*", vw_type: 83, pio: nil,
      length_src: "uvw.u", width_src: "uvw.w", height_src: "uvw.v",
      area_src: "areas.area_2d", volume_src: "areas.vol_bbox" },

    # ── Extrudes (type 24) — generic ──
    { class_pattern: "*", vw_type: 24, pio: nil,
      length_src: "uvw.u", width_src: "uvw.w", height_src: "uvw.v",
      perimeter_src: "areas.perim_2d", area_src: "areas.area_2d",
      wall_area_src: "calc.l_x_h", volume_src: "areas.vol_bbox" },

    # ── FramingMember PIO ──
    { class_pattern: "*", vw_type: 86, pio: "FramingMember",
      length_src: "pd.line_len", width_src: "pd.width", height_src: "pd.height",
      volume_src: "pd.vol_pio" },

    # ── Door PIO ──
    { class_pattern: "*", vw_type: 86, pio: "Door",
      width_src: "pd.width", height_src: "pd.height" },

    # ── Window PIO ──
    { class_pattern: "*", vw_type: 86, pio: "Window",
      width_src: "pd.width", height_src: "pd.height" },

    # ── WinDoor 6.0 PIO ──
    { class_pattern: "*", vw_type: 86, pio: "WinDoor 6.0",
      width_src: "pd.width", height_src: "pd.height" },

    # ── Space PIO (rooms) ──
    { class_pattern: "*", vw_type: 86, pio: "Space",
      perimeter_src: "areas.perim_2d", area_src: "areas.area_2d" },

    # ── Drilled Footing PIO ──
    { class_pattern: "*", vw_type: 86, pio: "Drilled Footing",
      width_src: "pd.dia", height_src: "pd.depth" },

    # ── Column2 PIO ──
    { class_pattern: "*", vw_type: 86, pio: "Column2",
      width_src: "pd.shaft_w", length_src: "pd.shaft_d", height_src: "pd.height" },

    # ── Extrude Along Path PIO ──
    { class_pattern: "*", vw_type: 86, pio: "Extrude Along Path",
      length_src: "eap.path_length", width_src: "uvw.w", height_src: "uvw.v",
      wall_area_src: "calc.l_x_h" },

    # ── Generic 3D fallback (any type with volume) ──
    { class_pattern: "*", vw_type: nil, pio: nil,
      length_src: "uvw.u", width_src: "uvw.w", height_src: "uvw.v",
      volume_src: "areas.vol_bbox" },
  ].freeze

  # Component defaults for walls
  WALL_COMPONENT_DEFAULTS = {
    length_src:    "parent.length",
    width_src:     "comp.thickness",
    height_src:    "calc.eff_height",
    wall_area_src: "calc.comp_wall_area",
    volume_src:    "calc.comp_volume",
  }.freeze

  def self.seed!
    count = 0
    DEFAULTS.each do |d|
      pio_str = d[:pio].to_s.presence || ""
      vw_type = d[:vw_type]
      type_str = vw_type ? vw_type.to_s : "*"

      key = "#{d[:class_pattern]}|#{type_str}|#{pio_str}"

      next if MeasurementMapping.exists?(mapping_key: key)

      MeasurementMapping.create!(
        mapping_key:    key,
        class_pattern:  d[:class_pattern],
        class_depth:    d[:class_pattern] == "*" ? 0 : d[:class_pattern].split("-").size,
        vw_type:        vw_type,
        pio:            d[:pio],
        count_src:      d[:count_src] || "fixed_1",
        length_src:     d[:length_src],
        width_src:      d[:width_src],
        height_src:     d[:height_src],
        perimeter_src:  d[:perimeter_src],
        area_src:       d[:area_src],
        wall_area_src:  d[:wall_area_src],
        volume_src:     d[:volume_src],
        confidence:     "auto",
      )
      count += 1
    end
    count
  end
end