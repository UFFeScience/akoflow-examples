package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestRejectsContractDriftBeforeDeletingOutputs(t *testing.T) {
	root := t.TempDir()
	for _, dir := range []string{"data", "outputs"} {
		if err := os.Mkdir(filepath.Join(root, dir), 0755); err != nil {
			t.Fatal(err)
		}
	}
	os.WriteFile(filepath.Join(root, "outputs/keep"), []byte("prior evidence"), 0644)
	os.WriteFile(filepath.Join(root, "data/input.json"), []byte(`{"stages":["start","left","right"],"dependencies":{"start":[],"left":["start"],"right":["start"]}}`), 0644)
	os.WriteFile(filepath.Join(root, "workflow.yaml"), []byte("  activities:\n    - name: start\n    - name: left\n      dependsOn: [\"start\"]\n    - name: right\n      dependsOn: [\"left\"]\n"), 0644)
	err := run(root)
	if err == nil || !strings.Contains(err.Error(), "dependency mismatch: right") {
		t.Fatalf("expected drift error, got %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "outputs/keep")); err != nil {
		t.Fatal("validation removed prior evidence")
	}
}

func TestExecutesForkJoinWithConcurrentSiblings(t *testing.T) {
	root := t.TempDir()
	for _, dir := range []string{"data", "scripts"} {
		if err := os.Mkdir(filepath.Join(root, dir), 0755); err != nil {
			t.Fatal(err)
		}
	}
	config := `{"stages":["start","left","right","join"],"dependencies":{"start":[],"left":["start"],"right":["start"],"join":["left","right"]}}`
	os.WriteFile(filepath.Join(root, "data/input.json"), []byte(config), 0644)
	workflow := "  activities:\n    - name: start\n    - name: left\n      dependsOn: [\"start\"]\n    - name: right\n      dependsOn: [\"start\"]\n    - name: join\n      dependsOn: [\"left\",\"right\"]\n"
	os.WriteFile(filepath.Join(root, "workflow.yaml"), []byte(workflow), 0644)
	script := `import argparse, pathlib, time
p=argparse.ArgumentParser(); p.add_argument('--stage'); p.add_argument('--output'); a=p.parse_args()
out=pathlib.Path(a.output); out.mkdir(exist_ok=True)
if a.stage in ('left','right'):
    assert (out/'stage-start.json').exists()
    (out/('ready-'+a.stage)).touch()
    sibling='right' if a.stage=='left' else 'left'
    deadline=time.monotonic()+3
    while not (out/('ready-'+sibling)).exists():
        assert time.monotonic()<deadline, 'siblings were serialized'
        time.sleep(0.01)
if a.stage=='join':
    assert all((out/('stage-'+n+'.json')).exists() for n in ('left','right'))
(out/('stage-'+a.stage+'.json')).write_text('{}')
`
	os.WriteFile(filepath.Join(root, "scripts/run_showcase.py"), []byte(script), 0644)
	if err := run(root); err != nil {
		t.Fatal(err)
	}
	result, err := os.ReadFile(filepath.Join(root, "outputs/dag-validation.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(result), `"completedActivities": 4`) {
		t.Fatalf("incomplete execution: %s", result)
	}
}

func TestChildDoesNotWaitForUnrelatedBranch(t *testing.T) {
	config := scenario{Stages: []string{"fast", "slow", "child"}, Dependencies: map[string][]string{"fast": {}, "slow": {}, "child": {"fast"}}}
	childStarted := make(chan struct{})
	err := executeReady(config, 2, func(name string) error {
		if name == "child" {
			close(childStarted)
		}
		if name == "slow" {
			select {
			case <-childStarted:
			case <-time.After(2 * time.Second):
				return fmt.Errorf("an unrelated branch inserted an extra barrier")
			}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}
