#!/usr/bin/env ruby
# frozen_string_literal: true

require 'fileutils'
require 'json'
require 'net/http'
require 'time'
require 'uri'

ROOT = File.expand_path(__dir__)
REPOSITORY = File.expand_path('../..', ROOT)
SOURCE_WORKFLOW = File.join(REPOSITORY, 'real/montage-cloud-local/workflow.json')
PLANNING_RESULTS = File.join(REPOSITORY, 'outputs/montage-58-seven-environments-planning.json')
WORKFLOW_NAME = 'montage-58-calibrated-real-050d'
WORKFLOW_ID = WORKFLOW_NAME
OLD_WORKFLOW_ID = 'montage-58-four-vm-local-050d'

GCP_RUNTIME = 'gcp-environment-cloud'
HPC_RUNTIME = 'plafrim-execution-slurm'
FOG_RUNTIME = 'montage-local-fog-runtime'

RESOURCE_MAPS = {
  'cloud_hetero' => {
    'scheduler-cloud_hetero-h3-standard-88-1' => 'montage-real-h3-standard-88-1',
    'scheduler-cloud_hetero-h3-standard-88-2' => 'montage-real-h3-standard-88-2',
    'scheduler-cloud_hetero-h4d-standard-192-1' => 'montage-real-c4d-standard-192-1',
    'scheduler-cloud_hetero-h4d-highmem-192-1' => 'montage-real-c4d-highmem-192-1'
  },
  'cloud_homo' => (1..4).to_h { |slot| ["scheduler-cloud_homo-h4d-standard-192-#{slot}", "montage-real-c4d-standard-192-#{slot}"] },
  'cluster_hetero' => {
    'scheduler-cluster_hetero-bora005' => 'plafrim-execution-ssh-node-bora001',
    'scheduler-cluster_hetero-bora006' => 'plafrim-execution-ssh-node-bora002',
    'scheduler-cluster_hetero-diablo01' => 'plafrim-execution-ssh-node-diablo03',
    'scheduler-cluster_hetero-diablo02' => 'plafrim-execution-ssh-node-diablo04'
  },
  'cluster_homo' => (1..4).to_h { |slot| [format('scheduler-cluster_homo-bora%03d', slot), format('plafrim-execution-ssh-node-bora%03d', slot)] },
  'hybrid_hetero' => {
    'scheduler-hybrid_hetero-bora011' => 'plafrim-execution-ssh-node-bora003',
    'scheduler-hybrid_hetero-diablo03' => 'plafrim-execution-ssh-node-diablo03',
    'scheduler-hybrid_hetero-h3-standard-88-2' => 'montage-real-h3-standard-88-2',
    'scheduler-hybrid_hetero-h4d-standard-192-7' => 'montage-real-c4d-standard-192-1'
  },
  'hybrid_homo' => {
    'scheduler-hybrid_homo-bora009' => 'plafrim-execution-ssh-node-bora001',
    'scheduler-hybrid_homo-bora010' => 'plafrim-execution-ssh-node-bora002',
    'scheduler-hybrid_homo-h4d-standard-192-5' => 'montage-real-c4d-standard-192-1',
    'scheduler-hybrid_homo-h4d-standard-192-6' => 'montage-real-c4d-standard-192-2'
  },
  'network_fog_hpc_cloud' => (1..10).to_h { |slot|
    [format('scheduler-network_fog_hpc_cloud-edge-fog-%02d', slot), format('montage-local-fog-%02d', slot)]
  }.merge(
    'scheduler-network_fog_hpc_cloud-hpc-fog-01' => 'plafrim-execution-ssh-node-bora001',
    'scheduler-network_fog_hpc_cloud-hpc-fog-02' => 'plafrim-execution-ssh-node-diablo03',
    'scheduler-network_fog_hpc_cloud-cloud-fog-01' => 'montage-real-h3-standard-88-1',
    'scheduler-network_fog_hpc_cloud-cloud-fog-02' => 'montage-real-c4d-standard-192-1'
  )
}.freeze

ENVIRONMENTS = {
  'cloud_hetero' => ['gcp-environment-v1'],
  'cloud_homo' => ['gcp-environment-v1'],
  'cluster_hetero' => ['plafrim-execution-v1'],
  'cluster_homo' => ['plafrim-execution-v1'],
  'hybrid_hetero' => ['gcp-environment-v1', 'plafrim-execution-v1'],
  'hybrid_homo' => ['gcp-environment-v1', 'plafrim-execution-v1'],
  'network_fog_hpc_cloud' => ['gcp-environment-v1', 'plafrim-execution-v1', 'montage-local-fog-execution-v1']
}.freeze

def fetch_json(path)
  base = ENV.fetch('AKOFLOW_API_URL', 'http://127.0.0.1:8080/akoflow-api')
  token = ENV.fetch('AKOFLOW_API_TOKEN')
  uri = URI.join(base.end_with?('/') ? base : base + '/', path.sub(%r{\A/}, ''))
  request = Net::HTTP::Get.new(uri)
  request['Authorization'] = "Bearer #{token}"
  response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: uri.scheme == 'https') { |http| http.request(request) }
  abort "GET #{uri} failed: #{response.code} #{response.body}" unless response.is_a?(Net::HTTPSuccess)
  JSON.parse(response.body)
end

def runtime_for(resource_id)
  return GCP_RUNTIME if resource_id.start_with?('montage-real-')
  return HPC_RUNTIME if resource_id.start_with?('plafrim-execution-')
  return FOG_RUNTIME if resource_id.start_with?('montage-local-fog-')

  abort "no runtime for #{resource_id}"
end

