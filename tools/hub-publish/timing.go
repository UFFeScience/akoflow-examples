package main

import (
	"fmt"
	"html"
	"os"
	"path/filepath"
	"strings"
)

type timingActivity struct {
	ID       string  `json:"activityId"`
	Finished float64 `json:"finishedAt"`
	Runtime  float64 `json:"runtimeSeconds"`
}

func timingFigure(dir, run string, stages []string, activities []timingActivity) error {
	if len(stages) != 2 {
		return nil
	}
	durations := map[string]float64{}
	maximum := 0.0
	for _, a := range activities {
		for _, name := range stages {
			if strings.HasSuffix(a.ID, "-"+name) {
				durations[name] = a.Runtime
				if a.Runtime > maximum {
					maximum = a.Runtime
				}
			}
		}
	}
	scale := maximum
	if scale == 0 {
		scale = 1
	}
	var svg strings.Builder
	fmt.Fprintf(&svg, `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="230" viewBox="0 0 1080 230" role="img" aria-label="Measured activity runtime"><rect width="1080" height="230" fill="#ffffff"/><g fill="#151515" font-family="system-ui,sans-serif"><text x="28" y="35" font-size="22" font-weight="600">Measured activity runtime</text><text x="28" y="59" font-size="10">%s</text>`, html.EscapeString(run))
	for index, name := range stages {
		y := 95 + index*54
		width := durations[name] / scale * 720
		fmt.Fprintf(&svg, `<text x="28" y="%d" font-size="14">%s</text><rect x="150" y="%d" width="%.3f" height="24" fill="#151515"/><text x="900" y="%d" font-size="14">%.4f s</text>`, y+17, html.EscapeString(name), y, width, y+17, durations[name])
	}
	svg.WriteString(`<text x="28" y="214" font-size="12">Observed Docker activity runtime; excludes queue and setup time. No cloud execution is claimed.</text></g></svg>`)
	return os.WriteFile(filepath.Join(dir, "evidence/timing.svg"), []byte(svg.String()), 0644)
}
