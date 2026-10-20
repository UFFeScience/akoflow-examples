// Command showcase executes contract fixtures by dependency waves, never by list order.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"regexp"
	"strings"
	"sync"
)

type scenario struct {
	Stages       []string            `json:"stages"`
	Dependencies map[string][]string `json:"dependencies"`
}

func main() {
	root := flag.String("root", ".", "showcase directory")
	flag.Parse()
	if err := run(*root); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(root string) error {
	data, err := os.ReadFile(filepath.Join(root, "data/input.json"))
	if err != nil {
		return err
	}
	var config scenario
	if err = json.Unmarshal(data, &config); err != nil {
		return err
	}
	workflow, err := os.ReadFile(filepath.Join(root, "workflow.yaml"))
	if err != nil {
		return err
	}
	blocks := regexp.MustCompile(`(?m)^    - name: `).Split(string(workflow), -1)[1:]
	if len(blocks) != len(config.Stages) {
		return fmt.Errorf("workflow activity count differs from contract")
	}
	known := map[string]bool{}
	for i, block := range blocks {
		name := strings.SplitN(block, "\n", 2)[0]
		if name != config.Stages[i] || known[name] {
			return fmt.Errorf("activity mismatch or duplicate: %s", name)
		}
		known[name] = true
		dependencies := []string{}
		match := regexp.MustCompile(`(?m)^      dependsOn: (.+)$`).FindStringSubmatch(block)
		if len(match) > 0 {
			if err := json.Unmarshal([]byte(match[1]), &dependencies); err != nil {
				return err
			}
		}
		if !reflect.DeepEqual(dependencies, config.Dependencies[name]) {
			return fmt.Errorf("dependency mismatch: %s", name)
		}
	}
	for name, deps := range config.Dependencies {
		for _, dep := range deps {
			if !known[dep] || name == dep {
				return fmt.Errorf("invalid dependency %s -> %s", dep, name)
			}
		}
	}
	// Remove only this fixture's generated output directory, after validating its contract.
	output := filepath.Join(root, "outputs")
	if err = os.RemoveAll(output); err != nil {
		return err
	}
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
			return fmt.Errorf("dependency cycle or missing contract")
		}
		var wg sync.WaitGroup
		failures := make(chan error, len(ready))
		for _, name := range ready {
			wg.Add(1)
			go func(name string) {
				defer wg.Done()
				cmd := exec.Command("python3", filepath.Join(root, "scripts/run_showcase.py"), "--stage", name, "--output", output)
				if result, err := cmd.CombinedOutput(); err != nil {
					failures <- fmt.Errorf("%s: %w: %s", name, err, result)
				}
			}(name)
		}
		wg.Wait()
		close(failures)
		for err := range failures {
			return err
		}
		for _, name := range ready {
			completed[name] = true
		}
		waves = append(waves, ready)
	}
	report := struct {
		Mode  string     `json:"mode"`
		Waves [][]string `json:"dependencyWaves"`
		Count int        `json:"completedActivities"`
	}{"contract-fixture", waves, len(completed)}
	result, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(output, "dag-validation.json"), append(result, '\n'), 0644)
}
