#!/bin/sh
set -eu
go -C "$(dirname "$0")/../.." mod download
