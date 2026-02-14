# app/models/vw_object.rb
class VwObject < ApplicationRecord
  belongs_to :vw_import

  scope :construction,  -> { where(zone: %w[matched unmatched]) }
  scope :matched,       -> { where(zone: "matched") }
  scope :unmatched,     -> { where(zone: "unmatched") }
  scope :annotation,    -> { where(zone: "annotation") }

  NON_CONSTRUCTION_PATTERNS = %w[
    PDF_ Z_SURVEY TEXT2 TEXT3 TEXT5 TEXT7 TOPO BDY BOUNDARY EASEMENT
    Shadow HATCH VE-TREE TREE Label- NonPlot CR-BDY DTM Survey-
    STAKE Dimension Guides DEFPOINTS U-COM U-ELE U-SEW U-WAT U-GAS
    DR-UG BROAD LEVEL Template Title\ Block Hyperlink Stake\ Object
    Site-Boundary Site-Cars PLANTINGS Setbacks RD-KERB KERB
    LS-FENCE LS-GARDEN LS-RW HS-CONC ST-ANCI ST-OPEN Section\ Style
  ].freeze

  CONSTRUCTION_KEYWORDS = %w[
    wall slab roof beam column footing foundation steel concrete
    timber brick floor ceiling cladding gutter fascia rafter finish
    structure component tile decking screed paving retaining handrail
    door window stair demolition demo insulation membrane batten
    cabinet joinery stormwater pipe
    skirting cornice architrave moulding trim scotia quad
    soffit eave bargeboard flashing weatherboard
    lintel bearer joist purlin truss bracing nogging
    plaster render paint waterproof damp
    space room
  ].freeze

  CONSTRUCTION_PIOS = %w[
    FramingMember Door Window WinDoor\ 6.0 Slab Drilled\ Footing
    Column2 Custom\ Stair Stairs\ CW Handrails\ 2
    Extrude\ Along\ Path Space
  ].freeze

  # Classify this object into a zone
  def self.classify_zone(vw_class, vw_type, pio, has_volume)
    return "annotation" if NON_CONSTRUCTION_PATTERNS.any? { |p| vw_class.to_s.include?(p) }

    cl_down = vw_class.to_s.downcase
    return "matched" if CONSTRUCTION_KEYWORDS.any? { |k| cl_down.include?(k) }

    has_3d = has_volume || [68, 71, 83, 84].include?(vw_type) || CONSTRUCTION_PIOS.include?(pio.to_s)
    return "unmatched" if has_3d

    "annotation"
  end
end