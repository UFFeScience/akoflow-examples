// Command openoil-chain executes and verifies OpenOil workflows serially on the local daemon.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

func main() {
	root := flag.String("root", ".", "examples checkout")
	env := flag.String("env-file", "", "protected daemon environment file")
	api := flag.String("api", "http://192.168.1.13:8080/akoflow-api", "daemon origin")
	flag.Parse()
	if *env == "" {
		panic("env-file required")
	}
	for _, n := range []int{8, 16, 32} {
		relative := fmt.Sprintf("scientific-workflows/openoil-ensemble-%02d", n)
		path := filepath.Join(*root, relative, "evidence/daemon-run.json")
		var record struct {
			RunID      string `json:"runId"`
			Status     string `json:"status"`
			Projection struct {
				Workspaces []struct {
					ActivityID string `json:"activityId"`
					Path       string `json:"executionPath"`
				} `json:"workspaces"`
			} `json:"projection"`
		}
		raw, err := os.ReadFile(path)
		if err == nil {
			if err = json.Unmarshal(raw, &record); err != nil {
				panic(err)
			}
			if record.Status == "failed" || record.Status == "cancelled" {
				panic("inspect existing failed run before retrying: " + record.RunID)
			}
		} else if !os.IsNotExist(err) {
			panic(err)
		}
		if record.RunID == "" {
			run(*root, "go", "run", "./tools/daemon-local", "-root", *root, "-example", relative, "-api-url", *api, "-env-file", *env, "-registry-image", "-wait=false", "-name-prefix", "oilv1-")
		}
		run(*root, "go", "run", "./tools/daemon-local", "-root", *root, "-example", relative, "-api-url", *api, "-env-file", *env, "-observe", "-wait-timeout", "4h")
		raw, err = os.ReadFile(path)
		if err != nil {
			panic(err)
		}
		if err = json.Unmarshal(raw, &record); err != nil {
			panic(err)
		}
		found := false
		for _, workspace := range record.Projection.Workspaces {
			if !strings.HasSuffix(workspace.ActivityID, "-validate") {
				continue
			}
			if !strings.HasPrefix(workspace.Path, "/akoflow/workspace/runs/") {
				panic("unexpected workspace path")
			}
			data, err := exec.Command("docker", "exec", "akoflow-platform-server-1", "cat", workspace.Path+"/manifest.json").Output()
			if err != nil {
				panic(err)
			}
			var result struct {
				Status   string `json:"status"`
				Showcase string `json:"showcase"`
			}
			if err = json.Unmarshal(data, &result); err != nil {
				panic(err)
			}
			if result.Status != "success" || result.Showcase != fmt.Sprintf("openoil-ensemble-%02d", n) {
				panic("scientific output validation did not pass")
			}
			found = true
		}
		if !found {
			panic("validated final workspace missing")
		}
		fmt.Printf("CHAIN VERIFIED %d members: %s at %s\n", n, record.RunID, time.Now().UTC().Format(time.RFC3339))
	}
	fmt.Println("CHAIN COMPLETE: 8 -> 16 -> 32 members, every real run and output validator passed")
}
func run(dir, name string, args ...string) {
	command := exec.Command(name, args...)
	command.Dir = dir
	command.Env = os.Environ()
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr
	if err := command.Run(); err != nil {
		panic(err)
	}
}
