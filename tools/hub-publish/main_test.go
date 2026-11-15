package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestRedactionRemovesNestedSecrets(t *testing.T) {
	input := map[string]any{"id": "run-123", "environment": map[string]any{"credentials": map[string]any{"password": "never-export"}, "name": "Local Docker"}, "attempts": []any{map[string]any{"accessToken": "private"}}}
	paths := []string{}
	output := redact(input, "snapshot", &paths).(map[string]any)
	if output["id"] != "run-123" || len(paths) != 2 {
		t.Fatalf("redaction changed identity or missed credentials: %v", paths)
	}
	if output["environment"].(map[string]any)["credentials"] != "[redacted]" {
		t.Fatal("nested credential object leaked")
	}
}
func TestHubCredentialsAreNotSentAsBearer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "" || r.Header.Get("Cookie") != "hub_session=private-session" {
			t.Error("incorrect credential transport")
		}
		w.Write([]byte(`{"id":"publication"}`))
	}))
	defer server.Close()
	c := client{Base: server.URL, Cookie: "private-session", HTTP: server.Client()}
	var result map[string]any
	if err := c.call("GET", "/publication", nil, &result); err != nil || result["id"] != "publication" {
		t.Fatal(err)
	}
}
func TestClientRejectsFailedPublication(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "conflicting version", http.StatusConflict)
	}))
	defer server.Close()
	c := client{Base: server.URL, HTTP: server.Client()}
	if err := c.call("POST", "/versions", map[string]any{}, nil); err == nil || !strings.Contains(err.Error(), "HTTP 409") {
		t.Fatal("failed publication was accepted")
	}
}
