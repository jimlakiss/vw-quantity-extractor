# app/models/vw_import.rb
class VwImport < ApplicationRecord
  has_many :vw_objects, dependent: :destroy

  validates :project, presence: true

  scope :latest, -> { order(created_at: :desc) }
  scope :ready,  -> { where(status: "ready") }

  def matched_objects   = vw_objects.where(zone: "matched")
  def unmatched_objects  = vw_objects.where(zone: "unmatched")
  def annotation_objects = vw_objects.where(zone: "annotation")
end