variable "name" {
  type        = string
  description = "Storage account name (3-24 chars, lowercase letters and digits)."
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "replication_type" {
  type    = string
  default = "ZRS"
}

variable "containers" {
  type        = list(string)
  description = "Lakehouse zones and supporting containers."
  default     = ["landing", "bronze", "silver", "gold", "checkpoints", "config", "archive"]
}

variable "private_endpoint_subnet_id" {
  type = string
}

variable "private_dns_zone_ids" {
  type        = map(string)
  description = "Private DNS zone ids keyed by sub-resource (needs dfs and blob)."
}

variable "tags" {
  type    = map(string)
  default = {}
}
