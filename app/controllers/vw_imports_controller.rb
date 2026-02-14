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

  # GET /vw_imports/:id — the landing page
  def show
    @import = VwImport.find(params[:id])

    @matched = @import.matched_objects
      .order(:vw_class, uvw_length: :desc)
      .group_by(&:vw_class)

    @unmatched = @import.unmatched_objects
      .order(:vw_class, uvw_length: :desc)
      .group_by(&:vw_class)

    @annotation_count = @import.annotation_objects.count
  end
end