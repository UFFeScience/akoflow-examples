package main

import (
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
	"testing"
)

func TestEnsembleDAGs(t *testing.T) {
	root := t.TempDir()
	for _, n := range []int{8, 16, 32} {
		bundle := filepath.Join("scientific-workflows", fmtSlug(n))
		for _, name := range []string{"prepare.sh", "run.sh", "validate.sh", "docker/Dockerfile"} {
			data, err := os.ReadFile(filepath.Join("../..", bundle, name))
			if err != nil {
				t.Fatal(err)
			}
			target := filepath.Join(root, bundle, name)
			if err = os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				t.Fatal(err)
			}
			if err = os.WriteFile(target, data, 0755); err != nil {
				t.Fatal(err)
			}
		}
		if err := generate(root, n, false); err != nil {
			t.Fatal(err)
		}
		if err := generate(root, n, true); err != nil {
			t.Fatal(err)
		}
		data, _ := os.ReadFile(filepath.Join(root, "scientific-workflows", fmtSlug(n), "workflow.yaml"))
		var d struct {
			Spec struct {
				Activities []struct {
					Name    string   `yaml:"name"`
					Parents []string `yaml:"dependsOn"`
				} `yaml:"activities"`
				Deps []struct {
					Producer string `yaml:"producerActivity"`
					Consumer string `yaml:"consumerActivity"`
					File     string `yaml:"logicalName"`
				} `yaml:"dataDependencies"`
			} `yaml:"spec"`
		}
		if err := yaml.Unmarshal(data, &d); err != nil {
			t.Fatal(err)
		}
		if len(d.Spec.Activities) != n+6 {
			t.Fatal("missing real activity", n)
		}
		parents := map[string][]string{}
		for _, a := range d.Spec.Activities {
			parents[a.Name] = a.Parents
		}
		if len(parents["aggregate"]) != n || len(parents["validate"]) != 3 {
			t.Fatal("fan-in or terminal validation missing")
		}
		for _, edge := range d.Spec.Deps {
			if _, ok := parents[edge.Producer]; !ok {
				t.Fatal("unknown producer")
			}
			if _, ok := parents[edge.Consumer]; !ok {
				t.Fatal("unknown consumer")
			}
			if edge.File == "" {
				t.Fatal("unnamed transfer")
			}
		}
	}
}
func fmtSlug(n int) string {
	if n == 8 {
		return "openoil-ensemble-08"
	}
	if n == 16 {
		return "openoil-ensemble-16"
	}
	return "openoil-ensemble-32"
}
