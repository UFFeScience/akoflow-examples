#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'

abort 'usage: materialize-matrix.rb CALIBRATION.json ENVIRONMENT_ID WORKFLOW.json OUTPUT.json' unless ARGV.length == 4

calibration_path, environment_id, workflow_path, output_path = ARGV
calibration = JSON.parse(File.read(calibration_path))
workflow = JSON.parse(File.read(workflow_path))
selected = calibration.fetch('calibrations').find { |entry| entry.fetch('environmentId') == environment_id }
abort "calibration not found for #{environment_id}" unless selected

activities = workflow.dig('spec', 'activities') || workflow.dig('version', 'activities') || workflow['activities']
abort 'workflow activities were not found' unless activities.is_a?(Array)

workflow_id = workflow['id'] || workflow['name'] || workflow.dig('workflow', 'id')
abort 'workflow id or name was not found' if workflow_id.to_s.empty?

slug = lambda do |value|
  value.to_s.downcase.each_char.select { |character| character.match?(/[a-z0-9-]/) }.join.gsub(/^-|-$/, '')
end

normalized = activities.map do |activity|
  name = activity['name'] || activity['externalId'] || activity['id']
  id = activity['id'] || "#{slug.call(workflow_id)}-#{slug.call(name)}"
  family = case name.to_s.downcase
           when /mproject/ then 'mproject'
           when /mdifffit/ then 'mdifffit'
           end
  { 'id' => id, 'family' => family }
end.select { |activity| activity['family'] }

slowdowns = selected.fetch('directedSlowdowns').to_h do |entry|
  [[entry.fetch('affectedWorkload'), entry.fetch('interferingWorkload')], entry.fetch('slowdownFactor')]
end

entries = normalized.product(normalized).each_with_object([]) do |(affected, interfering), result|
  next if affected['id'] == interfering['id']
  factor = slowdowns[[affected['family'], interfering['family']]]
  next unless factor

  result << {
    'affectedActivityId' => affected['id'],
    'interferingActivityId' => interfering['id'],
    'slowdownFactor' => factor
  }
end

matrix = {
  'schemaVersion' => '4',
  'model' => 'pairwise-slowdown',
  'aggregation' => 'additive-excess',
  'entries' => entries
}

File.write(output_path, JSON.pretty_generate(matrix) + "\n")
puts "Wrote #{output_path} with #{entries.length} directed pair(s)"
