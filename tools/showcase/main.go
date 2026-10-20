// Command showcase executes independent local activities from their authoritative workflow DAG.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

type scenario struct {
	Stages       []string            `json:"stages"`
	Dependencies map[string][]string `json:"dependencies"`
	Mode         string              `json:"validationMode"`
	Slug         string              `json:"slug"`
	Artifacts    []string            `json:"artifacts"`
}
type activity struct {
	Name              string   `yaml:"name"`
	DependsOn         []string `yaml:"dependsOn"`
	WorkspaceSeedPath string   `yaml:"workspaceSeedPath"`
	Command           struct {
		Entrypoint string   `yaml:"entrypoint"`
		Arguments  []string `yaml:"arguments"`
	} `yaml:"command"`
}
type workflow struct {
	Name string `yaml:"name"`
	Spec struct {
		Image      string     `yaml:"image"`
		Activities []activity `yaml:"activities"`
	} `yaml:"spec"`
	Activities []activity `yaml:"activities"` // Accepted by small runner regression fixtures.
}
type options struct {
	Container bool
	Parallel  int
}

func main() {
	root := flag.String("root", ".", "showcase directory")
	container := flag.Bool("container", os.Getenv("AKOFLOW_LOCAL_CONTAINER") == "1", "execute each activity in its prepared OCI image with network access disabled")
	prepare := flag.Bool("prepare-container", false, "build the local image and exit; network may be required during preparation")
	parallel := flag.Int("parallel", 4, "maximum concurrent local activities")
	flag.Parse()
	if *prepare {
		if err := prepareContainer(*root); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}
	if err := runWithOptions(*root, options{Container: *container, Parallel: *parallel}); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func run(root string) error { return runWithOptions(root, options{}) }

func load(root string) (scenario, workflow, error) {
	config := scenario{Dependencies: map[string][]string{}}
	var definition workflow
	data, err := os.ReadFile(filepath.Join(root, "workflow.yaml"))
	if err != nil {
		return config, definition, err
	}
	if err := yaml.Unmarshal(data, &definition); err != nil {
		return config, definition, err
	}
	if len(definition.Spec.Activities) == 0 {
		definition.Spec.Activities = definition.Activities
	}
	if data, err := os.ReadFile(filepath.Join(root, "data/input.json")); err == nil {
		if err := json.Unmarshal(data, &config); err != nil {
			return config, definition, err
		}
	} else if !os.IsNotExist(err) {
		return config, definition, err
	} else {
		config.Slug = definition.Name
		config.Mode = "local-pipeline"
		for _, a := range definition.Spec.Activities {
			config.Stages = append(config.Stages, a.Name)
			config.Dependencies[a.Name] = append([]string{}, a.DependsOn...)
		}
	}
	if len(config.Stages) == 0 || len(config.Stages) != len(definition.Spec.Activities) {
		return config, definition, fmt.Errorf("workflow activity count differs from contract")
	}
	known := map[string]bool{}
	for i, a := range definition.Spec.Activities {
		if a.Name != config.Stages[i] || known[a.Name] {
			return config, definition, fmt.Errorf("activity mismatch or duplicate: %s", a.Name)
		}
		known[a.Name] = true
		if !reflect.DeepEqual(append([]string{}, a.DependsOn...), config.Dependencies[a.Name]) {
			return config, definition, fmt.Errorf("dependency mismatch: %s", a.Name)
		}
	}
	if len(config.Dependencies) != len(known) {
		return config, definition, fmt.Errorf("activity dependency contract has missing or extra entries")
	}
	for name, deps := range config.Dependencies {
		for _, dep := range deps {
			if !known[dep] || name == dep {
				return config, definition, fmt.Errorf("invalid dependency %s -> %s", dep, name)
			}
		}
	}
	return config, definition, nil
}

func dependencyWaves(config scenario) ([][]string, error) {
	completed := map[string]bool{}
	waves := [][]string{}
	for len(completed) < len(config.Stages) {
		ready := []string{}
		for _, name := range config.Stages {
			if completed[name] {
				continue
			}
			eligible := true
			for _, dep := range config.Dependencies[name] {
				if !completed[dep] {
					eligible = false
				}
			}
			if eligible {
				ready = append(ready, name)
			}
		}
		if len(ready) == 0 {
			return nil, fmt.Errorf("dependency cycle or missing contract")
		}
		for _, name := range ready {
			completed[name] = true
		}
		waves = append(waves, ready)
	}
	return waves, nil
}

func runWithOptions(root string, opts options) error {
	root, err := filepath.Abs(root)
	if err != nil {
		return err
	}
	config, definition, err := load(root)
	if err != nil {
		return err
	}
	waves, err := dependencyWaves(config)
	if err != nil {
		return err
	}
	image := ""
	if opts.Container {
		image = "akoflow-local/" + filepath.Base(root) + ":workload"
		expected, err := contextDigest(root)
		if err != nil {
			return err
		}
		observed, err := exec.Command("docker", "image", "inspect", "--format", `{{index .Config.Labels "io.akoflow.source-sha256"}}`, image).Output()
		if err != nil || strings.TrimSpace(string(observed)) != expected {
			return fmt.Errorf("local container image is missing or stale; run ./prepare.sh before offline execution")
		}

	}
	output := filepath.Join(root, "outputs")
	if err := os.RemoveAll(output); err != nil {
		return err
	}
	if err := os.MkdirAll(output, 0755); err != nil {
		return err
	}
	if opts.Container {
		seeds := map[string]bool{}
		for _, a := range definition.Spec.Activities {
			if a.WorkspaceSeedPath != "" {
				seeds[a.WorkspaceSeedPath] = true
			}
		}
		for seed := range seeds {
			cmd := exec.Command("docker", "run", "--rm", "--network", "none", "--mount", "type=bind,src="+output+",dst=/outputs", "--entrypoint", "sh", image, "-c", `cp -an "$1"/. "$2"/`, "akoflow-seed", seed, "/outputs")
			if logs, err := cmd.CombinedOutput(); err != nil {
				return fmt.Errorf("seed image inputs: %w: %s", err, logs)
			}
		}
	}

	python := os.Getenv("AKOFLOW_PYTHON")
	if python == "" {
		python = "python3"
		if _, err := os.Stat(filepath.Join(root, ".venv/bin/python")); err == nil {
			python = filepath.Join(root, ".venv/bin/python")
		}
	}
	activities := map[string]activity{}
	for _, a := range definition.Spec.Activities {
		activities[a.Name] = a
	}
	work := func(name string) error {
		a := activities[name]
		args := append([]string{}, a.Command.Arguments...)
		if len(args) == 0 {
			args = []string{"/app/scripts/run_showcase.py", "--stage", name, "--output", "."}
		}
		for i, arg := range args {
			if i > 0 && args[i-1] == "--output" {
				if opts.Container {
					args[i] = "/outputs"
				} else {
					args[i] = output
				}
				continue
			}
			if !opts.Container && strings.HasPrefix(arg, "/app/") {
				args[i] = filepath.Join(root, strings.TrimPrefix(arg, "/app/"))
				if arg == "/app/run_showcase.py" {
					args[i] = filepath.Join(root, "scripts/run_showcase.py")
				}
			}
		}
		var cmd *exec.Cmd
		if opts.Container {
			entrypoint := a.Command.Entrypoint
			if entrypoint == "" {
				entrypoint = "python"
			}
			dockerArgs := []string{"run", "--rm", "--network", "none", "--mount", "type=bind,src=" + output + ",dst=/outputs", "--workdir", "/outputs", "--entrypoint", entrypoint, image}
			if profile := os.Getenv("AKOFLOW_PROFILE"); profile != "" {
				dockerArgs = append([]string{"run", "--rm", "--network", "none", "--env", "AKOFLOW_PROFILE=" + profile, "--mount", "type=bind,src=" + output + ",dst=/outputs", "--workdir", "/outputs", "--entrypoint", entrypoint, image}, args...)
			} else {
				dockerArgs = append(dockerArgs, args...)
			}
			cmd = exec.Command("docker", dockerArgs...)
		} else {
			entrypoint := python
			if a.Command.Entrypoint != "" && a.Command.Entrypoint != "python" && a.Command.Entrypoint != "python3" {
				entrypoint = a.Command.Entrypoint
			}
			cmd = exec.Command(entrypoint, args...)
			cmd.Dir = output
		}
		started := time.Now().UTC()
		fmt.Printf("Running %s\n", name)
		logs, err := cmd.CombinedOutput()
		finished := time.Now().UTC()
		if err != nil {
			return fmt.Errorf("%s: %w: %s", name, err, logs)
		}
		path := filepath.Join(output, "stage-"+name+".json")
		record := map[string]any{}
		if data, err := os.ReadFile(path); err == nil {
			if err := json.Unmarshal(data, &record); err != nil {
				return err
			}
		}
		if _, exists := record["result"]; !exists {
			record["result"] = map[string]any{"commandCompleted": true, "stdout": strings.TrimSpace(string(logs))}
		}
		mode := "local-process"
		if opts.Container {
			mode = "local-container"
		}
		record["showcase"], record["stage"], record["status"] = config.Slug, name, "success"
		record["executionMode"], record["dependencies"] = mode, config.Dependencies[name]
		fmt.Printf("Completed %s (%s)\n", name, finished.Sub(started).Round(time.Millisecond))
		record["startedAt"], record["finishedAt"] = started.Format(time.RFC3339Nano), finished.Format(time.RFC3339Nano)
		if err := writeJSON(path, record); err != nil {
			return err
		}
		return nil
	}
	if err := executeReady(config, opts.Parallel, work); err != nil {
		return err
	}

	if config.Mode == "" {
		config.Mode = "contract-fixture"
	}
	manifestPath := filepath.Join(output, "manifest.json")
	if config.Mode == "local-pipeline" {
		data, err := os.ReadFile(manifestPath)
		if err != nil {
			return err
		}
		var manifest struct {
			Status    string   `json:"status"`
			Artifacts []string `json:"artifacts"`
		}
		if err := json.Unmarshal(data, &manifest); err != nil {
			return err
		}
		if manifest.Status != "success" {
			return fmt.Errorf("pipeline manifest reports %s", manifest.Status)
		}
		config.Artifacts = manifest.Artifacts
	}
	digests := map[string]string{}
	for _, name := range config.Artifacts {
		clean := filepath.Clean(name)
		if filepath.IsAbs(name) || clean == ".." || strings.HasPrefix(clean, ".."+string(filepath.Separator)) {
			return fmt.Errorf("artifact escaped its workspace: %s", name)
		}
		data, err := os.ReadFile(filepath.Join(output, clean))
		if err != nil || len(data) == 0 {
			return fmt.Errorf("missing or empty computed artifact: %s", name)
		}
		digest := sha256.Sum256(data)
		digests[name] = hex.EncodeToString(digest[:])
	}
	if config.Mode == "local-workload" || config.Mode == "local-pipeline" {
		manifest := map[string]any{"showcase": config.Slug, "status": "success", "artifacts": config.Artifacts, "stages": config.Stages, "validationMode": config.Mode, "sha256": digests}
		if err := writeJSON(manifestPath, manifest); err != nil {
			return err
		}
	}
	mode := "local-process"
	if opts.Container {
		mode = "local-container"
	}
	report := map[string]any{"mode": config.Mode, "executionMode": mode, "dependencyWaves": waves, "completedActivities": len(config.Stages), "artifactSha256": digests, "schedulingPolicy": "ready activities with bounded concurrency"}
	return writeJSON(filepath.Join(output, "dag-validation.json"), report)
}
func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0644)
}

