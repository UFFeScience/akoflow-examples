package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

type contract struct {
	ReleaseTag   string            `json:"releaseTag"`
	Tags         []string          `json:"tags"`
	ResultImages map[string]string `json:"resultImages"`
	OriginalYAML string            `json:"originalYAML"`
	Title        string            `json:"title"`
	ExamplePath  string            `json:"examplePath"`
	LocalProfile string            `json:"localProfile"`
	Artifacts    []string          `json:"artifacts"`
	Screenshots  map[string]string `json:"screenshots"`
}
type evidence struct {
	RunID         string `json:"runId"`
	PlanID        string `json:"planId"`
	Status        string `json:"status"`
	Image         string `json:"image"`
	ActivityCount int    `json:"activityCount"`
	Completed     int    `json:"completedActivityCount"`
}
type client struct {
	Base, Cookie, Token, NamespaceID, Workspace string
	HTTP                                        *http.Client
}

func (c client) call(method, path string, in, out any) error {
	var body io.Reader
	if in != nil {
		data, err := json.Marshal(in)
		if err != nil {
			return err
		}
		body = bytes.NewReader(data)
	}
	r, err := http.NewRequest(method, c.Base+path, body)
	if err != nil {
		return err
	}
	r.Header.Set("Content-Type", "application/json")
	if c.Cookie != "" {
		r.Header.Set("Cookie", "hub_session="+c.Cookie)
	}
	if c.Token != "" {
		r.Header.Set("Authorization", "Bearer "+c.Token)
	}
	x, err := c.HTTP.Do(r)
	if err != nil {
		return err
	}
	defer x.Body.Close()
	data, err := io.ReadAll(io.LimitReader(x.Body, 24<<20))
	if err != nil {
		return err
	}
	if x.StatusCode < 200 || x.StatusCode >= 300 {
		return fmt.Errorf("%s %s HTTP %d: %.500s", method, path, x.StatusCode, data)
	}
	if out != nil {
		return json.Unmarshal(data, out)
	}
	return nil
}
func write(path string, v any) error {
	b, e := json.MarshalIndent(v, "", "  ")
	if e != nil {
		return e
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
func hash(s string) string { v := sha256.Sum256([]byte(s)); return hex.EncodeToString(v[:]) }

var sensitive = regexp.MustCompile(`(?i)(password|secret|token|private.?key|access.?key|authorization|credential)`)

func redact(v any, path string, paths *[]string) any {
	switch a := v.(type) {
	case map[string]any:
		for k, x := range a {
			p := path + "/" + k
			if sensitive.MatchString(k) && x != nil && x != "" {
				a[k] = "[redacted]"
				*paths = append(*paths, p)
			} else {
				a[k] = redact(x, p, paths)
			}
		}
	case []any:
		for i, x := range a {
			a[i] = redact(x, fmt.Sprintf("%s/%d", path, i), paths)
		}
	}
	return v
}
func packageRun(api client, e evidence, y string) (map[string]any, map[string]any, error) {
	var ctx, execution map[string]any
	if err := api.call("GET", "/schedule-plans/"+url.PathEscape(e.PlanID)+"/context/", nil, &ctx); err != nil {
		return nil, nil, err
	}
	if err := api.call("GET", "/execution-runs/"+url.PathEscape(e.RunID)+"/", nil, &execution); err != nil {
		return nil, nil, err
	}
	run, _ := execution["run"].(map[string]any)
	if run["status"] != "completed" || int(run["completedActivityCount"].(float64)) != e.ActivityCount {
		return nil, nil, fmt.Errorf("run is not fully completed")
	}
	paths := []string{}
	ctx = redact(ctx, "context", &paths).(map[string]any)
	execution = redact(execution, "execution", &paths).(map[string]any)
	workflow := ctx["workflow"].(map[string]any)
	version := workflow["version"].(map[string]any)
	exported := map[string]any{}
	for _, k := range []string{"run", "activities", "activityAttempts", "dataTransfers", "timeline", "cloudBilling", "artifactTransferRuns", "dataObjects", "dataLocations", "workspaces", "workspaceLeases", "artifactMaterializations", "infrastructureRuns", "events", "operationEvents"} {
		if v, ok := execution[k]; ok {
			exported[k] = v
		}
	}
	logs := []any{}
	if handles, ok := execution["handles"].([]any); ok {
		for _, h := range handles {
			record := map[string]any{}
			for _, k := range []string{"activityId", "attempt", "runtime", "status", "startedAt", "finishedAt", "exitCode", "log"} {
				if v, ok := h.(map[string]any)[k]; ok {
					record[k] = v
				}
			}
			logs = append(logs, record)
		}
	}
	exported["processLogs"] = logs
	exported["files"] = execution["dataObjects"]
	var metrics struct {
		Items []any `json:"items"`
	}
	if err := api.call("GET", "/execution-runs/"+url.PathEscape(e.RunID)+"/activity-metrics/", nil, &metrics); err != nil {
		return nil, nil, err
	}
	if metrics.Items == nil {
		metrics.Items = []any{}
	}
	exported["metricSummaries"] = metrics.Items
	files := []any{}
	for _, item := range []struct {
		path string
		data any
	}{{"workflow.yaml", y}, {"workflow.json", workflow}, {"plans.json", []any{map[string]any{"plan": ctx["plan"], "context": ctx}}}, {"executions.json", []any{exported}}} {
		content := y
		media := "application/yaml"
		if item.path != "workflow.yaml" {
			raw, err := json.Marshal(item.data)
			if err != nil {
				return nil, nil, err
			}
			content = string(raw)
			media = "application/json"
		}
		files = append(files, map[string]any{"path": item.path, "mediaType": media, "sha256": hash(content), "content": content})
	}
	return map[string]any{"format": "akoflow.experiment", "schemaVersion": "1.0", "exportedAt": time.Now().UTC().Format(time.RFC3339), "producer": map[string]string{"name": "Akoflow showcase publisher", "version": "1.0"}, "source": map[string]any{"workflowId": workflow["id"], "workflowVersionId": version["id"]}, "redactions": paths, "files": files}, run, nil
}
func main() {
	root := flag.String("root", ".", "examples checkout")
	docs := flag.String("docs", "", "documentation directory")
	hubURL := flag.String("hub", "https://hub.akoflow.com", "Hub origin")
	apiURL := flag.String("api", "http://192.168.1.13:8080/akoflow-api", "daemon origin")
	cookieFile := flag.String("session-file", "", "protected Hub session file")
	envFile := flag.String("env-file", "", "daemon env file")
	workspace := flag.String("workspace", "akoflow", "destination workspace slug")
	only := flag.String("only", "", "one example path")
	flag.Parse()
	token := ""
	env, err := os.ReadFile(*envFile)
	if err != nil {
		panic(err)
	}
	for _, line := range strings.Split(string(env), "\n") {
		if strings.HasPrefix(line, "AKOFLOW_API_TOKEN=") {
			token = strings.Trim(strings.TrimPrefix(line, "AKOFLOW_API_TOKEN="), "\"'")
		}
	}
	cookie, err := os.ReadFile(*cookieFile)
	if err != nil {
		panic(err)
	}
	httpClient := &http.Client{Timeout: 45 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	hub := client{Base: *hubURL + "/api/v1", Cookie: strings.TrimSpace(string(cookie)), HTTP: httpClient}
	api := client{Base: *apiURL, Token: token, HTTP: httpClient}
	var namespaces []struct {
		ID   string `json:"id"`
		Slug string `json:"slug"`
	}
	if err = hub.call("GET", "/namespaces", nil, &namespaces); err != nil {
		panic(err)
	}
	for _, ns := range namespaces {
		if ns.Slug == *workspace {
			hub.NamespaceID = ns.ID
			hub.Workspace = ns.Slug
		}
	}
	if hub.NamespaceID == "" {
		panic("destination workspace not accessible")
	}
	raw, err := os.ReadFile(filepath.Join(*docs, "src/data/showcase-contracts.json"))
	if err != nil {
		panic(err)
	}
	catalog := map[string]contract{}
	if err = json.Unmarshal(raw, &catalog); err != nil {
		panic(err)
	}
	extraPath := filepath.Join(*docs, "src/data/showcase-extra-contracts.json")
	if extra, e := os.ReadFile(extraPath); e == nil {
		var additions map[string]contract
		if e = json.Unmarshal(extra, &additions); e != nil {
			panic(e)
		}
		for route, item := range additions {
			catalog[route] = item
		}
	}
	routes := []string{}
	for r := range catalog {
		routes = append(routes, r)
	}
	sort.Strings(routes)
	manifest := []any{}
	failed := false
	for _, route := range routes {
		c := catalog[route]
		if *only != "" && c.ExamplePath != *only {
			continue
		}
		receipt, err := publish(hub, api, *root, route, c)
		if err != nil {
			fmt.Fprintf(os.Stderr, "FAILED %s: %v\n", c.ExamplePath, err)
			failed = true
			continue
		}
		manifest = append(manifest, receipt)
		fmt.Printf("PUBLISHED %s %v\n", c.ExamplePath, receipt["uri"])
	}
	manifest = []any{}
	receipts, _ := filepath.Glob(filepath.Join(*root, "*", "*", "evidence", "hub-publication.json"))
	sort.Strings(receipts)
	for _, path := range receipts {
		data, e := os.ReadFile(path)
		if e != nil {
			panic(e)
		}
		var item map[string]any
		if e = json.Unmarshal(data, &item); e != nil {
			panic(e)
		}
		manifest = append(manifest, item)
	}
	if err := write(filepath.Join(*root, "hub-publications.json"), manifest); err != nil {
		panic(err)
	}
	if failed {
		os.Exit(1)
	}
}
func publish(hub, api client, root, route string, c contract) (map[string]any, error) {
	dir, err := filepath.Abs(filepath.Join(root, c.ExamplePath))
	if err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(filepath.Join(dir, "evidence/daemon-run.json"))
	if err != nil {
		return nil, err
	}
	var e evidence
	if err = json.Unmarshal(raw, &e); err != nil {
		return nil, err
	}
	if e.Status != "completed" || e.Completed != e.ActivityCount {
		return nil, fmt.Errorf("fresh execution incomplete: %s", e.Status)
	}
	capturedImage := e.Image
	e.Image, err = publicImage(dir, e.Image)
	if err != nil {
		return nil, err
	}
	y, err := os.ReadFile(filepath.Join(dir, "workflow.yaml"))
	if err != nil {
		return nil, err
	}
	var definition map[string]any
	if err = yaml.Unmarshal(y, &definition); err != nil {
		return nil, err
	}
	definition["spec"].(map[string]any)["image"] = e.Image
	y, err = yaml.Marshal(definition)
	if err != nil {
		return nil, err
	}
	if err = collectResults(dir, raw, c.Artifacts); err != nil {
		return nil, err
	}
	bundle, run, err := packageRun(api, e, string(y))
	if err != nil {
		return nil, err
	}
	if err = write(filepath.Join(dir, "evidence/experiment.json"), bundle); err != nil {
		return nil, err
	}
	slug := strings.ReplaceAll(c.ExamplePath, "/", "-")
	var pub struct {
		ID     string `json:"id"`
		Readme string `json:"readme"`
	}
	err = hub.call("GET", "/publications/resolve?kind=organization&owner="+url.QueryEscape(hub.Workspace)+"&slug="+slug, nil, &pub)
	original, errRead := os.ReadFile(filepath.Join(dir, "README.md"))
	if errRead != nil {
		return nil, errRead
	}
	base := strings.SplitN(string(original), "\n<!-- hub-publication -->", 2)[0]
	if cut := strings.Index(base, "## Current execution evidence"); cut >= 0 {
		base = strings.TrimSpace(base[:cut])
	}
	base = strings.ReplaceAll(base, "New daemon execution and one capture per activity are still required before claiming Desktop verification.", "The measured execution and validated outputs for this publication are recorded below.")
	absoluteRoot, eRoot := filepath.Abs(root)
	if eRoot != nil {
		return nil, eRoot
	}
	ref, eRef := exec.Command("git", "-C", absoluteRoot, "rev-parse", "HEAD").Output()
	if eRef != nil {
		return nil, eRef
	}
	base = bundleLinks(base, absoluteRoot, dir, strings.TrimSpace(string(ref)))
	if err != nil {
		if !strings.Contains(err.Error(), "HTTP 404") {
			return nil, err
		}
		in := map[string]any{"namespaceId": hub.NamespaceID, "slug": slug, "title": c.Title, "description": c.LocalProfile, "readme": base, "visibility": "public", "tags": c.Tags}
		if err = hub.call("POST", "/publications", in, &pub); err != nil {
			return nil, err
		}
	}
	var versions []struct {
		Number int `json:"number"`
	}
	if err = hub.call("GET", "/publications/"+pub.ID+"/versions", nil, &versions); err != nil {
		return nil, err
	}
	baseVersion := 0
	for _, v := range versions {
		if v.Number > baseVersion {
			baseVersion = v.Number
		}
	}
	if baseVersion == 0 && c.OriginalYAML != "" {
		original, e := os.ReadFile(filepath.Join(root, c.OriginalYAML))
		if e != nil {
			return nil, e
		}
		if strings.HasSuffix(c.OriginalYAML, ".json") {
			var value any
			if e = json.Unmarshal(original, &value); e != nil {
				return nil, e
			}
			original, e = yaml.Marshal(value)
			if e != nil {
				return nil, e
			}
		}
		var first struct {
			Number int `json:"number"`
		}
		if e = hub.call("POST", "/publications/"+pub.ID+"/versions", map[string]any{"yaml": string(original), "message": "Original cloud placement reference; cloud infrastructure execution is not claimed by this local profile", "baseVersion": 0}, &first); e != nil {
			return nil, e
		}
		baseVersion = first.Number
	}
	bundleBytes, err := json.Marshal(bundle)
	if err != nil {
		return nil, err
	}
	var receipt struct {
		ExperimentID string `json:"experimentId"`
		ResultCount  int    `json:"resultCount"`
		Version      struct {
			ID     string `json:"id"`
			Number int    `json:"number"`
			Hash   string `json:"hash"`
		} `json:"version"`
	}
	if err = hub.call("POST", "/publications/"+pub.ID+"/import/confirm", map[string]any{"bundleFile": string(bundleBytes), "baseVersion": baseVersion, "message": "Official showcase: measured homeserver execution using a public immutable image"}, &receipt); err != nil {
		return nil, err
	}
	uri := fmt.Sprintf("akoflow://hub/publications/%s/versions/%d", pub.ID, receipt.Version.Number)
	page := strings.TrimSuffix(hub.Base, "/api/v1") + "/o/" + hub.Workspace + "/" + slug
	var extra strings.Builder
	fmt.Fprintf(&extra, "\n<!-- hub-publication -->\n\n## Public Hub version and measured execution\n\n[Open this workflow and its results](%s) · [Documentation](https://akoflow.com%s)\n\n### Import into AkôFlow Desktop\n\nCreate workflow → Import from Hub → paste this immutable URI:\n\n```text\n%s\n```\n\nThe URI imports the workflow definition. Build or pull the public image and register the companion `environment.yaml`, `scope.yaml`, and `topology.yaml` from this source bundle before planning a local execution. No hosted account, GPU or cloud capacity is required for this CPU profile.\n\nImage: `%s`.\n\n### Actual homeserver results\n\nRun `%s` completed **%d/%d** activities in **%v seconds**. These are measured Docker-backed computations, not simulated timing. The captured manual plan uses placeholder predicted timings; those predictions are not benchmark measurements. Use the observed execution metrics for performance analysis. Cost is the configured local compute cost and excludes electricity and hardware.\n\n[Download the native experiment capture](%s/api/v1/publications/%s/experiments/%s). The Hub Results tab includes the same plan, attempts, metrics and logs.\n\n### Inputs and outputs\n\nInput fixtures and scientific source are described in this bundle's README; inspect them together with the workflow definition and bundle configuration for profile assumptions. Fixtures are generated by the included code unless a bundle identifies an upstream dataset. No repository-wide LICENSE file is currently present: inspect the bundle and upstream terms before redistributing source or data; publication here does not grant additional rights. Outputs expected from this workflow:\n\n", page, route, uri, e.Image, e.RunID, e.Completed, e.ActivityCount, run["makespanSeconds"], strings.TrimSuffix(hub.Base, "/api/v1"), pub.ID, receipt.ExperimentID)
	for _, a := range c.Artifacts {
		fmt.Fprintf(&extra, "- `%s`\n", a)
	}
	releaseTag := c.ReleaseTag
	if releaseTag == "" {
		releaseTag = "showcase-hub-v1"
	}
	fmt.Fprintf(&extra, "\n[Download the actual validated output files](https://github.com/UFFeScience/akoflow-examples/releases/download/%s/%s-results.tar.gz).\n\n", releaseTag, slug)
	if len(c.ResultImages) > 0 {
		extra.WriteString("\n### Images from this validated execution\n\n")
		imageNames := []string{}
		for k := range c.ResultImages {
			imageNames = append(imageNames, k)
		}
		sort.Strings(imageNames)
		for _, k := range imageNames {
			fmt.Fprintf(&extra, "![%s](https://akoflow.com%s)\n\n", k, c.ResultImages[k])
		}
	}
	extra.WriteString("\n### Illustrated walkthrough\n\nThe following reference screenshots come from the documentation walkthrough. The current measured run is recorded separately above.\n\n")
	keys := []string{}
	for k := range c.Screenshots {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Fprintf(&extra, "#### %s\n\n![%s](https://akoflow.com%s)\n\n", k, k, c.Screenshots[k])
	}
	if capturedImage != e.Image {
		fmt.Fprintf(&extra, "\nThe captured run used local alias `%s`. Its complete filesystem layers, runtime configuration, OS and architecture were compared with the public digest above and match; the recorded capture preserves the original image reference.\n", capturedImage)
	}
	readme := strings.TrimRight(base+extra.String(), "\n") + "\n"
	if err = os.WriteFile(filepath.Join(dir, "README.md"), []byte(readme), 0644); err != nil {
		return nil, err
	}
	if err = hub.call("PATCH", "/publications/"+pub.ID, map[string]any{"title": c.Title, "description": c.LocalProfile, "readme": strings.ReplaceAll(readme, "<!-- hub-publication -->\n", ""), "visibility": "public", "tags": c.Tags}, nil); err != nil {
		return nil, err
	}
	result := map[string]any{"route": route, "examplePath": c.ExamplePath, "publicationId": pub.ID, "versionId": receipt.Version.ID, "version": receipt.Version.Number, "yamlHash": receipt.Version.Hash, "uri": uri, "url": page, "experimentId": receipt.ExperimentID, "runId": e.RunID, "image": e.Image, "activityCount": e.Completed, "resultCount": receipt.ResultCount}
	return result, write(filepath.Join(dir, "evidence/hub-publication.json"), result)
}
