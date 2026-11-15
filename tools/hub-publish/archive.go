package main

import (
	"archive/tar"
	"compress/gzip"
	"io"
	"os"
	"path/filepath"
	"time"
)

func archiveResults(dir string) error {
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
	root := filepath.Join(dir, "outputs")
	walkErr := filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if !info.Mode().IsRegular() {
			return nil
		}
		relative, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		header, err := tar.FileInfoHeader(info, "")
		if err != nil {
			return err
		}
		header.Name = filepath.ToSlash(relative)
		header.ModTime = time.Unix(0, 0)
		header.Mode = 0644
		header.Uid = 0
		header.Gid = 0
		header.Uname = ""
		header.Gname = ""
		if err = archive.WriteHeader(header); err != nil {
			return err
		}
		source, err := os.Open(path)
		if err != nil {
			return err
		}
		_, err = io.Copy(archive, source)
		closeErr := source.Close()
		if err != nil {
			return err
		}
		return closeErr
	})
	tarErr := archive.Close()
	gzipErr := zipped.Close()
	fileErr := file.Close()
	for _, e := range []error{walkErr, tarErr, gzipErr, fileErr} {
		if e != nil {
			return e
		}
	}
	return nil
}
