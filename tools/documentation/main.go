// Command documentation exports verified source contracts and local execution evidence to the docs checkout.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type contract struct {
	Title            string              `json:"title"`
	ExamplePath      string              `json:"examplePath"`
	Stages           [][]string          `json:"stages"`
	Dependencies     map[string][]string `json:"dependencies"`
	ValidationMode   string              `json:"validationMode"`
	LocalProfile     string              `json:"localProfile"`
	SourceCommit     string              `json:"sourceCommit"`
	Requirements     []string            `json:"requirements"`
	Artifacts        []string            `json:"artifacts"`
	ExecutionMode    string              `json:"executionMode"`
	ValidationStatus string              `json:"validationStatus"`
	Screenshots      map[string]string   `json:"screenshots"`
	Daemon           map[string]any      `json:"daemon,omitempty"`
}

func main() {
	root := flag.String("root", ".", "examples checkout")
	docs := flag.String("docs", "../akoflow/docs", "documentation checkout")
	flag.Parse()
	if err := export(*root, *docs); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func export(root, docs string) error {
	target := filepath.Join(docs, "src/data/showcase-contracts.json")
	data, err := os.ReadFile(target)
	if err != nil {
		return err
	}
	catalog := map[string]contract{}
	if err := json.Unmarshal(data, &catalog); err != nil {
		return err
	}
	commit, err := exec.Command("git", "-C", root, "rev-parse", "HEAD").Output()
	if err != nil {
		return err
	}
	results := []map[string]any{}
	for route, item := range catalog {
		bundle := filepath.Join(root, item.ExamplePath)
		workflowData, err := os.ReadFile(filepath.Join(bundle, "workflow.yaml"))
		if err != nil {
			return err
		}
		var definition struct {
			Spec struct {
				Activities []struct {
					Name      string   `yaml:"name"`
					DependsOn []string `yaml:"dependsOn"`
				} `yaml:"activities"`
			} `yaml:"spec"`
		}
		if err := yaml.Unmarshal(workflowData, &definition); err != nil {
			return err
		}
		item.Dependencies = map[string][]string{}
		remaining := []string{}
		for _, a := range definition.Spec.Activities {
			remaining = append(remaining, a.Name)
			item.Dependencies[a.Name] = append([]string{}, a.DependsOn...)
		}
		item.Stages = [][]string{}
		complete := map[string]bool{}
		for len(remaining) > 0 {
			ready := []string{}
			pending := []string{}
			for _, name := range remaining {
				eligible := true
				for _, dep := range item.Dependencies[name] {
					if !complete[dep] {
						eligible = false
					}
				}
				if eligible {
					ready = append(ready, name)
				} else {
					pending = append(pending, name)
				}
			}
			if len(ready) == 0 {
				return fmt.Errorf("DAG cycle in %s", item.ExamplePath)
			}
			for _, name := range ready {
				complete[name] = true
			}
			item.Stages = append(item.Stages, ready)
			remaining = pending
		}
		item.ValidationMode = "local-pipeline"
		item.Requirements = []string{}
		if raw, err := os.ReadFile(filepath.Join(bundle, "data/input.json")); err == nil {
			var config struct {
				Mode         string   `json:"validationMode"`
				Profile      string   `json:"localProfile"`
				CIValidation string   `json:"ciValidation"`
				Artifacts    []string `json:"artifacts"`
			}
			if err := json.Unmarshal(raw, &config); err != nil {
				return err
			}
			item.ValidationMode = config.Mode
			item.LocalProfile = config.Profile
		} else {
			readme, err := os.ReadFile(filepath.Join(bundle, "README.md"))
			if err != nil {
				return err
			}
			paragraphs := strings.SplitN(string(readme), "\n\n", 3)
			if len(paragraphs) > 1 {
				item.LocalProfile = paragraphs[1]
			}
		}
		if raw, err := os.ReadFile(filepath.Join(bundle, "requirements.txt")); err == nil {
			for _, line := range strings.Split(strings.TrimSpace(string(raw)), "\n") {
				if line != "" && !strings.HasPrefix(line, "--") {
					item.Requirements = append(item.Requirements, line)
				}
			}
		}
		var profile struct {
			CIValidation string   `json:"ciValidation"`
			Artifacts    []string `json:"artifacts"`
		}
		if raw, err := os.ReadFile(filepath.Join(bundle, "data/input.json")); err == nil {
			if err := json.Unmarshal(raw, &profile); err != nil {
				return err
			}
		}
		evidence := filepath.Join(docs, "static/showcase/validation", item.ExamplePath)
		if err := os.MkdirAll(evidence, 0755); err != nil {
			return err
		}
		item.SourceCommit = strings.TrimSpace(string(commit))
		item.Screenshots = map[string]string{}
		item.ValidationStatus = "passed"
		completed := 0
		if profile.CIValidation == "image-and-contract" {
			raw, err := os.ReadFile(filepath.Join(bundle, "evidence/image-contract.json"))
			if err != nil {
				return err
			}
			if err := os.WriteFile(filepath.Join(evidence, "image-contract.json"), raw, 0644); err != nil {
				return err
			}
			item.Artifacts = profile.Artifacts
			item.ValidationStatus = "image-and-contract-verified"
			item.ExecutionMode = "not-executed"
		} else {
			var manifest struct {
				Status    string   `json:"status"`
				Artifacts []string `json:"artifacts"`
			}
			raw, err := os.ReadFile(filepath.Join(bundle, "outputs/manifest.json"))
			if err != nil {
				return err
			}
			if err := json.Unmarshal(raw, &manifest); err != nil {
				return err
			}
			if manifest.Status != "success" {
				return fmt.Errorf("unverified local example: %s", item.ExamplePath)
			}
			item.Artifacts = manifest.Artifacts
			var validation struct {
				Mode      string `json:"executionMode"`
				Completed int    `json:"completedActivities"`
			}
			raw, err = os.ReadFile(filepath.Join(bundle, "outputs/dag-validation.json"))
			if err != nil {
				return err
			}
			if err := json.Unmarshal(raw, &validation); err != nil {
				return err
			}
			if validation.Completed != len(definition.Spec.Activities) {
				return fmt.Errorf("incomplete activity evidence: %s", item.ExamplePath)
			}
			item.ExecutionMode = validation.Mode
			completed = validation.Completed
			files := []string{"manifest.json", "dag-validation.json"}
			for _, a := range definition.Spec.Activities {
				files = append(files, "stage-"+a.Name+".json")
			}
			for _, file := range files {
				contents, err := os.ReadFile(filepath.Join(bundle, "outputs", file))
				if err != nil {
					return err
				}
				if err := os.WriteFile(filepath.Join(evidence, file), contents, 0644); err != nil {
					return err
				}
			}
		}
		if raw, err := os.ReadFile(filepath.Join(bundle, "evidence/daemon-run.json")); err == nil {
			var daemon map[string]any
			if err := json.Unmarshal(raw, &daemon); err != nil {
				return err
			}
			item.Daemon = map[string]any{}
			for _, key := range []string{"workflowId", "planId", "runId", "image", "imageId", "status", "activityCount", "completedActivityCount", "observedAt"} {
				item.Daemon[key] = daemon[key]
			}
			if profile.CIValidation != "image-and-contract" && daemon["status"] != "completed" {
				return fmt.Errorf("daemon execution is incomplete for %s", item.ExamplePath)
			}
			if profile.CIValidation == "image-and-contract" {
				item.ValidationStatus = fmt.Sprint(daemon["status"])
				item.ExecutionMode = "daemon-local-docker"
			}
			if err := os.WriteFile(filepath.Join(evidence, "daemon-run.json"), raw, 0644); err != nil {
				return err
			}
			capturePath := filepath.Join(bundle, "screenshots/current/capture-manifest.json")
			if capture, err := os.ReadFile(capturePath); err == nil {
				var captures struct {
					RunID              string `json:"runId"`
					ImageID            string `json:"imageId"`
					WorkflowScreenshot string `json:"workflowScreenshot"`
					Activities         []struct {
						Stage string `json:"stage"`
						File  string `json:"file"`
					} `json:"activities"`
				}
				if err := json.Unmarshal(capture, &captures); err != nil {
					return err
				}
				if captures.RunID != daemon["runId"] || captures.ImageID != daemon["imageId"] {
					return fmt.Errorf("screenshots do not match the verified run: %s", item.ExamplePath)
				}
				if profile.CIValidation != "image-and-contract" && len(captures.Activities) != len(definition.Spec.Activities) {
					return fmt.Errorf("missing activity screenshots: %s", item.ExamplePath)
				}
				imageDir := filepath.Join(docs, "static/showcase/evidence", item.ExamplePath)
				if err := os.MkdirAll(imageDir, 0755); err != nil {
					return err
				}
				images := map[string]string{}
				if captures.WorkflowScreenshot != "" {
					images["workflow"] = captures.WorkflowScreenshot
				}
				for _, activity := range captures.Activities {
					images[activity.Stage] = activity.File
				}
				for name, file := range images {
					if filepath.Base(file) != file || !strings.HasSuffix(file, ".png") {
						return fmt.Errorf("invalid capture path")
					}
					bytes, err := os.ReadFile(filepath.Join(bundle, "screenshots/current", file))
					if err != nil {
						return err
					}
					if err := os.WriteFile(filepath.Join(imageDir, file), bytes, 0644); err != nil {
						return err
					}
					item.Screenshots[name] = "/showcase/evidence/" + item.ExamplePath + "/" + file
				}
			} else if profile.CIValidation != "image-and-contract" {
				return fmt.Errorf("missing screenshot manifest: %s", item.ExamplePath)
			}
		} else if profile.CIValidation != "image-and-contract" {
			return fmt.Errorf("missing daemon verification: %s", item.ExamplePath)
		}

		catalog[route] = item
		results = append(results, map[string]any{"path": item.ExamplePath, "status": item.ValidationStatus, "activities": completed, "declaredActivities": len(definition.Spec.Activities), "executionMode": item.ExecutionMode, "sourceCommit": item.SourceCommit})
	}
	encoded, err := json.MarshalIndent(catalog, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(target, append(encoded, '\n'), 0644); err != nil {
		return err
	}
	summary, err := json.MarshalIndent(map[string]any{"sourceCommit": strings.TrimSpace(string(commit)), "results": results}, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(docs, "static/showcase/validation/summary.json"), append(summary, '\n'), 0644)
}
