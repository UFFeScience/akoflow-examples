resource "google_compute_network" "matrix" {
  name                    = "akoflow-montage-interference"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "matrix" {
  name          = "akoflow-montage-interference"
  ip_cidr_range = "10.91.0.0/24"
  region        = join("-", slice(split("-", var.zone), 0, 2))
  network       = google_compute_network.matrix.id
}

resource "google_compute_firewall" "ssh" {
  name    = "akoflow-montage-interference-ssh"
  network = google_compute_network.matrix.name

  source_ranges = [var.ssh_source_cidr]
  target_tags   = ["akoflow-montage-interference"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_instance" "matrix" {
  name         = "akoflow-montage-interference"
  machine_type = var.machine_type
  tags         = ["akoflow-montage-interference"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 30
      type  = "pd-balanced"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.matrix.id
    access_config {}
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${trimspace(file(var.ssh_public_key_path))}"
  }

  metadata_startup_script = <<-SCRIPT
    #!/usr/bin/env bash
    set -euo pipefail
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io
    systemctl enable --now docker
    usermod -aG docker ${var.ssh_user}
    touch /var/lib/akoflow-docker-ready
  SCRIPT

  labels = {
    managed_by = "terraform"
    experiment = "montage-58-interference"
  }

  lifecycle {
    prevent_destroy = false
  }
}
