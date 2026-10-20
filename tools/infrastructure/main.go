// Command infrastructure normalizes local-only showcase infrastructure and runtime bindings.
package main

import (
	"bytes"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	root := flag.String("root", ".", "examples checkout")
	flag.Parse()
	if err := generate(*root); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func generate(root string) error {
	for _, category := range []string{"scientific-workflows", "scientific-ai", "machine-learning", "generative-ai", "agentic-workflows", "document-ai", "media", "rendering"} {
		files, err := filepath.Glob(filepath.Join(root, category, "*", "workflow.yaml"))
		if err != nil {
			return err
		}
		for _, file := range files {
			raw, err := os.ReadFile(file)
			if err != nil {
				return err
			}
			var definition map[string]any
			if err := yaml.Unmarshal(raw, &definition); err != nil {
				return err
			}
			name, ok := definition["name"].(string)
			if !ok {
				return fmt.Errorf("missing workflow name: %s", file)
			}
			spec := definition["spec"].(map[string]any)
			runtimeID := name + "-local"
			resourceID := name + "-local-docker"
			versionID := name + "-v1"
			for _, rawActivity := range spec["activities"].([]any) {
				activity := rawActivity.(map[string]any)
				activity["runtime"] = runtimeID
				command := activity["command"].(map[string]any)
				delete(command, "workingDirectory")
				if strings.Contains(file, "model-conversion") || strings.Contains(file, "training-with-mlflow") {
					activity["memoryLimit"] = "1Gi"
				}
			}
			var buffer bytes.Buffer
			encoder := yaml.NewEncoder(&buffer)
			encoder.SetIndent(2)
			if err := encoder.Encode(definition); err != nil {
				return err
			}
			encoder.Close()
			if err := os.WriteFile(file, buffer.Bytes(), 0644); err != nil {
				return err
			}
			environment := fmt.Sprintf(`environment:
  id: %s
  name: %s local Docker
  description: CPU-only local execution; no remote capacity is provisioned
  status: ready
version:
  id: %s
  environmentId: %s
  version: 1
  status: published
  networkModel: local
  interferenceModel: none
  costModel: free
  configurationHash: %s
runtimes:
  - environmentVersionId: %s
    id: %s
    name: Local Docker host
    driver: local
    mode: execution
    role: compute
    capabilities: {batch: true, container: true}
resources:
  - id: %s
    environmentVersionId: %s
    type: machine
    name: Local Docker host
    providerId: local-docker
    cpuCores: 4
    cpuCapacity: 4
    memoryBytes: 8589934592
    storageBytes: 21474836480
    computeSpeedup: 1
    pricePerSecond: 0
    bootOverheadSeconds: 0
    containerOverheadSeconds: 0
    schedulable: true
storages: []
connections: []
activityResourceProfiles: []
resourceRuntimeBindings:
  - {resourceId: %s, runtimeId: %s, enabled: true}
`, name, name, versionID, name, versionID, versionID, runtimeID, resourceID, versionID, resourceID, runtimeID)
			if strings.Contains(file, "montage-050") {
				environment = strings.Replace(environment, "cpuCapacity: 4", "cpuCapacity: 2", 1)
			}
			if err := os.WriteFile(filepath.Join(filepath.Dir(file), ".dockerignore"), []byte("*\n!data/\n!data/**\n!scripts/\n!scripts/**\n!requirements.txt\n!docker/\n!docker/Dockerfile\n"), 0644); err != nil {
				return err
			}
			scope := fmt.Sprintf("id: %s-scope\nname: %s local scope\nenvironmentVersionIds: [%s]\n", name, name, versionID)
			topology := fmt.Sprintf("id: %s-topology\nname: %s local topology\nversion: 1\nexecutionScopeId: %s-scope\nlinks: []\n", name, name, name)
			for filename, content := range map[string]string{"environment.yaml": environment, "scope.yaml": scope, "topology.yaml": topology} {
				if err := os.WriteFile(filepath.Join(filepath.Dir(file), filename), []byte(content), 0644); err != nil {
					return err
				}
			}
		}
	}
	return nil
}
