# app/services/mapping_resolver.rb
#
# Given a VwObject and a MeasurementMapping, resolves the source field
# references to actual numeric values.
#
# Usage:
#   mapping = MeasurementMapping.find_mapping(obj.vw_class, obj.vw_type, obj.pio)
#   resolved = MappingResolver.new(obj, mapping).resolve
#   # => { count: 1, length: 4301, width: 90, height: 2450, ... }
#
#   # For a component:
#   comp_mapping = mapping.component_measurement_mappings.find_by(component_class: "Component-Timber Framing")
#   comp_resolved = MappingResolver.new(obj, comp_mapping, component: comp_data, parent_resolved: resolved).resolve
#

class MappingResolver
  UOM_FIELDS = %i[count length width height perimeter area wall_area volume].freeze

  def initialize(obj, mapping, component: nil, parent_resolved: nil)
    @obj = obj
    @mapping = mapping
    @comp = component&.deep_symbolize_keys
    @parent = parent_resolved || {}
    @raw = (obj.raw_json || {}).deep_symbolize_keys
    @resolving = Set.new  # Recursion guard — prevents stack overflow when calc fields reference other calc-dependent sources
  end

  def resolve
    return {} unless @mapping

    result = {}
    UOM_FIELDS.each do |field|
      src = @mapping.send("#{field}_src")
      result[field] = resolve_source(src)
    end
    result
  end

  # Dynamically walk the entire raw_json and surface every numeric value
  # as a dot-notation key. No hardcoding — anything the extractor provides
  # automatically appears in the mapping dropdowns.
  AVAIL_EXCLUDE = %w[components records user_fields classes_used].freeze

  def available_values
    avail = {}
    filtered = @raw.reject { |k, _| AVAIL_EXCLUDE.include?(k.to_s) }
    flatten_hash(filtered, "", avail)

    # Strip nils, zeros, and non-numeric values (we only map numbers)
    avail.compact!
    avail.reject! { |_k, v| !v.is_a?(Numeric) || v == 0 }
    avail
  end

  private

  # Recursively flatten a hash into dot-notation keys
  # e.g. { wall: { length: 6125 } } → { "wall.length" => 6125 }
  def flatten_hash(obj, prefix, result)
    case obj
    when Hash
      obj.each do |k, v|
        key = prefix.empty? ? k.to_s : "#{prefix}.#{k}"
        flatten_hash(v, key, result)
      end
    when Array
      obj.each_with_index do |v, i|
        key = "#{prefix}[#{i}]"
        if v.is_a?(Numeric)
          result[key] = v
        elsif v.is_a?(Hash) || v.is_a?(Array)
          flatten_hash(v, key, result)
        end
      end
    when Numeric
      result[prefix] = obj
    end
  end

  # Recursion guard: if src is already being resolved up the call stack,
  # return nil to break the cycle. Never remove or weaken this guard —
  # it prevents SystemStackError when calc fields reference other
  # calc-dependent dimension sources (e.g. volume_src = calc.l_x_w_x_h
  # which reads length_src, and length_src is itself a calc.*).
  def resolve_source(src)
    return nil if src.blank? || src == "null"
    return 1   if src == "fixed_1"
    return nil if @resolving.include?(src)  # cycle detected → nil

    @resolving.add(src)
    result = resolve_source_inner(src)
    @resolving.delete(src)
    result
  end

  def resolve_source_inner(src)
    # Parent inherit (for components)
    if src.start_with?("parent.")
      field = src.sub("parent.", "").to_sym
      return @parent[field]
    end

    # Component fields
    if src.start_with?("comp.") && @comp
      key = src.sub("comp.", "").to_sym
      return @comp[key]&.to_f
    end

    # Calculated fields
    if src.start_with?("calc.")
      return resolve_calc(src)
    end

    # Raw field lookup
    resolve_raw(src)
  end

  # Generic dot-notation lookup into raw_json
  # Handles: "wall.length", "areas.dims_3d.d1", "areas.raw_3d[0]", "probe.HLength"
  def resolve_raw(src)
    current = @raw
    parts = src.split(".")

    parts.each do |part|
      return nil if current.nil?

      # Handle array index notation: "raw_3d[0]"
      if part =~ /^(.+)\[(\d+)\]$/
        key = $1.to_sym
        idx = $2.to_i
        current = current.is_a?(Hash) ? current[key] : nil
        current = current.is_a?(Array) ? current[idx] : nil
      else
        current = current.is_a?(Hash) ? current[part.to_sym] : nil
      end
    end

    current.is_a?(Numeric) ? current : nil
  end

  def resolve_calc(src)
    l = resolve_source(@mapping.try(:length_src))
    w = resolve_source(@mapping.try(:width_src))
    h = resolve_source(@mapping.try(:height_src))

    case src
    when "calc.l_x_h"
      (l && h) ? (l.to_f * h.to_f / 1e6) : nil
    when "calc.l_x_w"
      (l && w) ? (l.to_f * w.to_f / 1e6) : nil
    when "calc.l_x_w_x_h"
      (l && w && h) ? (l.to_f * w.to_f * h.to_f / 1e9) : nil
    when "calc.perim_x_h"
      p = resolve_source(@mapping.try(:perimeter_src))
      (p && h) ? (p.to_f * h.to_f / 1e6) : nil
    when "calc.circumference"
      w ? (w.to_f * Math::PI) : nil
    when "calc.curved_area"
      circ = w ? (w.to_f * Math::PI) : nil
      (circ && h) ? (circ * h.to_f / 1e6) : nil
    when "calc.circle_area"
      w ? (Math::PI / 4.0 * w.to_f ** 2 / 1e6) : nil
    when "calc.circle_vol"
      a = w ? (Math::PI / 4.0 * w.to_f ** 2) : nil
      (a && h) ? (a * h.to_f / 1e9) : nil
    when "calc.gross_x_thick"
      g = resolve_raw("wall.gross")
      t = resolve_raw("wall.thickness")
      (g && t) ? (g.to_f * t.to_f / 1000.0) : nil
    when "calc.area_x_thick"
      a = resolve_source(@mapping.try(:area_src)) || @parent[:area]
      thick = @comp ? @comp.dig(:thickness)&.to_f : w&.to_f
      (a && thick && thick > 0) ? (a.to_f * thick / 1000.0) : nil
    when "calc.eff_height"
      # V2.8: prefer direct eff_height_mm from extractor (net_area / length)
      direct_h = @comp&.dig(:eff_height_mm)&.to_f
      return direct_h if direct_h && direct_h > 0

      wall_h = @parent[:height] ||
               resolve_raw("wall.overall_height_mm") ||
               resolve_raw("wall.height") ||
               resolve_raw("areas.raw_3d[2]") ||
               resolve_raw("uvw.v") ||
               resolve_raw("pio_dims.height")
      # VW offsets are SIGNED: top_offset=-200 means 200mm shorter from top
      # So effective height = wall_h + top_offset - bottom_offset
      top = @comp&.dig(:top_offset).to_f    # negative = shorter
      bot = @comp&.dig(:bottom_offset).to_f  # positive = shorter
      wall_h ? (wall_h.to_f + top - bot) : nil
    when "calc.comp_wall_area"
      # V2.12: prefer offset-adjusted area for slabs/roofs (edge offset geometry)
      # Then fall back to net_area (VW API, handles wall openings + peaks)
      direct_a = @comp&.dig(:offset_area_m2)&.to_f
      direct_a = @comp&.dig(:net_area_m2)&.to_f unless direct_a && direct_a > 0
      return direct_a if direct_a && direct_a > 0

      parent_l = @parent[:length] ||
                 resolve_raw("wall.length_mm") ||
                 resolve_raw("wall.length") ||
                 resolve_raw("wall.length_pts") ||
                 resolve_raw("areas.len_2d") ||
                 resolve_raw("uvw.u") ||
                 resolve_raw("eap.path_length") ||
                 resolve_raw("areas.dims_3d.d1") ||
                 resolve_raw("areas.raw_3d[1]")
      eff_h = resolve_calc("calc.eff_height")
      (parent_l && eff_h) ? (parent_l.to_f * eff_h.to_f / 1e6) : nil
    when "calc.comp_volume"
      # V2.12: prefer offset-adjusted volume, then VW API volume
      direct_v = @comp&.dig(:offset_volume_m3)&.to_f
      direct_v = @comp&.dig(:net_volume_m3)&.to_f unless direct_v && direct_v > 0
      return direct_v if direct_v && direct_v > 0

      comp_area = resolve_calc("calc.comp_wall_area")
      thick = @comp&.dig(:thickness).to_f
      (comp_area && thick > 0) ? (comp_area.to_f * thick / 1000.0) : nil
    end
  end
end