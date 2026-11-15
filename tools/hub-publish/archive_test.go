package main

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestOutputArchiveIsDeterministicAndExcludesSymlinks(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "examples", "category", "case")
	outputs := filepath.Join(dir, "outputs")
	if err := os.MkdirAll(outputs, 0755); err != nil {
		t.Fatal(err)
	}
	data := filepath.Join(outputs, "result.json")
	if err := os.WriteFile(data, []byte(`{"value":42}`), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(outputs, "old-validation.json"), []byte("unverified previous run"), 0644); err != nil {
		t.Fatal(err)
	}
	private := filepath.Join(root, "private.txt")
	if err := os.WriteFile(private, []byte("never export"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(private, filepath.Join(outputs, "private-link")); err != nil {
		t.Fatal(err)
	}
	if err := archiveResults(dir, []string{"result.json", "private-link"}); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "artifacts", "category-case-results.tar.gz")
	first, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.Chtimes(data, time.Unix(1000, 0), time.Unix(1000, 0)); err != nil {
		t.Fatal(err)
	}
	if err = archiveResults(dir, []string{"result.json", "private-link"}); err != nil {
		t.Fatal(err)
	}
	second, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(first, second) {
		t.Fatal("file modification time changed the archive identity")
	}
	zipped, err := gzip.NewReader(bytes.NewReader(first))
	if err != nil {
		t.Fatal(err)
	}
	defer zipped.Close()
	reader := tar.NewReader(zipped)
	header, err := reader.Next()
	if err != nil || header.Name != "result.json" {
		t.Fatalf("unexpected archive member: %v %v", header, err)
	}
	if _, err = reader.Next(); err != io.EOF {
		t.Fatal("symlink or unrelated file was exported")
	}
}
