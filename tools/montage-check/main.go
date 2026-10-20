// Command montage-check validates the complete native Montage contract or its computed final images.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"image/png"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

func main() {
	root := flag.String("root", ".", "Montage bundle")
	definition := flag.Bool("definition", false, "validate all source commands and pinned image without executing the long workload")
	flag.Parse()
	if err := validate(*root, *definition); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func validate(root string, definitionOnly bool) error {
	raw, err := os.ReadFile(filepath.Join(root, "data/input.json"))
	if err != nil {
		return err
	}
	var config struct {
		Stages    []string `json:"stages"`
		Artifacts []string `json:"artifacts"`
		Upstream  string   `json:"upstreamImage"`
	}
	if err := json.Unmarshal(raw, &config); err != nil {
		return err
	}
	raw, err = os.ReadFile(filepath.Join(root, "workflow.yaml"))
	if err != nil {
		return err
	}
	var workflow struct {
		Spec struct {
			Activities []struct {
				Name    string `yaml:"name"`
				Runtime string `yaml:"runtime"`
				Command struct {
					Entrypoint string   `yaml:"entrypoint"`
					Arguments  []string `yaml:"arguments"`
				} `yaml:"command"`
			} `yaml:"activities"`
			DataDependencies []map[string]any `yaml:"dataDependencies"`
		} `yaml:"spec"`
	}
	if err := yaml.Unmarshal(raw, &workflow); err != nil {
		return err
	}
	if len(config.Stages) != 58 || len(workflow.Spec.Activities) != 58 || len(workflow.Spec.DataDependencies) != 138 {
		return fmt.Errorf("the original 58-activity / 138-handoff contract was changed")
	}
	inputs := []string{}
	for index, a := range workflow.Spec.Activities {
		if a.Name != config.Stages[index] || a.Runtime != "montage-050-local-local" {
			return fmt.Errorf("activity %s is not in the original local DAG", a.Name)
		}
		if a.Command.Entrypoint == "mProject" {
			inputs = append(inputs, "/akoflow-wfa-shared/"+a.Command.Arguments[1])
		}
	}
	if len(inputs) != 12 {
		return fmt.Errorf("expected twelve original FITS projections")
	}
	if definitionOnly {
		args := []string{"run", "--rm", "--network", "none", "--platform", "linux/amd64", "--entrypoint", "sh", config.Upstream, "-c", `for command in mProject mDiffFit mConcatFit mBgModel mBackground mImgtbl mAdd mViewer; do command -v "$command" >/dev/null || exit 1; done; for file do test -s "$file" || exit 1; done`, "montage-input-check"}
		args = append(args, inputs...)
		if logs, err := exec.Command("docker", args...).CombinedOutput(); err != nil {
			return fmt.Errorf("pinned image contract: %w: %s", err, logs)
		}
		evidence := map[string]any{"image": config.Upstream, "activities": 58, "handoffs": 138, "fitsInputs": 12, "validatedAt": time.Now().UTC().Format(time.RFC3339), "fullExecutionPerformed": false}
		bytes, err := json.MarshalIndent(evidence, "", "  ")
		if err != nil {
			return err
		}
		if err := os.MkdirAll(filepath.Join(root, "evidence"), 0755); err != nil {
			return err
		}
		if err := os.WriteFile(filepath.Join(root, "evidence/image-contract.json"), append(bytes, '\n'), 0644); err != nil {
			return err
		}
		fmt.Println("Validated Montage 050d source/image contract: 58 native activities, 138 handoffs, 12 FITS inputs (full execution not performed)")
		return nil
	}
	manifest, err := os.ReadFile(filepath.Join(root, "outputs/manifest.json"))
	if err != nil {
		return err
	}
	var observed struct {
		Status string   `json:"status"`
		Stages []string `json:"stages"`
	}
	if err := json.Unmarshal(manifest, &observed); err != nil {
		return err
	}
	if observed.Status != "success" || len(observed.Stages) != 58 {
		return fmt.Errorf("Montage has not completed all 58 local activities")
	}
	for _, name := range config.Artifacts {
		path := filepath.Join(root, "outputs", name)
		if strings.HasSuffix(name, ".fits") {
			file, err := os.Open(path)
			if err != nil {
				return err
			}
			header := make([]byte, 2880)
			_, err = file.Read(header)
			file.Close()
			if err != nil {
				return err
			}
			if !strings.HasPrefix(string(header), "SIMPLE") {
				return fmt.Errorf("invalid FITS file: %s", name)
			}
			dimensions := map[string]int{}
			for start := 0; start+80 <= len(header); start += 80 {
				card := string(header[start : start+80])
				key := strings.TrimSpace(card[:8])
				if key == "NAXIS1" || key == "NAXIS2" {
					value := strings.TrimSpace(strings.SplitN(card[10:], "/", 2)[0])
					parsed, err := strconv.Atoi(value)
					if err != nil {
						return err
					}
					dimensions[key] = parsed
				}
			}
			if dimensions["NAXIS1"] != 1800 || dimensions["NAXIS2"] != 1800 {
				return fmt.Errorf("unexpected mosaic dimensions: %s: %v", name, dimensions)
			}
		} else if strings.HasSuffix(name, ".png") {
			file, err := os.Open(path)
			if err != nil {
				return err
			}
			image, err := png.DecodeConfig(file)
			file.Close()
			if err != nil {
				return err
			}
			if image.Width != 1800 || image.Height != 1800 {
				return fmt.Errorf("unexpected PNG dimensions: %s", name)
			}
		}
	}
	fmt.Println("Validated Montage: all 58 activities, three 1800x1800 FITS mosaics and four PNG previews")
	return nil
}
