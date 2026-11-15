// Command openoil materializes the three reproducible OpenOil Docker workflow bundles.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
	"regexp"
)

const baselineImage = "ghcr.io/uffescience/openoil-ensemble@sha256:267348059d11049d42458ab2e3a30cedb4efa143b619f60686d44525f1bba19a"

func main() {
	root := flag.String("root", ".", "examples checkout")
	check := flag.Bool("check", false, "verify generated workflow files")
	flag.Parse()
	for _, count := range []int{8, 16, 32} {
		if err := generate(*root, count, *check); err != nil {
			panic(err)
		}
	}
}
func generate(root string, count int, check bool) error {
	image := baselineImage
	cores, memory := 2, int64(12884901888)
	if count == 32 {
		cores, memory = 4, 17179869184
		image = "ghcr.io/uffescience/openoil-ensemble@sha256:9939dcaa4c26b62ce5496f46f3946d26f0ad1168fbfe1c5acd13b3385fd25b6e"
	}
	slug := fmt.Sprintf("openoil-ensemble-%02d", count)
	dir := filepath.Join(root, "scientific-workflows", slug)
	if err := os.MkdirAll(filepath.Join(dir, "docker"), 0755); err != nil {
		return err
	}
	os.MkdirAll(filepath.Join(dir, "data"), 0755)
	runtime := slug + "-local"
	activities := []map[string]any{}
	deps := []map[string]any{}
	add := func(name string, parents []string) {
		activities = append(activities, map[string]any{"name": name, "dependsOn": parents, "runtime": runtime, "cpuLimit": "1", "memoryLimit": "4Gi", "command": map[string]any{"entrypoint": "python", "arguments": []string{"/opt/openoil/workflow.py", "--stage", name, "--members", fmt.Sprint(count)}}})
	}
	edge := func(producer, consumer string, files ...string) {
		for _, file := range files {
			deps = append(deps, map[string]any{"producerActivity": producer, "consumerActivity": consumer, "logicalName": file, "sizeBytes": 1_000_000})
		}
	}
	add("prepare", []string{})
	members := []string{}
	for i := 0; i < count; i++ {
		name := fmt.Sprintf("member-%03d", i)
		members = append(members, name)
		add(name, []string{"prepare"})
		edge("prepare", name, "parameters.json", "scenario.json")
	}
	add("aggregate", members)
	edge("prepare", "aggregate", "scenario.json", "parameters.json")
	for i, name := range members {
		edge(name, "aggregate", fmt.Sprintf("membro_%03d.nc", i), "profile-"+name+".json")
	}
	for _, name := range []string{"map", "summary", "animate"} {
		add(name, []string{"aggregate"})
		edge("prepare", name, "scenario.json", "parameters.json")
		edge("aggregate", name, "summary.json")
	}
	edge("aggregate", "map", "probability.nc")
	edge("aggregate", "summary", "mass_balance.csv", "arrival.csv", "perfil_tarefas.csv")
	edge("aggregate", "animate", "selected-member.nc")
	add("validate", []string{"map", "summary", "animate"})
	edge("prepare", "validate", "scenario.json", "parameters.json", "profile-prepare.json")
	edge("aggregate", "validate", "summary.json", "probability.nc", "mass_balance.csv", "arrival.csv", "perfil_tarefas.csv", "selected-member.nc", "profile-aggregate.json")
	for i, name := range members {
		edge(name, "validate", fmt.Sprintf("membro_%03d.nc", i), "profile-"+name+".json")
	}
	edge("map", "validate", "mapa_probabilidade.png", "profile-map.json")
	edge("summary", "validate", "resumo_workflow.png", "profile-summary.json")
	edge("animate", "validate", "animacao.gif", "profile-animate.json")
	workflow := map[string]any{"name": slug, "spec": map[string]any{"namespace": "oil", "image": image, "activities": activities, "dataDependencies": deps}}
	env := map[string]any{"environment": map[string]any{"id": slug, "name": fmt.Sprintf("OpenOil %d members · homeserver Docker", count), "description": "Real CPU OpenOil ensemble with synthetic constant forcings; no cloud resources", "status": "ready"}, "version": map[string]any{"id": slug + "-v1", "environmentId": slug, "version": 1, "status": "published", "networkModel": "local", "interferenceModel": "none", "costModel": "free", "configurationHash": slug + "-v1"}, "runtimes": []any{map[string]any{"environmentVersionId": slug + "-v1", "id": runtime, "name": "Local Docker host", "driver": "local", "mode": "execution", "role": "compute", "capabilities": map[string]bool{"batch": true, "container": true}}}, "resources": []any{map[string]any{"id": slug + "-docker", "environmentVersionId": slug + "-v1", "type": "machine", "name": "Local Docker host", "providerId": "local-docker", "cpuCores": cores, "cpuCapacity": cores, "memoryBytes": memory, "storageBytes": 42949672960, "computeSpeedup": 1, "pricePerSecond": 0, "bootOverheadSeconds": 0, "containerOverheadSeconds": 0, "schedulable": true}}, "storages": []any{}, "connections": []any{}, "activityResourceProfiles": []any{}, "resourceRuntimeBindings": []any{map[string]any{"resourceId": slug + "-docker", "runtimeId": runtime, "enabled": true}}}
	scope := map[string]any{"id": slug + "-scope", "name": slug + " local scope", "environmentVersionIds": []string{slug + "-v1"}}
	topology := map[string]any{"id": slug + "-topology", "name": slug + " local topology", "version": 1, "executionScopeId": slug + "-scope", "links": []any{}}
	for name, value := range map[string]any{"workflow.yaml": workflow, "environment.yaml": env, "scope.yaml": scope, "topology.yaml": topology} {
		data, err := yaml.Marshal(value)
		if err != nil {
			return err
		}
		target := filepath.Join(dir, name)
		if check {
			old, err := os.ReadFile(target)
			if err != nil || string(old) != string(data) {
				return fmt.Errorf("stale bundle %s", target)
			}
		} else if err := os.WriteFile(target, data, 0644); err != nil {
			return err
		}
	}
	config, _ := json.MarshalIndent(map[string]any{"slug": slug, "members": count, "ciValidation": "image-and-contract", "stages": []string{}, "syntheticForcings": true}, "", "  ")
	if !check {
		os.WriteFile(filepath.Join(dir, "data/input.json"), append(config, '\n'), 0644)
	}
	for _, name := range []string{"prepare.sh", "run.sh", "validate.sh", "docker/Dockerfile"} {
		path := filepath.Join(dir, name)
		source, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		pattern := regexp.MustCompile(`ghcr.io/uffescience/openoil-ensemble@sha256:[a-f0-9]{64}`)
		if !pattern.Match(source) {
			return fmt.Errorf("missing pinned image in %s", path)
		}
		expected := pattern.ReplaceAllString(string(source), image)
		if check && expected != string(source) {
			return fmt.Errorf("stale companion image in %s", path)
		}
		if !check {
			if err := os.WriteFile(path, []byte(expected), 0755); err != nil {
				return err
			}
		}
	}
	return nil
}
