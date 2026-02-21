# app/controllers/vw_imports_controller.rb
class VwImportsController < ApplicationController
  skip_before_action :verify_authenticity_token, only: [:create]

  # GET /vw_imports
  def index
    @imports = VwImport.latest.limit(20)
  end

  # POST /vw_imports — called by V2.6 exporter from VectorWorks
  def create
    data = params.require(:vw_import).permit!.to_h
    imp  = VwImportProcessor.new(data).call

    render json: {
      id:           imp.id,
      status:       imp.status,
      object_count: imp.object_count,
      url:          vw_import_url(imp),
    }, status: :created
  rescue => e
    render json: { error: e.message }, status: :unprocessable_entity
  end

  # GET /vw_imports/:id — the staging area
  def show
    @import = VwImport.find(params[:id])

    objects = @import.vw_objects
      .where.not(zone: "annotation")
      .order(:vw_class, uvw_length: :desc)

    @annotation_count = @import.vw_objects.where(zone: "annotation").count

    # Group by class and resolve mappings
    @groups = []
    objects.group_by(&:vw_class).each do |vw_class, objs|
      sample = objs.first
      mapping = MeasurementMapping.find_mapping(vw_class, sample.vw_type, sample.pio)

      confidence = if mapping.nil?
                     "unmapped"
                   elsif mapping.confidence == "reviewed" || mapping.confidence == "manual"
                     "reviewed"
                   elsif mapping.class_pattern == "*"
                     "auto_wildcard"
                   else
                     "auto_exact"
                   end

      @groups << {
        vw_class:    vw_class,
        objects:     objs,
        mapping:     mapping,
        confidence:  confidence,
        zone:        sample.zone,
      }
    end

    # Sort: unmapped first (need attention), then auto, then reviewed
    priority = { "unmapped" => 0, "auto_wildcard" => 1, "auto_exact" => 2, "reviewed" => 3 }
    @groups.sort_by! { |g| [priority[g[:confidence]] || 99, g[:vw_class]] }

    # Summary counts
    @summary = {
      reviewed:      @groups.count { |g| g[:confidence] == "reviewed" },
      auto_exact:    @groups.count { |g| g[:confidence] == "auto_exact" },
      auto_wildcard: @groups.count { |g| g[:confidence] == "auto_wildcard" },
      unmapped:      @groups.count { |g| g[:confidence] == "unmapped" },
    }
  end
end