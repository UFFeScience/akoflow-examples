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
)

func main() {
	root := flag.String("root", ".", "GAWA bundle")
	definition := flag.Bool("definition", false, "check image and DAG without executing the scientific workload")
	flag.Parse()
	if err := check(*root, *definition); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func check(root string, definition bool) error {
	raw, err := os.ReadFile(filepath.Join(root, "workflow.yaml"))
	if err != nil {
		return err
	}
	var workflow struct {
		Spec struct {
			Activities []struct {
				Name      string   `yaml:"name"`
				DependsOn []string `yaml:"dependsOn"`
			} `yaml:"activities"`
		} `yaml:"spec"`
	}
	if err = yaml.Unmarshal(raw, &workflow); err != nil {
		return err
	}
	activities := workflow.Spec.Activities
	if len(activities) != 16 || activities[0].Name != "prepare" || activities[15].Name != "merge" {
		return fmt.Errorf("expected prepare, fourteen tile tasks and merge")
	}
	for i := 0; i < 14; i++ {
		a := activities[i+1]
		dep := "prepare"
		if i >= 4 {
			dep = fmt.Sprintf("tile-%03d", i-4)
		}
		if a.Name != fmt.Sprintf("tile-%03d", i) || len(a.DependsOn) != 1 || a.DependsOn[0] != dep {
			return fmt.Errorf("invalid four-chain tile contract: %s", a.Name)
		}
	}
	if len(activities[15].DependsOn) != 14 {
		return fmt.Errorf("merge must depend on every tile")
	}
	if definition {
		code := `import shutil; from astropy.table import Table; from lib.tile_tasks import run_gawa_tile_job; assert len(Table.read('/data/output_ref/tiles_specs.fits')) == 14; assert len(Table.read('/data/output_ref/clusters.fits')) == 67; assert shutil.which('mr_filter'); assert callable(run_gawa_tile_job); import gawa_tasks, gawa_validate; print('GAWA image and 16-activity contract validated; no scientific execution performed')`
		cmd := exec.Command("docker", "run", "--rm", "--network", "none", "--entrypoint", "conda", "akoflow-local/gawa:workload", "run", "--no-capture-output", "-n", "gawa", "python", "-c", code)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("image contract: %w: %s", err, output)
		}
		fmt.Print(string(output))
		return nil
	}
	path := filepath.Join(root, "outputs/results/validation.json")
	if _, err := os.Stat(path); os.IsNotExist(err) {
		path = filepath.Join(root, "outputs/validation.json")
	}
	raw, err = os.ReadFile(path)
	if err != nil {
		return err
	}
	var result struct {
		Validation string `json:"validation"`
		Tiles      int    `json:"tilesCompleted"`
		Candidates int    `json:"candidateCount"`
	}
	if err = json.Unmarshal(raw, &result); err != nil {
		return err
	}
	if result.Validation != "passed" || result.Tiles != 14 || result.Candidates != 67 {
		return fmt.Errorf("GAWA fixture validation failed")
	}
	image, err := os.Open(filepath.Join(filepath.Dir(path), "catalog-preview.png"))
	if err != nil {
		return err
	}
	defer image.Close()
	config, err := png.DecodeConfig(image)
	if err != nil || config.Width < 100 || config.Height < 100 {
		return fmt.Errorf("invalid catalog preview")
	}
	fmt.Println("Validated GAWA result: 14 completed tiles, 67 candidates and readable PNG preview")
	return nil
}
