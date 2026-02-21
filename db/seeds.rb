# db/seeds.rb
#
# Load built-in measurement mappings.
# Run with: rails db:seed
# Safe to re-run — skips existing keys.

count = MeasurementMappingSeeds.seed!
puts "Seeded #{count} measurement mappings (#{MeasurementMapping.count} total)"