// Command catalog emits the complete runnable showcase CI matrix from workflow files.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
	"strings"
)

type entry struct {
	Category   string `json:"category"`
	Showcase   string `json:"showcase"`
	Image      string `json:"image"`
	Validation string `json:"validation"`
}

func main() {
	root := flag.String("root", ".", "examples checkout")
	format := flag.String("format", "json", "json CI matrix or markdown local command table")
	flag.Parse()
	entries, err := discover(*root)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if *format == "markdown" {
		fmt.Println("| Example | Local command (from the repository root) |")
		fmt.Println("| --- | --- |")
		for _, entry := range entries {
			path := entry.Category + "/" + entry.Showcase
			title := strings.ReplaceAll(entry.Showcase, "-", " ")
			if readme, err := os.ReadFile(filepath.Join(*root, path, "README.md")); err == nil {
				title = strings.TrimPrefix(strings.SplitN(string(readme), "\n", 2)[0], "# ")
			}
			fmt.Printf("| [%s](%s/README.md) | `(cd %s && ./prepare.sh && ./run.sh)` |\n", title, path, path)
		}
		return
	}
	if err := json.NewEncoder(os.Stdout).Encode(entries); err != nil {
		panic(err)
	}
}
func discover(root string) ([]entry, error) {
	entries := []entry{}
	for _, category := range []string{"scientific-workflows", "scientific-ai", "machine-learning", "generative-ai", "agentic-workflows", "document-ai", "media", "rendering"} {
		directories, err := os.ReadDir(filepath.Join(root, category))
		if err != nil {
			return nil, err
		}
		for _, directory := range directories {
			if !directory.IsDir() {
				continue
			}
			bundle := filepath.Join(root, category, directory.Name())
			if _, err := os.Stat(filepath.Join(bundle, "docker/Dockerfile")); os.IsNotExist(err) {
				continue
			}
			data, err := os.ReadFile(filepath.Join(bundle, "workflow.yaml"))
			if err != nil {
				return nil, err
			}
			var workflow struct {
				Spec struct {
					Image      string `yaml:"image"`
					Activities []struct {
						Command struct {
							Entrypoint string   `yaml:"entrypoint"`
							Arguments  []string `yaml:"arguments"`
						} `yaml:"command"`
					} `yaml:"activities"`
				} `yaml:"spec"`
			}
			if err := yaml.Unmarshal(data, &workflow); err != nil {
				return nil, err
			}
			if workflow.Spec.Image == "" || len(workflow.Spec.Activities) == 0 {
				return nil, fmt.Errorf("incomplete workflow: %s", bundle)
			}
			for _, a := range workflow.Spec.Activities {
				if a.Command.Entrypoint == "" || a.Command.Entrypoint == "docker" || strings.Contains(strings.Join(a.Command.Arguments, " "), "docker run") {
					return nil, fmt.Errorf("invalid runtime-owned command in %s", bundle)
				}
			}
			info, err := os.Stat(filepath.Join(bundle, "run.sh"))
			if err != nil || info.Mode()&0111 == 0 {
				return nil, fmt.Errorf("missing executable runner: %s", bundle)
			}
			validation := "full"
			if raw, err := os.ReadFile(filepath.Join(bundle, "data/input.json")); err == nil {
				var config struct {
					Mode string `json:"ciValidation"`
				}
				if err := json.Unmarshal(raw, &config); err != nil {
					return nil, err
				}
				if config.Mode == "image-and-contract" {
					validation = "image-and-contract"
				}
			}
			entries = append(entries, entry{category, directory.Name(), workflow.Spec.Image, validation})
		}
	}
	if len(entries) == 0 {
		return nil, fmt.Errorf("no runnable showcases found")
	}
	return entries, nil
}
