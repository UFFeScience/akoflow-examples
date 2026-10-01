#!/usr/bin/env ruby
# frozen_string_literal: true

require 'csv'
require 'json'

abort 'usage: build-calibration.rb OUTPUT.json RUNS.tsv [RUNS.tsv ...]' if ARGV.length < 2

output = ARGV.shift
rows = ARGV.flat_map do |path|
  CSV.read(path, headers: true, col_sep: "\t").map(&:to_h)
end

def median(values)
  sorted = values.map(&:to_f).sort
  abort 'cannot calculate a median without samples' if sorted.empty?
  middle = sorted.length / 2
  sorted.length.odd? ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2.0
end

def samples(rows, environment, case_id, workload)
  rows.each_with_object([]) do |row, values|
    next unless row['environment'] == environment && row['case'] == case_id && row['workload'] == workload
    next unless row['exit_code'].to_i.zero?

    values << row['duration_seconds'].to_f
  end
end

environments = rows.map { |row| row.fetch('environment') }.uniq.sort
calibrations = environments.map do |environment|
  baselines = {
    'mproject-a' => median(samples(rows, environment, 'mproject-a-alone', 'mproject-a')),
    'mproject-b' => median(samples(rows, environment, 'mproject-b-alone', 'mproject-b')),
    'mdifffit' => median(samples(rows, environment, 'mdifffit-alone', 'mdifffit'))
  }

  same_family = %w[mproject-a mproject-b].flat_map do |workload|
    samples(rows, environment, 'mproject-with-mproject', workload).map { |value| value / baselines.fetch(workload) }
  end
  mproject_with_mdifffit = samples(rows, environment, 'mproject-with-mdifffit', 'mproject-a')
  mdifffit_with_mproject = samples(rows, environment, 'mproject-with-mdifffit', 'mdifffit')

  {
    'environmentId' => environment,
    'baselineMedianSeconds' => baselines,
    'directedSlowdowns' => [
      {
        'affectedWorkload' => 'mproject',
        'interferingWorkload' => 'mproject',
        'slowdownFactor' => median(same_family),
        'samples' => same_family.length
      },
      {
        'affectedWorkload' => 'mproject',
        'interferingWorkload' => 'mdifffit',
        'slowdownFactor' => median(mproject_with_mdifffit.map { |value| value / baselines.fetch('mproject-a') }),
        'samples' => mproject_with_mdifffit.length
      },
      {
        'affectedWorkload' => 'mdifffit',
        'interferingWorkload' => 'mproject',
        'slowdownFactor' => median(mdifffit_with_mproject.map { |value| value / baselines.fetch('mdifffit') }),
        'samples' => mdifffit_with_mproject.length
      }
    ]
  }
end

document = {
  'schemaVersion' => '1',
  'kind' => 'akoflow-interference-calibration',
  'model' => 'pairwise-slowdown',
  'aggregation' => 'additive-excess',
  'calibrations' => calibrations
}

File.write(output, JSON.pretty_generate(document) + "\n")
puts "Wrote #{output} with #{calibrations.length} environment calibration(s)"
