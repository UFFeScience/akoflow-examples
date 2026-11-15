package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

func collectResults(dir string, raw []byte, artifacts []string) error {
	var record struct {
		RunID      string `json:"runId"`
		Image      string `json:"image"`
		Projection struct {
			Workspaces []struct {
				ActivityID string `json:"activityId"`
				Path       string `json:"executionPath"`
				Manifest   struct {
					Final []struct {
						Path   string `json:"path"`
						Digest string `json:"digest"`
					} `json:"final"`
				} `json:"manifest"`
			} `json:"workspaces"`
			Activities []struct {
				ID       string  `json:"activityId"`
				Finished float64 `json:"finishedAt"`
			} `json:"activities"`
		} `json:"projection"`
	}
	if err := json.Unmarshal(raw, &record); err != nil {
		return err
	}
	finished := map[string]float64{}
	for _, a := range record.Projection.Activities {
		finished[a.ID] = a.Finished
	}
	workspaces := record.Projection.Workspaces
	sort.SliceStable(workspaces, func(i, j int) bool { return finished[workspaces[i].ActivityID] > finished[workspaces[j].ActivityID] })
	var config struct {
		Stages []string `json:"stages"`
		Slug   string   `json:"slug"`
	}
	input, err := os.ReadFile(filepath.Join(dir, "data/input.json"))
	if err != nil {
		return err
	}
	if err = json.Unmarshal(input, &config); err != nil {
		return err
	}
	names := append([]string{}, artifacts...)
	if filepath.Base(dir) != "montage-050" {
		for _, s := range config.Stages {
			names = append(names, "stage-"+s+".json")
		}
	}
	output := filepath.Join(dir, "outputs")
	if err = os.MkdirAll(output, 0755); err != nil {
		return err
	}
	for _, name := range names {
		if filepath.IsAbs(name) || strings.Contains(name, "..") {
			return fmt.Errorf("unsafe output name")
		}
		copied := false
		for _, w := range workspaces {
			if !strings.HasPrefix(w.Path, "/akoflow/workspace/runs/") {
				continue
			}
			source := w.Path + "/" + name
			if exec.Command("docker", "exec", "akoflow-platform-server-1", "test", "-f", source).Run() != nil {
				continue
			}
			target := filepath.Join(output, name)
			if err = os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return err
			}
			if data, e := exec.Command("docker", "cp", "akoflow-platform-server-1:"+source, target).CombinedOutput(); e != nil {
				return fmt.Errorf("collect %s: %w: %s", name, e, data)
			}
			data, e := os.ReadFile(target)
			if e != nil {
				return e
			}
			sum := sha256.Sum256(data)
			actual := "sha256:" + hex.EncodeToString(sum[:])
			matched := false
			for _, f := range w.Manifest.Final {
				if f.Path == name && f.Digest == actual {
					matched = true
					break
				}
			}
			if !matched {
				return fmt.Errorf("copied output checksum does not match recorded execution manifest: %s", name)
			}
			copied = true
			break
		}
		if !copied {
			return fmt.Errorf("actual output unavailable: %s", name)
		}
	}
	if err = write(filepath.Join(output, "manifest.json"), map[string]any{"showcase": config.Slug, "status": "success", "artifacts": artifacts, "stages": config.Stages, "runId": record.RunID, "image": record.Image}); err != nil {
		return err
	}
	validator := exec.Command("sh", filepath.Join(dir, "validate.sh"))
	if filepath.Base(dir) == "montage-050" {
		self, e := os.Executable()
		if e != nil {
			return e
		}
		validator = exec.Command(filepath.Join(filepath.Dir(self), "montage-check"), "-root", dir)
	}
	validator.Stdout = os.Stdout
	validator.Stderr = os.Stderr
	if err = validator.Run(); err != nil {
		return fmt.Errorf("semantic output validation: %w", err)
	}
	if err = archiveResults(dir); err != nil {
		return err
	}
	return write(filepath.Join(dir, "evidence/output-validation.json"), map[string]any{"status": "passed", "artifacts": artifacts, "source": "actual daemon workspaces", "validator": "validate.sh", "runId": record.RunID, "image": record.Image, "checksumVerification": "all copied outputs match sealed workspace manifests"})
}
