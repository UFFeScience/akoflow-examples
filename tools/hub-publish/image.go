package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
)

func publicImage(dir, captured string) (string, error) {
	if strings.Contains(captured, "@sha256:") {
		return captured, nil
	}
	raw, err := os.ReadFile(filepath.Join(dir, "evidence/public-image-alias.json"))
	if err != nil {
		return "", fmt.Errorf("execution must use a digest-pinned public registry image")
	}
	var proof struct {
		Original string `json:"originalImage"`
		Public   string `json:"publicImage"`
	}
	if json.Unmarshal(raw, &proof) != nil || proof.Original != captured || !strings.Contains(proof.Public, "@sha256:") {
		return "", fmt.Errorf("invalid public image alias")
	}
	images, err := exec.Command("docker", "image", "inspect", captured, proof.Public).Output()
	if err != nil {
		return "", err
	}
	var data []struct {
		Config       any    `json:"Config"`
		RootFS       any    `json:"RootFS"`
		Architecture string `json:"Architecture"`
		OS           string `json:"Os"`
	}
	if json.Unmarshal(images, &data) != nil || len(data) != 2 || !reflect.DeepEqual(data[0], data[1]) {
		return "", fmt.Errorf("public image is not runtime-equivalent to the captured image")
	}
	return proof.Public, nil
}
