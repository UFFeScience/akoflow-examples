package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

func put(path string, data []byte, mode os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, mode)
}
func encode(path string, v any) error {
	raw, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	return put(path, append(raw, '\n'), 0644)
}
func main() {
	root := flag.String("root", ".", "examples checkout")
	flag.Parse()
	for _, variant := range []string{"local", "kind"} {
		if err := generate(*root, variant); err != nil {
			panic(err)
		}
	}
	if err := montage(*root); err != nil {
		panic(err)
	}
}
func generate(root, variant string) error {
	slug := "hybrid-" + variant + "-cloud-profile"
	relative := "connections/" + slug
	dir := filepath.Join(root, relative)
	original := "real/hybrid-cloud-transfer/" + variant + "-cloud-workflow.yaml"
	raw, err := os.ReadFile(filepath.Join(root, original))
	if err != nil {
		return err
	}
	var workflow map[string]any
	if err = yaml.Unmarshal(raw, &workflow); err != nil {
		return err
	}
	prefix := "showcase-" + slug
	workflow["name"] = prefix
	spec := workflow["spec"].(map[string]any)
	for _, item := range spec["activities"].([]any) {
		a := item.(map[string]any)
		name := a["name"].(string)
		script := a["run"].(string)
		marker, _ := json.Marshal(map[string]any{"name": name, "status": "completed"})
		script += "\nprintf '%s\\n' '" + string(marker) + "' > stage-" + name + ".json\n"
		delete(a, "run")
		a["runtime"] = prefix + "-local"
		a["command"] = map[string]any{"entrypoint": "sh", "arguments": []string{"-c", script}}
	}
	raw, err = yaml.Marshal(workflow)
	if err != nil {
		return err
	}
	if err = put(filepath.Join(dir, "workflow.yaml"), raw, 0644); err != nil {
		return err
	}
	for _, name := range []string{"environment.yaml", "scope.yaml", "topology.yaml"} {
		data, e := os.ReadFile(filepath.Join(root, "machine-learning/hyperparameter-search", name))
		if e != nil {
			return e
		}
		data = []byte(strings.ReplaceAll(string(data), "showcase-hyperparameter-search", prefix))
		if e = put(filepath.Join(dir, name), data, 0644); e != nil {
			return e
		}
	}
	profile := "Execute the original producer/consumer file-content checks in two Docker activities on one local host. The local profile verifies actual file handoff and receipt content. It does not measure GCP provisioning, Kubernetes placement, or cross-cloud networking."
	config := map[string]any{"slug": slug, "title": "Hybrid " + variant + " to cloud — local reproducibility profile", "stages": []string{"produce", "consume"}, "dependencies": map[string][]string{"produce": {}, "consume": {"produce"}}, "artifacts": []string{"handoff.txt", "receipt.txt"}, "localProfile": profile, "validationMode": "local-workload"}
	if err = encode(filepath.Join(dir, "data/input.json"), config); err != nil {
		return err
	}
	if err = encode(filepath.Join(dir, "expected/manifest.json"), map[string]any{"showcase": slug, "status": "success", "artifacts": []string{"handoff.txt", "receipt.txt"}}); err != nil {
		return err
	}
	files := map[string]string{"docker/Dockerfile": "FROM busybox:1.36\n", "prepare.sh": "#!/bin/sh\nset -eu\ngo -C \"$(dirname \"$0\")/../..\" mod download\n", "run.sh": "#!/bin/sh\nset -eu\nroot=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\ngo run \"$root/../../tools/showcase\" -root \"$root\"\n"}
	fixture := "akoflow-" + variant + "-to-gcp"
	files["validate.sh"] = "#!/bin/sh\nset -eu\nroot=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\ngrep -qx '" + fixture + "' \"$root/outputs/handoff.txt\"\ngrep -qx 'cloud consumed: " + fixture + "' \"$root/outputs/receipt.txt\"\ntest -s \"$root/outputs/stage-produce.json\"\ntest -s \"$root/outputs/stage-consume.json\"\nprintf 'Validated original transfer fixture and receipt\\n'\n"
	files["README.md"] = fmt.Sprintf("# Hybrid %s to GCP: portable local profile\n\n%s\n\nThe original [cloud placement definition](../../%s) remains available as a separate historical version in Hub. It requires the GCP/Kind setup from the documentation. The words `cloud consumed` in the receipt are an inherited fixture label, not evidence that a cloud VM was used.\n\n## Activities and data\n\n1. `produce` writes the original synthetic fixture `%s` to `handoff.txt`.\n2. AkôFlow materializes this declared dependency into the consumer workspace.\n3. `consume` checks the exact bytes and writes `receipt.txt`. Each activity records its successful completion after the content checks pass.\n\nThe fixture is generated inline; no external dataset, account or secret is needed for this local profile.\n\n## Local execution\n\nInstall Go 1.23+ for the standalone command, or use AkôFlow Desktop/server with Docker. From this directory:\n\n```sh\n./prepare.sh && ./run.sh && ./validate.sh\n```\n\nFor the daemon, import `environment.yaml`, `scope.yaml`, `topology.yaml`, and the digest-pinned YAML returned by Hub. Build a plan and execute it locally. Review the runtime configuration before choosing any original cloud placement variant.\n", variant, profile, original, fixture)
	for name, data := range files {
		mode := os.FileMode(0644)
		if strings.HasSuffix(name, ".sh") {
			mode = 0755
		}
		if err = put(filepath.Join(dir, name), []byte(data), mode); err != nil {
			return err
		}
	}
	return nil
}
func montage(root string) error {
	source := filepath.Join(root, "scientific-workflows/montage-050")
	dir := filepath.Join(root, "connections/montage-cloud-local-profile")
	for _, name := range []string{"workflow.yaml", "environment.yaml", "scope.yaml", "topology.yaml", "data/input.json", "docker/Dockerfile", "expected/manifest.json", "prepare.sh", "run.sh", "validate.sh", "evidence/daemon-run.json", "evidence/public-image-alias.json"} {
		raw, err := os.ReadFile(filepath.Join(source, name))
		if err != nil {
			return err
		}
		mode := os.FileMode(0644)
		if strings.HasSuffix(name, ".sh") {
			mode = 0755
		}
		if err = put(filepath.Join(dir, name), raw, mode); err != nil {
			return err
		}
	}
	text := "# Montage GCP/local: portable reference profile\n\nThis profile preserves the complete original Montage 050d computation: 58 activities, 138 file handoffs, twelve FITS observations, three 1800×1800 mosaics and four PNG previews. All activities execute through local Docker.\n\nThe measured reference execution is shared with the Montage 050 local showcase because the executable DAG, input data, image filesystem and runtime configuration are identical. This is explicitly a shared reference capture, not a second independent experiment and not evidence of a GCP execution. The public capture preserves its original execution identifiers.\n\nThe [original cloud/local configuration](../../real/montage-cloud-local/workflow.json) is retained as a separate historical version for users who configure GCP resources. Its four on-demand worker placements and predicted values are not measured by the local reference run.\n\n## Inputs, outputs and execution\n\nThe pinned image includes the twelve original FITS observations and Montage executables. Use the source image's upstream dataset terms before redistributing the input observations. Configure local Docker using the companion environment, scope and topology definitions, import the public local-profile URI, create a plan and execute. On Apple Silicon the image requires amd64 emulation.\n\n`./prepare.sh && ./run.sh && ./validate.sh` executes and validates the same local profile with Go and Docker. This is a full scientific workload, not a short timing simulation. The generated FITS and PNG files are validated before publication.\n"
	return put(filepath.Join(dir, "README.md"), []byte(text), 0644)
}
