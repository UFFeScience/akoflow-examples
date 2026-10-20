package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func copyWorkload(t *testing.T, relative string) string {
	t.Helper()
	root := t.TempDir()
	source := filepath.Join("../..", relative)
	for _, name := range []string{"workflow.yaml", "data/input.json", "data/workload.json", "scripts/run_showcase.py"} {
		data, err := os.ReadFile(filepath.Join(source, name))
		if err != nil {
			t.Fatal(err)
		}
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, data, 0644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}
func objectFile(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var value map[string]any
	if err := json.Unmarshal(raw, &value); err != nil {
		t.Fatal(err)
	}
	return value
}
func TestScientificInferenceRespondsToChangedInputs(t *testing.T) {
	root := copyWorkload(t, "scientific-ai/ai-assisted-analysis")
	if err := run(root); err != nil {
		t.Fatal(err)
	}
	first := objectFile(t, filepath.Join(root, "outputs/analysis.json"))["inference"].(map[string]any)["fittedDecayRate"].(float64)
	inputPath := filepath.Join(root, "data/workload.json")
	input := objectFile(t, inputPath)
	input["decay"] = 0.45
	input["maxError"] = 0.1
	if err := writeJSON(inputPath, input); err != nil {
		t.Fatal(err)
	}
	if err := run(root); err != nil {
		t.Fatal(err)
	}
	second := objectFile(t, filepath.Join(root, "outputs/analysis.json"))["inference"].(map[string]any)["fittedDecayRate"].(float64)
	if second-first < 0.1 {
		t.Fatalf("inference did not respond to changed experiment inputs: %v vs %v", first, second)
	}
}
func TestUnsafeExperimentBatchCannotPublishSuccess(t *testing.T) {
	root := copyWorkload(t, "scientific-ai/experiment-feedback-loop")
	inputPath := filepath.Join(root, "data/workload.json")
	input := objectFile(t, inputPath)
	input["maximum"] = 1.0
	if err := writeJSON(inputPath, input); err != nil {
		t.Fatal(err)
	}
	err := run(root)
	if err == nil || !strings.Contains(err.Error(), "safety envelope") {
		t.Fatalf("expected safety rejection, got %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "outputs/manifest.json")); !os.IsNotExist(err) {
		t.Fatal("a rejected experiment published a manifest")
	}
}
func TestOCRReadsChangedRasterizedDigits(t *testing.T) {
	root := copyWorkload(t, "generative-ai/document-extraction")
	path := filepath.Join(root, "data/workload.json")
	input := objectFile(t, path)
	input["invoiceId"] = "987"
	input["amountDigits"] = "065"
	if err := writeJSON(path, input); err != nil {
		t.Fatal(err)
	}
	if err := run(root); err != nil {
		t.Fatal(err)
	}
	result := objectFile(t, filepath.Join(root, "outputs/extraction.json"))
	if result["invoiceId"] != "987" || result["amount"].(float64) != 65 {
		t.Fatalf("OCR did not process the changed input pixels: %+v", result)
	}
}
