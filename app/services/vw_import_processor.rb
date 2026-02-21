# app/services/vw_import_processor.rb
#
# Takes the JSON payload from V2.8 exporter, creates VwImport + VwObjects.
# All the quantity extraction logic lives here — single source of truth.
#
class VwImportProcessor
  def initialize(params)
    @p = params.deep_symbolize_keys
  end

  def call
    project_name = @p[:project] || "Unknown"

    # Same project? Overwrite. New project? Create.
    imp = VwImport.find_by(project: project_name)

    if imp
      imp.vw_objects.delete_all  # clear old objects
      imp.update!(
        exporter_version: @p[:exporter_version] || "2.6",
        exported_at:      @p[:exported_at],
        jsonl_path:       @p[:jsonl_path],
        status:           "processing"
      )
    else
      imp = VwImport.create!(
        project:          project_name,
        exporter_version: @p[:exporter_version] || "2.6",
        exported_at:      @p[:exported_at],
        jsonl_path:       @p[:jsonl_path],
        status:           "processing"
      )
    end

    rows = (@p[:objects] || []).map { |raw| build_row(imp.id, raw.deep_symbolize_keys) }

    VwObject.insert_all!(rows) if rows.any?

    imp.update!(object_count: rows.size, status: "ready")
    imp
  rescue => e
    imp&.update(status: "error")
    raise
  end

  private

  def build_row(import_id, r)
    uvw  = r[:uvw]      || {}
    wall = r[:wall]      || {}
    pd   = r[:pio_dims]  || {}
    d3   = (r.dig(:areas, :dims_3d) || {})
    vb   = r.dig(:areas, :vol_bbox).to_f

    cl  = r[:class].to_s.presence || "None"
    t   = r[:type]
    pio = r[:pio].to_s.presence

    l, w, h, a, v = quantities(t, pio, uvw, wall, pd, d3, vb)

    # Plan area (m²) — from VW's area_2d (rooms, slabs, roofs)
    area_plan = r.dig(:areas, :area_2d)
    area_plan = area_plan.to_f.round(4) if area_plan && area_plan.to_f > 0

    # Perimeter (mm) — from VW's perim_2d (rooms, slabs, roofs, extrude profiles)
    perimeter = r.dig(:areas, :perim_2d)
    perimeter = perimeter.to_f.round if perimeter && perimeter.to_f > 0

    # Vertical area (m²) — wall face / elevation area
    area_vert = if t == 68 && wall[:gross].to_f > 0
                  wall[:gross].to_f    # VW wall API gives us this directly
                elsif l.to_f > 0 && h.to_f > 0 && t != 71  # not roof faces
                  l.to_f * h.to_f / 1e6
                end
    area_vert = area_vert&.round(4)

    {
      vw_import_id: import_id,
      vw_class:     cl,
      layer:        r[:layer],
      vw_type:      t,
      pio:          pio,
      name:         r[:name].to_s.presence,
      description:  r[:description].to_s.presence,
      ifc_entity:   r[:ifc_entity].to_s.presence,
      style_name:   r[:style_name].to_s.presence,
      uvw_length:   l&.round,
      uvw_width:    w&.round,
      uvw_height:   h&.round,
      area:         a&.round(4),
      area_plan:    area_plan,
      area_vertical: area_vert,
      perimeter:    perimeter,
      volume:       v&.round(6),
      material:     first_material(r),
      components:   r[:components] || [],
      raw_json:     r,
      zone:         VwObject.classify_zone(cl, t, pio, vb > 0),
      iqs_uuid:     r[:iqs_uuid],
      created_at:   Time.current,
      updated_at:   Time.current,
    }
  end

  # V2.6 convention: u=length, v=height(Z), w=width — for all bbox3d objects
  def quantities(t, pio, uvw, wall, pd, d3, vb)
    case
    when t == 68  # Wall — wall_api gives correct UVW already
      l = uvw[:u];  h = uvw[:v] || wall[:height];  w = uvw[:w] || wall[:thickness]
      a = wall[:gross]
      v = (a && w && w > 0) ? a * w / 1000.0 : nil
    when pio == "FramingMember"
      l = pd[:line_len] || uvw[:u];  w = pd[:width];  h = pd[:height]
      v = pd[:vol_pio]
    when %w[Door Window].include?(pio) || pio == "WinDoor 6.0"
      w = uvw[:u];  h = uvw[:v]
      l = a = v = nil
    when pio == "Drilled Footing"
      w = pd[:dia] || uvw[:u];  h = pd[:depth] || uvw[:w]
      l = a = v = nil
    when pio == "Column2"
      w = uvw[:u];  l = uvw[:v];  h = uvw[:w]
      a = v = nil
    when [71, 83, 84].include?(t) || pio == "Slab"
      # Slab: u=length, v=Z(=slab thickness), w=width
      l = uvw[:u];  w = uvw[:w];  h = uvw[:v]
      a = (l && w) ? (l.to_f * w.to_f / 1e6) : nil
      v = vb > 0 ? vb / 1e9 : nil
    else
      # Generic: u=length, v=height(Z), w=width
      l = uvw[:u];  h = uvw[:v];  w = uvw[:w]
      a = nil
      v = vb > 0 ? vb / 1e9 : nil
    end
    [l, w, h, a, v]
  end

  def first_material(r)
    (r[:components] || []).each do |c|
      m = c[:material].to_s
      return m if m.present? && m != "0"
    end
    m = r[:material].to_s
    (m.present? && m != "0") ? m : nil
  end
end