// Command daemon-local builds, registers and runs a showcase on a verified local Docker daemon.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type client struct {
	Base, Token string
	HTTP        *http.Client
}

func (c client) request(method, path string, value any) (map[string]any, error) {
	var body io.Reader
	if value != nil {
		data, err := json.Marshal(value)
		if err != nil {
			return nil, err
		}
		body = bytes.NewReader(data)
	}
	request, err := http.NewRequest(method, c.Base+"/"+strings.Trim(path, "/")+"/", body)
	if err != nil {
		return nil, err
	}
	request.Header.Set("Authorization", "Bearer "+c.Token)
	request.Header.Set("Content-Type", "application/json")
	response, err := c.HTTP.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	data, err := io.ReadAll(io.LimitReader(response.Body, 16<<20))
	if err != nil {
		return nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, fmt.Errorf("%s %s: HTTP %d: %s", method, path, response.StatusCode, data)
	}
	result := map[string]any{}
	if len(bytes.TrimSpace(data)) > 0 {
		if err := json.Unmarshal(data, &result); err != nil {
			return nil, err
		}
	}
	return result, nil
}
func readYAML(path string) (map[string]any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	result := map[string]any{}
	if err := yaml.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}
func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0644)
}
func main() {
	root := flag.String("root", ".", "examples checkout")
	example := flag.String("example", "", "relative showcase bundle path")
	base := flag.String("api-url", "http://127.0.0.1:8080/akoflow-api", "local AkôFlow API")
	envFile := flag.String("env-file", "", "optional env file containing AKOFLOW_API_TOKEN (never stored in output)")
	build := flag.Bool("build", true, "build the declared image before execution")
	wait := flag.Bool("wait", true, "wait for terminal state; false submits and leaves the daemon run active")
	flag.Parse()
	token := os.Getenv("AKOFLOW_API_TOKEN")
	if token == "" && *envFile != "" {
		data, err := os.ReadFile(*envFile)
		if err != nil {
			panic(err)
		}
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "AKOFLOW_API_TOKEN=") {
				token = strings.Trim(strings.TrimSpace(strings.TrimPrefix(line, "AKOFLOW_API_TOKEN=")), "\"'")
			}
		}
	}
	if token == "" || *example == "" {
		fmt.Fprintln(os.Stderr, "-example and AKOFLOW_API_TOKEN (or -env-file) are required")
		os.Exit(1)
	}
	c := client{strings.TrimSuffix(*base, "/"), token, &http.Client{Timeout: 45 * time.Second}}
	if err := run(c, *root, *example, *build, *wait); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func run(c client, root, relative string, build, wait bool) error {
	preflight, err := c.request("GET", "preflight", nil)
	if err != nil {
		return err
	}
	docker, ok := preflight["docker"].(map[string]any)
	if !ok || docker["available"] != true {
		return fmt.Errorf("the daemon has not validated local Docker connectivity")
	}
	bundle, err := filepath.Abs(filepath.Join(root, relative))
	if err != nil {
		return err
	}
	definition, err := readYAML(filepath.Join(bundle, "workflow.yaml"))
	if err != nil {
		return err
	}
	spec := definition["spec"].(map[string]any)
	image := spec["image"].(string)
	if build {
		command := exec.Command("docker", "build", "-f", filepath.Join(bundle, "docker/Dockerfile"), "-t", image, bundle)
		command.Stdout = os.Stdout
		command.Stderr = os.Stderr
		if err := command.Run(); err != nil {
			return fmt.Errorf("build %s: %w", relative, err)
		}
	}
	imageID, err := exec.Command("docker", "image", "inspect", "--format", "{{.Id}}", image).Output()
	if err != nil {
		return err
	}
	// Keep repeat executions tied to these exact image bytes rather than a mutable release tag.
	if !strings.Contains(image, "@sha256:") {
		digest := strings.TrimSpace(strings.TrimPrefix(string(imageID), "sha256:"))
		repository := image
		if colon := strings.LastIndex(repository, ":"); colon > strings.LastIndex(repository, "/") {
			repository = repository[:colon]
		}
		immutable := repository + ":local-" + digest[:16]
		if logs, err := exec.Command("docker", "tag", image, immutable).CombinedOutput(); err != nil {
			return fmt.Errorf("tag verified local image: %w: %s", err, logs)
		}
		image = immutable
		spec["image"] = immutable
	}
	// Revision-specific workflow names preserve older registered definitions and run evidence.
	hash := sha256.Sum256(append([]byte(fmt.Sprint(definition)), imageID...))
	suffix := hex.EncodeToString(hash[:])[:10]
	definition["name"] = definition["name"].(string) + "-local-" + suffix
	environment, err := readYAML(filepath.Join(bundle, "environment.yaml"))
	if err != nil {
		return err
	}
	scope, err := readYAML(filepath.Join(bundle, "scope.yaml"))
	if err != nil {
		return err
	}
	topology, err := readYAML(filepath.Join(bundle, "topology.yaml"))
	if err != nil {
		return err
	}
	for _, pair := range []struct {
		Path  string
		Value map[string]any
	}{{"environments", environment}, {"execution-scopes", scope}, {"network-topologies", topology}} {
		id := pair.Value["id"]
		if pair.Path == "environments" {
			id = pair.Value["environment"].(map[string]any)["id"]
		}
		if _, err := c.request("GET", pair.Path+"/"+fmt.Sprint(id), nil); err != nil {
			if !strings.Contains(err.Error(), "HTTP 404") {
				return err
			}
			if _, err := c.request("POST", pair.Path, pair.Value); err != nil {
				return err
			}
		}
	}
	registered, err := c.request("GET", "workflow-definitions/"+fmt.Sprint(definition["name"]), nil)
	if err != nil {
		if !strings.Contains(err.Error(), "HTTP 404") {
			return err
		}
		registered, err = c.request("POST", "workflow-definitions", definition)
		if err != nil {
			return err
		}
	}
	version, ok := registered["version"].(map[string]any)
	if !ok {
		return fmt.Errorf("workflow registration did not return a version")
	}
	resources := environment["resources"].([]any)
	resourceID := resources[0].(map[string]any)["id"].(string)
	runtimeID := environment["runtimes"].([]any)[0].(map[string]any)["id"].(string)
	activities := version["activities"].([]any)
	workflowID := registered["id"].(string)
	planID := workflowID + "-manual-plan-" + time.Now().UTC().Format("20060102t150405.000000000")
	assignments := []map[string]any{}
	order := map[string]int{}
	for index, raw := range spec["activities"].([]any) {
		order[raw.(map[string]any)["name"].(string)] = index
	}
	for _, raw := range activities {
		a := raw.(map[string]any)
		index, exists := order[fmt.Sprint(a["name"])]
		if !exists {
			return fmt.Errorf("registered activity does not match source: %v", a["name"])
		}
		assignments = append(assignments, map[string]any{"id": planID + "-" + fmt.Sprint(a["id"]), "planId": planID, "activityId": a["id"], "resourceId": resourceID, "orderOnResource": index, "predictedStartAt": index, "predictedFinishAt": index + 1, "metadata": map[string]any{"runtimeId": runtimeID}})
	}
	plan := map[string]any{"id": planID, "workflowVersionId": version["id"], "executionScopeId": scope["id"], "networkTopologyId": topology["id"], "source": "imported", "algorithm": "manual", "algorithmVersion": "1", "objective": "custom", "predicted": map[string]any{"makespanSeconds": len(activities), "cost": 0, "feasible": true}, "assignments": assignments}
	imported, err := c.request("POST", "schedule-plans/import", map[string]any{"plan": plan})
	if err != nil {
		return err
	}
	plan = imported
	runID := workflowID + "-run-" + time.Now().UTC().Format("20060102t150405.000000000")
	request := map[string]any{"run": map[string]any{"id": runID, "schedulePlanId": planID, "mode": "real", "status": "created"}, "plan": plan, "workflow": version, "resources": resources, "executionScope": scope, "networkTopology": topology, "runtimes": environment["runtimes"], "runtimeBindings": environment["resourceRuntimeBindings"]}
	if _, err := c.request("POST", "execution-runs", request); err != nil {
		return err
	}
	evidence := map[string]any{"workflowId": workflowID, "planId": planID, "runId": runID, "image": image, "imageId": strings.TrimSpace(string(imageID)), "status": "submitted", "activityCount": len(activities), "observedAt": time.Now().UTC().Format(time.RFC3339)}
	output := filepath.Join(bundle, "evidence")
	if err := os.MkdirAll(output, 0755); err != nil {
		return err
	}
	path := filepath.Join(output, "daemon-run.json")
	if err := writeJSON(path, evidence); err != nil {
		return err
	}
	fmt.Printf("Submitted %s: %s (%d activities)\n", relative, runID, len(activities))
	if !wait {
		return nil
	}
	deadline := time.Now().Add(20 * time.Minute)
	for time.Now().Before(deadline) {
		projection, err := c.request("GET", "execution-runs/"+runID, nil)
		if err != nil {
			return err
		}
		observed, ok := projection["run"].(map[string]any)
		if !ok {
			return fmt.Errorf("run projection missing run")
		}
		status, _ := observed["status"].(string)
		evidence["status"] = status
		evidence["observedAt"] = time.Now().UTC().Format(time.RFC3339)
		evidence["completedActivityCount"] = observed["completedActivityCount"]
		if err := writeJSON(path, evidence); err != nil {
			return err
		}
		if status == "completed" || status == "failed" || status == "cancelled" {
			evidence["projection"] = projection
			if err := writeJSON(path, evidence); err != nil {
				return err
			}
			if status != "completed" {
				return fmt.Errorf("%s daemon run ended %s; inspect %s", relative, status, path)
			}
			if observed["completedActivityCount"] != float64(len(activities)) {
				return fmt.Errorf("run completed with an unexpected activity count")
			}
			fmt.Printf("Verified %s: %s, %d/%d activities\n", relative, status, len(activities), len(activities))
			return nil
		}
		time.Sleep(time.Second)
	}
	return fmt.Errorf("run %s is still live; inspect it before starting another execution", runID)
}
