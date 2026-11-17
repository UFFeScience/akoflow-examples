package main

import (
	"fmt"
	"os/exec"
	"strings"
)

func changedEntries(root string, entries []entry, base string, mergeBase bool) ([]entry, error) {
	var revision string
	var err error
	if strings.Trim(base, "0") == "" {
		revision, err = gitOutput(root, "hash-object", "-w", "-t", "tree", "--stdin")
	} else {
		revision, err = gitOutput(root, "rev-parse", "--verify", "--end-of-options", base+"^{commit}")
		if err == nil && mergeBase {
			revision, err = gitOutput(root, "merge-base", revision, "HEAD")
		}
	}
	if err != nil {
		return nil, err
	}
	output, err := gitOutput(root, "diff", "--name-only", "--no-renames", "-z", revision, "HEAD", "--")
	if err != nil {
		return nil, err
	}
	return entriesForPaths(entries, strings.Split(output, "\x00")), nil
}

func entriesForPaths(entries []entry, paths []string) []entry {
	selected := []entry{}
	for _, candidate := range entries {
		prefix := candidate.Category + "/" + candidate.Showcase + "/"
		for _, path := range paths {
			if strings.HasPrefix(path, prefix) {
				selected = append(selected, candidate)
				break
			}
		}
	}
	return selected
}

func gitOutput(root string, args ...string) (string, error) {
	command := exec.Command("git", append([]string{"-C", root}, args...)...)
	output, err := command.Output()
	if err != nil {
		return "", fmt.Errorf("git %s: %w", strings.Join(args, " "), err)
	}
	return strings.TrimSuffix(string(output), "\n"), nil
}