// executeReady admits a child as soon as its own dependencies complete. It never
// inserts a barrier across unrelated branches of a scientific DAG.
func executeReady(config scenario, parallel int, work func(string) error) error {
	if parallel <= 0 {
		parallel = 4
	}
	type result struct {
		Name string
		Err  error
	}
	results := make(chan result, parallel)
	started, completed := map[string]bool{}, map[string]bool{}
	active := 0
	var failure error
	for len(completed) < len(config.Stages) {
		if failure == nil {
			for _, name := range config.Stages {
				if active >= parallel {
					break
				}
				if started[name] {
					continue
				}
				ready := true
				for _, parent := range config.Dependencies[name] {
					if !completed[parent] {
						ready = false
					}
				}
				if ready {
					started[name] = true
					active++
					go func(name string) { results <- result{name, work(name)} }(name)
				}
			}
		}
		if active == 0 {
			if failure != nil {
				return failure
			}
			return fmt.Errorf("no eligible activity remains")
		}
		observed := <-results
		active--
		if observed.Err != nil {
			if failure == nil {
				failure = observed.Err
			}
		} else {
			completed[observed.Name] = true
		}
		if failure != nil && active == 0 {
			return failure
		}
	}
	return nil
}

func contextDigest(root string) (string, error) {
	paths := []string{}
	for _, dir := range []string{"scripts", "data"} {
		path := filepath.Join(root, dir)
		if _, err := os.Stat(path); os.IsNotExist(err) {
			continue
		}
		if err := filepath.WalkDir(path, func(path string, entry os.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if !entry.IsDir() {
				paths = append(paths, path)
			}
			return nil
		}); err != nil {
			return "", err
		}
	}
	for _, name := range []string{"docker/Dockerfile", "requirements.txt", ".dockerignore"} {
		path := filepath.Join(root, name)
		if _, err := os.Stat(path); err == nil {
			paths = append(paths, path)
		}
	}
	sort.Strings(paths)
	digest := sha256.New()
	for _, path := range paths {
		relative, err := filepath.Rel(root, path)
		if err != nil {
			return "", err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return "", err
		}
		fmt.Fprintln(digest, relative)
		digest.Write(data)
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}
func prepareContainer(root string) error {
	root, err := filepath.Abs(root)
	if err != nil {
		return err
	}
	if _, _, err := load(root); err != nil {
		return err
	}
	digest, err := contextDigest(root)
	if err != nil {
		return err
	}
	image := "akoflow-local/" + filepath.Base(root) + ":workload"
	build := exec.Command("docker", "build", "-f", filepath.Join(root, "docker/Dockerfile"), "--label", "io.akoflow.source-sha256="+digest, "-t", image, root)
	build.Stdout = os.Stdout
	build.Stderr = os.Stderr
	return build.Run()
}
