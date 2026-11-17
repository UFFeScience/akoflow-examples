package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

var sampleEntries = []entry{
	{Category: "scientific-workflows", Showcase: "opendronemap"},
	{Category: "scientific-workflows", Showcase: "other"},
	{Category: "media", Showcase: "video-intelligence"},
}

func TestEntriesForPaths(t *testing.T) {
	tests := []struct {
		name  string
		paths []string
		want  []entry
	}{
		{"one nested change", []string{"scientific-workflows/opendronemap/scripts/run.py"}, sampleEntries[:1]},
		{"multiple workflows deduplicated", []string{"scientific-workflows/opendronemap/workflow.yaml", "media/video-intelligence/run.sh", "scientific-workflows/opendronemap/README.md"}, []entry{sampleEntries[0], sampleEntries[2]}},
		{"shared tools do not rebuild images", []string{"tools/showcase/main.go", "go.mod", "experiments/test_inputs.py", "workloads/shared.py", ".github/workflows/checks.yml", "README.md"}, []entry{}},
		{"directory boundary", []string{"scientific-workflows/opendronemap-backup/run.sh"}, []entry{}},
		{"deleted example absent from catalog", []string{"scientific-workflows/deleted/workflow.yaml"}, []entry{}},
		{"empty selection", nil, []entry{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := entriesForPaths(sampleEntries, tt.paths)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("got %v, want %v", got, tt.want)
			}
			if len(got) == 0 {
				data, _ := json.Marshal(got)
				if string(data) != "[]" {
					t.Fatalf("empty matrix must be [], got %s", data)
				}
			}
		})
	}
}

func TestChangedEntriesUsesPRMergeBase(t *testing.T) {
	root, base := fixtureRepository(t)
	gitTest(t, root, "checkout", "-b", "feature")
	writeFixture(t, root, "scientific-workflows/opendronemap/new.txt", "feature")
	commitFixture(t, root)
	gitTest(t, root, "checkout", "main")
	writeFixture(t, root, "scientific-workflows/other/new.txt", "base update")
	commitFixture(t, root)
	advancedBase := gitTest(t, root, "rev-parse", "HEAD")
	gitTest(t, root, "checkout", "feature")
	got, err := changedEntries(root, sampleEntries, advancedBase, true)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(got, sampleEntries[:1]) {
		t.Fatalf("base branch changes leaked into PR matrix: %v", got)
	}
	got, err = changedEntries(root, sampleEntries, base, false)
	if err != nil || !reflect.DeepEqual(got, sampleEntries[:1]) {
		t.Fatalf("push selection: %v, %v", got, err)
	}
}

func TestChangedEntriesIncludesEveryCommitAndBothRenamePaths(t *testing.T) {
	root, base := fixtureRepository(t)
	gitTest(t, root, "mv", "scientific-workflows/opendronemap/input.txt", "scientific-workflows/other/moved.txt")
	commitFixture(t, root)
	writeFixture(t, root, "media/video-intelligence/new.txt", "second commit")
	commitFixture(t, root)
	got, err := changedEntries(root, sampleEntries, base, false)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(got, sampleEntries) {
		t.Fatalf("multi-commit rename selection: %v", got)
	}
}

func TestChangedEntriesHandlesInitialPushAndInvalidRevision(t *testing.T) {
	root, _ := fixtureRepository(t)
	got, err := changedEntries(root, sampleEntries, "0000000000000000000000000000000000000000", false)
	if err != nil || !reflect.DeepEqual(got, sampleEntries) {
		t.Fatalf("initial push: %v, %v", got, err)
	}
	if _, err := changedEntries(root, sampleEntries, "missing-revision", false); err == nil {
		t.Fatal("invalid revision must fail instead of building everything")
	}
}

func TestChangedEntriesSkipsUnrelatedChangesAndDeletedExamples(t *testing.T) {
	root, base := fixtureRepository(t)
	writeFixture(t, root, "README.md", "documentation")
	commitFixture(t, root)
	got, err := changedEntries(root, sampleEntries, base, false)
	if err != nil || len(got) != 0 {
		t.Fatalf("unrelated changes: %v, %v", got, err)
	}
	base = gitTest(t, root, "rev-parse", "HEAD")
	gitTest(t, root, "rm", "scientific-workflows/opendronemap/input.txt")
	commitFixture(t, root)
	got, err = changedEntries(root, sampleEntries[1:], base, false)
	if err != nil || len(got) != 0 {
		t.Fatalf("deleted example: %v, %v", got, err)
	}
}

func fixtureRepository(t *testing.T) (string, string) {
	t.Helper()
	root := t.TempDir()
	gitTest(t, root, "init", "-b", "main")
	gitTest(t, root, "config", "user.name", "Catalog test")
	gitTest(t, root, "config", "user.email", "catalog@example.invalid")
	for _, item := range sampleEntries {
		writeFixture(t, root, item.Category+"/"+item.Showcase+"/input.txt", "original")
	}
	commitFixture(t, root)
	return root, gitTest(t, root, "rev-parse", "HEAD")
}

func gitTest(t *testing.T, root string, args ...string) string {
	t.Helper()
	output, err := gitOutput(root, args...)
	if err != nil {
		t.Fatal(err)
	}
	return output
}

func writeFixture(t *testing.T, root, path, contents string) {
	t.Helper()
	target := filepath.Join(root, path)
	if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte(contents), 0644); err != nil {
		t.Fatal(err)
	}
}

func commitFixture(t *testing.T, root string) {
	t.Helper()
	gitTest(t, root, "add", ".")
	gitTest(t, root, "commit", "-m", "fixture")
}
