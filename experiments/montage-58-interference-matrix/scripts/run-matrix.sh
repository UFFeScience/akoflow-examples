#!/usr/bin/env bash
set -euo pipefail

environment_name=${1:?usage: run-matrix.sh ENVIRONMENT RESULT_DIRECTORY}
result_directory=${2:?usage: run-matrix.sh ENVIRONMENT RESULT_DIRECTORY}
repetitions=${REPETITIONS:-5}
source_image=${MONTAGE_IMAGE:-ovvesley/akoflow-wf-montage@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9}
script_directory=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
experiment_directory=$(cd "$script_directory/.." && pwd)
image=${CALIBRATION_IMAGE:-akoflow/montage-58-interference-calibration:050d}

case "$repetitions" in
  ''|*[!0-9]*) echo "REPETITIONS must be a positive integer" >&2; exit 2 ;;
  0) echo "REPETITIONS must be greater than zero" >&2; exit 2 ;;
esac

mkdir -p "$result_directory/logs"
result_directory=$(cd "$result_directory" && pwd)
runs_file="$result_directory/runs.tsv"
printf 'environment\tcase\trepetition\tworkload\tstarted_ns\tfinished_ns\tduration_seconds\texit_code\tcontainer_id\n' > "$runs_file"

{
  printf 'environment=%s\n' "$environment_name"
  printf 'captured_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  uname -a
  docker version
  docker info
} > "$result_directory/host.txt" 2>&1

if ! docker image inspect "$image" >/dev/null 2>&1; then
  docker pull "$source_image" > "$result_directory/image-pull.log"
  docker build --pull=false --build-arg "BASE_IMAGE=$source_image" \
    --platform linux/amd64 \
    --tag "$image" --file "$experiment_directory/docker/Dockerfile" \
    "$experiment_directory/docker" > "$result_directory/image-build.log"
fi
source_digest=$(docker image inspect "$source_image" --format '{{index .RepoDigests 0}}')
calibration_id=$(docker image inspect "$image" --format '{{.Id}}')
printf 'source=%s\ncalibration=%s\n' "$source_digest" "$calibration_id" > "$result_directory/image.txt"

command_for() {
  case "$1" in
    mproject-a)
      printf '%s\n' 'mProject -X poss2ukstu_blue_001_001.fits out-mproject-a.fits region-oversized.hdr'
      ;;
    mproject-b)
      printf '%s\n' 'mProject -X poss2ukstu_red_001_001.fits out-mproject-b.fits region-oversized.hdr'
      ;;
    mdifffit)
      printf '%s\n' 'mDiffFit -d -s out-mdifffit.txt pposs2ukstu_blue_001_001.fits pposs2ukstu_blue_001_002.fits out-mdifffit.fits region-oversized.hdr'
      ;;
    *) echo "unknown workload: $1" >&2; return 2 ;;
  esac
}

record_container() {
  local case_id=$1 repetition=$2 workload=$3 container=$4 log=$5 timing_file=$6
  local status started finished duration
  docker logs "$container" > "$log" 2>&1 || true
  status=$(docker inspect "$container" --format '{{.State.ExitCode}}')
  read -r started finished < "$timing_file"
  duration=$(awk -v start="$started" -v finish="$finished" 'BEGIN { printf "%.9f", (finish-start)/1000000000 }')
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$environment_name" "$case_id" "$repetition" "$workload" \
    "$started" "$finished" "$duration" "$status" "$container" >> "$runs_file"
  if [ "$status" -ne 0 ]; then
    echo "$case_id repetition $repetition workload $workload failed; see $log" >&2
    return 1
  fi
}

run_case() {
  local case_id=$1 repetition=$2
  shift 2
  local containers=() workloads=() timing_files=() workload command wrapped container index=0 timing_directory timing_file
  for workload in "$@"; do
    index=$((index + 1))
    command=$(command_for "$workload")
    timing_directory="$result_directory/.timing/${case_id}-r${repetition}-${workload}"
    mkdir -p "$timing_directory"
    timing_file="$timing_directory/timing"
    wrapped="started=\$(date +%s%N); set +e; $command; status=\$?; set -e; finished=\$(date +%s%N); printf '%s %s\\n' \"\$started\" \"\$finished\" > /akoflow-results/timing; exit \"\$status\""
    container=$(docker create --platform linux/amd64 --cpus=1 --memory=1536m \
      --mount "type=bind,source=$timing_directory,target=/akoflow-results" \
      --workdir /akoflow-wfa-shared "$image" sh -c "$wrapped")
    containers+=("$container")
    workloads+=("$workload")
    timing_files+=("$timing_file")
  done

  cleanup() { docker rm -f "${containers[@]}" >/dev/null 2>&1 || true; }
  trap cleanup RETURN

  local pids=() failed=0
  for container in "${containers[@]}"; do
    docker start -a "$container" >/dev/null 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    wait "$pid" || failed=1
  done

  for ((index=0; index<${#containers[@]}; index++)); do
    record_container "$case_id" "$repetition" "${workloads[$index]}" \
      "${containers[$index]}" \
      "$result_directory/logs/${case_id}-r${repetition}-${workloads[$index]}.log" \
      "${timing_files[$index]}" || failed=1
  done
  return "$failed"
}

for repetition in $(seq 1 "$repetitions"); do
  run_case mproject-a-alone "$repetition" mproject-a
  run_case mproject-b-alone "$repetition" mproject-b
  run_case mdifffit-alone "$repetition" mdifffit
  run_case mproject-with-mproject "$repetition" mproject-a mproject-b
  run_case mproject-with-mdifffit "$repetition" mproject-a mdifffit
done

awk -F '\t' 'BEGIN { OFS="\t" }
  NR > 1 { key=$1 FS $2 FS $4; count[key]++; total[key]+=$7 }
  END {
    print "environment","case","workload","samples","mean_seconds","baseline_case","baseline_mean_seconds","slowdown"
    for (key in count) mean[key]=total[key]/count[key]
    for (key in count) {
      split(key, part, FS)
      baseline_case=part[3] "-alone"
      baseline_key=part[1] FS baseline_case FS part[3]
      baseline=(baseline_key in mean) ? mean[baseline_key] : mean[key]
      print part[1],part[2],part[3],count[key],mean[key],baseline_case,baseline,mean[key]/baseline
    }
  }' "$runs_file" > "$result_directory/summary.tsv"

echo "Matrix completed: $result_directory"
