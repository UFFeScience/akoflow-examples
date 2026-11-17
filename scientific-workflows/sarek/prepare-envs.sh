#!/bin/bash
set -euo pipefail
micromamba create -y -p /opt/nf-envs/sarek-7a76a1a96509 -f /app/upstream/sarek/modules/nf-core/gatk4/createsequencedictionary/environment.yml
micromamba env export -p /opt/nf-envs/sarek-7a76a1a96509 --explicit > /opt/nf-env-locks/sarek-7a76a1a96509.txt
micromamba create -y -p /opt/nf-envs/sarek-79834e3e6d8c -f /app/upstream/sarek/modules/nf-core/bedtools/sort/environment.yml
micromamba env export -p /opt/nf-envs/sarek-79834e3e6d8c --explicit > /opt/nf-env-locks/sarek-79834e3e6d8c.txt
micromamba create -y -p /opt/nf-envs/sarek-b7682ac7c9ee -f /app/upstream/sarek/modules/nf-core/gawk/environment.yml
micromamba env export -p /opt/nf-envs/sarek-b7682ac7c9ee --explicit > /opt/nf-env-locks/sarek-b7682ac7c9ee.txt
micromamba create -y -p /opt/nf-envs/sarek-0e04ebbbf085 -f /app/upstream/sarek/modules/nf-core/htslib/bgziptabix/environment.yml
micromamba env export -p /opt/nf-envs/sarek-0e04ebbbf085 --explicit > /opt/nf-env-locks/sarek-0e04ebbbf085.txt
micromamba create -y -p /opt/nf-envs/sarek-8087b7c1a8b5 -f /app/upstream/sarek/modules/nf-core/bcftools/concat/environment.yml
micromamba env export -p /opt/nf-envs/sarek-8087b7c1a8b5 --explicit > /opt/nf-env-locks/sarek-8087b7c1a8b5.txt
micromamba create -y -p /opt/nf-envs/sarek-63248d3d790d -f /app/upstream/sarek/modules/nf-core/vcftools/environment.yml
micromamba env export -p /opt/nf-envs/sarek-63248d3d790d --explicit > /opt/nf-env-locks/sarek-63248d3d790d.txt
micromamba create -y -p /opt/nf-envs/sarek-fb630f3315e9 -f /app/upstream/sarek/modules/nf-core/mosdepth/environment.yml
micromamba env export -p /opt/nf-envs/sarek-fb630f3315e9 --explicit > /opt/nf-env-locks/sarek-fb630f3315e9.txt
micromamba clean --all --yes