def link_characteristics(left, right)
  kinds = [left, right].map do |resource|
    if resource.start_with?('montage-real-') then 'cloud'
    elsif resource.start_with?('plafrim-execution-') then 'hpc'
    else 'fog'
    end
  end.sort
  case kinds
  when %w[cloud cloud] then [10_000_000_000, 0.001]
  when %w[hpc hpc] then [100_000_000_000, 0.0001]
  when %w[fog fog] then [10_000_000_000, 0.0001]
  when %w[cloud hpc] then [1_000_000_000, 0.08]
  when %w[cloud fog] then [200_000_000, 0.05]
  else [200_000_000, 0.10]
  end
end

workflow = JSON.parse(File.read(SOURCE_WORKFLOW))
workflow['name'] = WORKFLOW_NAME
File.write(File.join(ROOT, 'workflow.json'), JSON.pretty_generate(workflow) + "\n")

planning = JSON.parse(File.read(PLANNING_RESULTS))
records = planning.fetch('records').to_h do |record|
  session = record.dig('session', 'session')
  scenario = session.fetch('id').sub('montage-58-seven-env-20261001-', '')
  [scenario, record]
end

%w[scopes networks plans].each { |directory| FileUtils.mkdir_p(File.join(ROOT, directory)) }
manifest = { 'workflow' => WORKFLOW_NAME, 'generatedAt' => Time.now.utc.iso8601, 'scenarios' => [] }

RESOURCE_MAPS.each do |scenario, resource_map|
  record = records.fetch(scenario)
  session = record.dig('session', 'session')
  candidate = record.fetch('candidates').select { |item| item['algorithm'] == 'prism-time' }.min_by { |item| item.fetch('rank') }
  candidate = fetch_json("planning-sessions/#{session.fetch('id')}/candidates/#{candidate.fetch('id')}/")
  source_plan = candidate.fetch('plan')
  scope_id = "montage-real-#{scenario.tr('_', '-')}-c4d-scope-v1"
  topology_id = "montage-real-#{scenario.tr('_', '-')}-c4d-network-v1"
  plan_id = "montage-real-#{scenario.tr('_', '-')}-c4d-prism-time-v1"

  scope = {
    'id' => scope_id, 'name' => "Montage real #{scenario.tr('_', ' ')}",
    'networkTopologyId' => topology_id,
    'environmentVersionIds' => ENVIRONMENTS.fetch(scenario),
    'metadata' => {
      'scenario' => scenario, 'realExecution' => true,
      'sourcePlanningSessionId' => session.fetch('id'),
      'cloudMachineTranslation' => {'h4d-standard-192' => 'c4d-standard-192', 'h4d-highmem-192' => 'c4d-highmem-192'}
    }
  }

  resources = resource_map.values.uniq
  links = resources.combination(2).each_with_index.map do |(left, right), index|
    bandwidth, latency = link_characteristics(left, right)
    {
      'id' => format('%s-link-%03d', topology_id, index + 1),
      'sourceResourceId' => left, 'targetResourceId' => right,
      'bandwidthBitsPerSecond' => bandwidth, 'latencySeconds' => latency,
      'pricePerByte' => 0, 'bidirectional' => true
    }
  end
  topology = {'id' => topology_id, 'name' => "Montage real #{scenario.tr('_', ' ')} links", 'version' => 1, 'executionScopeId' => scope_id, 'links' => links}

  assignments = source_plan.fetch('assignments').map.with_index do |assignment, index|
    source_resource = assignment.fetch('resourceId')
    resource_id = resource_map.fetch(source_resource)
    activity_id = assignment.fetch('activityId').sub("#{OLD_WORKFLOW_ID}-", "#{WORKFLOW_ID}-")
    source_core = assignment['coreId'].to_s
    slot_id = source_core.empty? ? 'default' : source_core.sub("#{source_resource}-", '')
    translated = assignment.reject { |key, _| %w[id planId resourceId activityId coreId slotId metadata].include?(key) }
    translated.merge(
      'id' => "#{plan_id}-assignment-#{index + 1}", 'planId' => plan_id,
      'activityId' => activity_id, 'resourceId' => resource_id,
      'slotId' => slot_id,
      'metadata' => (assignment['metadata'] || {}).merge('runtimeId' => runtime_for(resource_id), 'translatedFromResourceId' => source_resource)
    )
  end
  plan = {
    'plan' => {
      'id' => plan_id, 'workflowVersionId' => "#{WORKFLOW_ID}-v1",
      'executionScopeId' => scope_id, 'networkTopologyId' => topology_id,
      'source' => 'imported', 'algorithm' => 'prism-time-translated', 'algorithmVersion' => '1',
      'objective' => 'time', 'predicted' => candidate.fetch('predicted'), 'assignments' => assignments,
      'metadata' => {
        'sourceCandidateId' => candidate.fetch('id'), 'sourcePlanningSessionId' => session.fetch('id'),
        'translatedToRealResources' => true,
        'cloudMachineTranslation' => {'h4d-standard-192' => 'c4d-standard-192', 'h4d-highmem-192' => 'c4d-highmem-192'}
      }
    }
  }

  File.write(File.join(ROOT, 'scopes', "#{scenario}.json"), JSON.pretty_generate(scope) + "\n")
  File.write(File.join(ROOT, 'networks', "#{scenario}.json"), JSON.pretty_generate(topology) + "\n")
  File.write(File.join(ROOT, 'plans', "#{scenario}.json"), JSON.pretty_generate(plan) + "\n")
  manifest['scenarios'] << {'id' => scenario, 'scopeId' => scope_id, 'networkTopologyId' => topology_id, 'planId' => plan_id, 'resources' => resources}
end

File.write(File.join(ROOT, 'manifest.json'), JSON.pretty_generate(manifest) + "\n")
puts "generated #{manifest['scenarios'].length} real scenarios for #{WORKFLOW_NAME}"
