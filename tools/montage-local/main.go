// Command montage-local derives a local-only bundle from the original 050d workflow.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	if err := generate("."); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func generate(root string) error {
	raw, err := os.ReadFile(filepath.Join(root, "real/montage-cloud-local/workflow.json"))
	if err != nil {
		return err
	}
	var original map[string]any
	if err := json.Unmarshal(raw, &original); err != nil {
		return err
	}
	spec := original["spec"].(map[string]any)
	upstream := spec["image"].(string)
	if upstream != "ovvesley/akoflow-wf-montage@sha256:26b060b83b990557ea86ab40503cc8f17ab6016b5973e7e6f9201100a96440c9" {
		return fmt.Errorf("unexpected upstream Montage image; review the 050d contract")
	}
	stages := []string{}
	dependencies := map[string][]string{}
	activities := spec["activities"].([]any)
	if len(activities) != 58 {
		return fmt.Errorf("Montage must preserve all 58 activities")
	}
	for _, value := range activities {
		activity := value.(map[string]any)
		name := activity["name"].(string)
		run := activity["run"].(string)
		if strings.ContainsAny(run, "'\";|&<>$`\\") {
			return fmt.Errorf("command requires an explicit structured conversion: %s", name)
		}
		args := strings.Fields(run)
		if len(args) == 0 {
			return fmt.Errorf("empty Montage command")
		}
		activity["command"] = map[string]any{"entrypoint": args[0], "arguments": args[1:]}
		delete(activity, "run")
		activity["runtime"] = "montage-050-local-local"
		activity["memoryLimit"] = "1Gi"
		stages = append(stages, name)
		parents := []string{}
		for _, parent := range activity["dependsOn"].([]any) {
			parents = append(parents, parent.(string))
		}
		dependencies[name] = parents
	}
	original["name"] = "montage-050-local"
	spec["image"] = "ghcr.io/uffescience/akoflow-examples/montage-050-local:v1"
	artifacts := []string{"1-mosaic.fits", "2-mosaic.fits", "3-mosaic.fits", "1-mosaic.png", "2-mosaic.png", "3-mosaic.png", "mosaic-color.png"}
	profile := "Run all 58 original Montage 050d activities locally, using the immutable amd64 image and its twelve bundled FITS observations. The default uses two CPU slots, preserves the 138 named file handoffs, creates three calibrated astronomical mosaics and a color preview, and provisions no cloud machines. This is a long-running scientific workload; on Apple Silicon Docker uses amd64 emulation."
	bundle := filepath.Join(root, "scientific-workflows/montage-050")
	for _, dir := range []string{"data", "docker", "expected"} {
		if err := os.MkdirAll(filepath.Join(bundle, dir), 0755); err != nil {
			return err
		}
	}
	var buffer bytes.Buffer
	encoder := yaml.NewEncoder(&buffer)
	encoder.SetIndent(2)
	if err := encoder.Encode(original); err != nil {
		return err
	}
	encoder.Close()
	if err := os.WriteFile(filepath.Join(bundle, "workflow.yaml"), buffer.Bytes(), 0644); err != nil {
		return err
	}
	config := map[string]any{"slug": "montage-050-local", "title": "Montage 050 locally", "stages": stages, "dependencies": dependencies, "artifacts": artifacts, "validationMode": "local-workload", "localProfile": profile, "ciValidation": "image-and-contract", "upstreamImage": upstream}
	for filename, value := range map[string]any{"data/input.json": config, "expected/manifest.json": map[string]any{"showcase": "montage-050-local", "status": "success", "artifacts": artifacts}} {
		data, err := json.MarshalIndent(value, "", "  ")
		if err != nil {
			return err
		}
		if err := os.WriteFile(filepath.Join(bundle, filename), append(data, '\n'), 0644); err != nil {
			return err
		}
	}
	files := map[string]string{
		"docker/Dockerfile": "FROM --platform=linux/amd64 " + upstream + "\n",
		".gitignore":        "/outputs/\n.venv/\n",
		"prepare.sh": `#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v go >/dev/null
command -v docker >/dev/null
go -C "$root/../.." mod download
go run "$root/../../tools/showcase/main.go" -root "$root" -prepare-container
`,
		"run.sh": `#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/showcase/main.go" -root "$root" -container -parallel 2
"$root/validate.sh"
`,
		"validate.sh": `#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
go run "$root/../../tools/montage-check/main.go" -root "$root" "$@"
`,
		"README.md": "# Montage 050 locally\n\n" + profile + `\n
## Run locally

Install Go and Docker with linux/amd64 support. Keep at least 15 GiB of free disk for the image and intermediate workspaces; the exact peak depends on artifact retention and concurrency. The image already contains the 87 MiB input dataset, headers, tables, and Montage executables.

` + "```sh\ngit clone https://github.com/UFFeScience/akoflow-examples.git\ncd akoflow-examples/scientific-workflows/montage-050\n./prepare.sh && ./run.sh\n```\n" + `
Preparation downloads the Go YAML module and the pinned image. Activities run with network access disabled. The local runner copies the image's input seed once, executes native Montage commands as soon as their dependencies and a CPU slot are available, and publishes a successful manifest only after every activity and final file passes validation. No activity is replaced with a simulation or omitted.

Outputs are in ` + "`outputs/`" + `: three FITS mosaics, three monochrome previews, the color preview, per-activity observations, and a manifest with SHA-256 digests. The validator checks FITS image dimensions and decodes the PNG headers.

## Run through the local daemon and Desktop

With your local AkôFlow daemon running and ` + "`AKOFLOW_API_TOKEN`" + ` configured in the shell, run from this bundle:

` + "```sh\ngo run ../../tools/daemon-local -root ../.. -example scientific-workflows/montage-050 -wait=false\n```\n" + `
This builds the same pinned image, validates the daemon's Docker connection, registers a local-only environment and the full 58-activity DAG, and submits a real run. It prints the run ID and leaves the daemon responsible for execution. Open that run in Desktop to inspect progress or cancel it. The local environment allows two simultaneous activities. No GCP credentials, VMs, Kubernetes cluster, or remote HPC account are used.

## Provenance

Derived from ` + "`real/montage-cloud-local/workflow.json`" + `. The native commands, twelve source FITS files, 58 activity names, dependency graph, and 138 file handoffs are preserved. Historical ` + "`simulation.durationSeconds`" + ` values in the source describe a different CPU; they are planning references, not measurements of this local run. The immutable upstream image is:

` + "```text\n" + upstream + "\n```\n",
	}
	for filename, text := range files {
		mode := os.FileMode(0644)
		if strings.HasSuffix(filename, ".sh") {
			mode = 0755
		}
		if err := os.WriteFile(filepath.Join(bundle, filename), []byte(strings.ReplaceAll(text, "\\n\n", "\n\n")), mode); err != nil {
			return err
		}
	}
	return nil
}
