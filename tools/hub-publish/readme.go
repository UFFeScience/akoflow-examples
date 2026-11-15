package main

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var markdownLink = regexp.MustCompile(`(!?\[[^\]]*\])\(([^)\s]+)\)`)

func bundleLinks(text, root, dir, ref string) string {
	text = strings.ReplaceAll(text, "https://github.com/UFFeScience/akoflow-examples/blob/AKO-238/", "https://github.com/UFFeScience/akoflow-examples/blob/"+ref+"/")
	text = strings.ReplaceAll(text, "https://raw.githubusercontent.com/UFFeScience/akoflow-examples/AKO-238/", "https://raw.githubusercontent.com/UFFeScience/akoflow-examples/"+ref+"/")
	return markdownLink.ReplaceAllStringFunc(text, func(match string) string {
		parts := markdownLink.FindStringSubmatch(match)
		target := parts[2]
		if strings.Contains(target, ":") || strings.HasPrefix(target, "#") || strings.HasPrefix(target, "/") {
			return match
		}
		path := filepath.Join(dir, filepath.FromSlash(target))
		relative, err := filepath.Rel(root, path)
		if err != nil || strings.HasPrefix(relative, "..") || filepath.IsAbs(relative) {
			return strings.TrimPrefix(parts[1], "!")
		}
		if _, err = os.Stat(path); err != nil {
			return strings.TrimPrefix(parts[1], "!") + " (not included in this bundle)"
		}
		origin := "https://github.com/UFFeScience/akoflow-examples/blob/" + ref + "/"
		if strings.HasPrefix(parts[1], "!") {
			origin = "https://raw.githubusercontent.com/UFFeScience/akoflow-examples/" + ref + "/"
		}
		return fmt.Sprintf("%s(%s%s)", parts[1], origin, filepath.ToSlash(relative))
	})
}
