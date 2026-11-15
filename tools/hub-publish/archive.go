package main

import (
	"archive/tar"
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

func archiveResults(dir string, names []string) error {
	folder := filepath.Clean(filepath.Join(dir, "../../..", "artifacts"))
	if err := os.MkdirAll(folder, 0755); err != nil {
		return err
	}
	name := filepath.Base(filepath.Dir(dir)) + "-" + filepath.Base(dir) + "-results.tar.gz"
	file, err := os.Create(filepath.Join(folder, name))
	if err != nil {
		return err
	}
	zipped := gzip.NewWriter(file)
	archive := tar.NewWriter(zipped)
	seen := map[string]bool{}
	allowed := append([]string{}, names...)
	sort.Strings(allowed)
	exportErr := func() error {
		for _, name := range allowed {
			if filepath.IsAbs(name) || strings.Contains(name, "..") {
				return fmt.Errorf("unsafe output archive path")
			}
			if seen[name] {
				continue
			}
			seen[name] = true
			path := filepath.Join(dir, "outputs", name)
			info, e := os.Lstat(path)
			if e != nil {
				return e
			}
			if !info.Mode().IsRegular() {
				continue
			}
			header, e := tar.FileInfoHeader(info, "")
			if e != nil {
				return e
			}
			header.Name = filepath.ToSlash(name)
			header.ModTime = time.Unix(0, 0)
			header.Mode = 0644
			header.Uid = 0
			header.Gid = 0
			header.Uname = ""
			header.Gname = ""
			if e = archive.WriteHeader(header); e != nil {
				return e
			}
			source, e := os.Open(path)
			if e != nil {
				return e
			}
			_, e = io.Copy(archive, source)
			closeErr := source.Close()
			if e != nil {
				return e
			}
			if closeErr != nil {
				return closeErr
			}
		}
		return nil
	}()
	tarErr := archive.Close()
	gzipErr := zipped.Close()
	fileErr := file.Close()
	for _, e := range []error{exportErr, tarErr, gzipErr, fileErr} {
		if e != nil {
			return e
		}
	}
	return nil
}
