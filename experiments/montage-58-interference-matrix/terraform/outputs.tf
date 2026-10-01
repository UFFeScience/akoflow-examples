output "instance_name" {
  value = google_compute_instance.matrix.name
}

output "zone" {
  value = var.zone
}

output "external_ip" {
  value = google_compute_instance.matrix.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  value = "ssh ${var.ssh_user}@${google_compute_instance.matrix.network_interface[0].access_config[0].nat_ip}"
}
