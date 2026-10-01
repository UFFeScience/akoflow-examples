variable "project_id" {
  description = "GCP project used only for the approved calibration VM."
  type        = string
}

variable "zone" {
  description = "GCP zone for the calibration VM."
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Machine type held fixed for the cloud matrix."
  type        = string
  default     = "e2-medium"
}

variable "ssh_user" {
  description = "Linux user written to instance SSH metadata."
  type        = string
}

variable "ssh_public_key_path" {
  description = "Absolute path to an existing public SSH key."
  type        = string
}

variable "ssh_source_cidr" {
  description = "Approved operator source range, normally a single /32."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.ssh_source_cidr))
    error_message = "ssh_source_cidr must be valid CIDR notation."
  }
}
