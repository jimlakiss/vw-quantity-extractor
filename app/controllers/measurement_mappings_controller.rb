# app/controllers/measurement_mappings_controller.rb
class MeasurementMappingsController < ApplicationController
  skip_before_action :verify_authenticity_token

  # POST /measurement_mappings — create or update a mapping
  def create
    key = params[:mapping_key]
    mapping = MeasurementMapping.find_or_initialize_by(mapping_key: key)

    mapping.assign_attributes(mapping_params)
    mapping.class_depth = mapping.class_pattern.to_s.split("-").size unless mapping.class_pattern == "*"

    if mapping.save
      # Save component mappings if provided
      save_component_mappings(mapping) if params[:components].present?

      render json: { ok: true, id: mapping.id, key: mapping.mapping_key }
    else
      render json: { ok: false, errors: mapping.errors.full_messages }, status: :unprocessable_entity
    end
  end

  # PATCH /measurement_mappings/:id
  def update
    mapping = MeasurementMapping.find(params[:id])
    mapping.assign_attributes(mapping_params)

    if mapping.save
      save_component_mappings(mapping) if params[:components].present?
      render json: { ok: true, id: mapping.id, key: mapping.mapping_key }
    else
      render json: { ok: false, errors: mapping.errors.full_messages }, status: :unprocessable_entity
    end
  end

  # GET /measurement_mappings/sample_values?vw_object_id=123
  def sample_values
    obj = VwObject.find(params[:vw_object_id])
    resolver = MappingResolver.new(obj, nil)
    avail = resolver.available_values

    # Also include component info if present
    comps = (obj.components || []).map do |c|
      c = c.deep_symbolize_keys rescue c
      {
        class_name: c[:class],
        thickness: c[:thickness],
        top_offset: c[:top_offset],
        bottom_offset: c[:bottom_offset],
        material: c[:material],
        function: c[:function],
      }
    end.select { |c| c[:class_name].present? }

    render json: { available: avail, components: comps, object_id: obj.id }
  end

  private

  def mapping_params
    params.permit(
      :mapping_key, :class_pattern, :vw_type, :pio, :confidence,
      :count_src, :length_src, :width_src, :height_src,
      :perimeter_src, :area_src, :wall_area_src, :volume_src, :notes
    )
  end

  def save_component_mappings(parent)
    params[:components].each do |comp_params|
      comp_params = comp_params.permit!.to_h.symbolize_keys
      next if comp_params[:component_class].blank?

      comp_idx = comp_params[:component_index].to_i

      cm = parent.component_measurement_mappings
        .find_or_initialize_by(component_class: comp_params[:component_class],
                               component_index: comp_idx)

      cm.assign_attributes(
        count_src:     comp_params[:count_src],
        length_src:    comp_params[:length_src],
        width_src:     comp_params[:width_src],
        height_src:    comp_params[:height_src],
        perimeter_src: comp_params[:perimeter_src],
        area_src:      comp_params[:area_src],
        wall_area_src: comp_params[:wall_area_src],
        volume_src:    comp_params[:volume_src],
        confidence:    "manual",
      )
      cm.save!
    end
  end
end