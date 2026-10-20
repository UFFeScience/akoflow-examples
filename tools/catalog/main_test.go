package main

import "testing"

func TestCatalogIncludesEveryDomainPipeline(t *testing.T) {
	entries, err := discover("../..")
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 28 {
		t.Fatalf("expected all 28 catalog showcases, got %d", len(entries))
	}
	images := map[string]string{}
	for _, e := range entries {
		images[e.Showcase] = e.Image
	}
	for _, name := range []string{"document-intelligence", "video-intelligence", "blender-render-farm"} {
		if images[name] == "" {
			t.Fatalf("missing domain pipeline: %s", name)
		}
	}
	if images["video-studio"] != "ghcr.io/uffescience/akoflow-examples/ai-video-studio:v1" {
		t.Fatal("CI image must match the workflow's authoritative image, not its directory name")
	}
}
