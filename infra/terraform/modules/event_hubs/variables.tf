variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "capture_storage_account_id" {
  type = string
}

variable "capture_container_name" {
  type = string
}

variable "private_endpoint_subnet_id" {
  type = string
}

variable "private_dns_zone_id" {
  type = string
}

variable "partition_count" {
  type    = number
  default = 4
}

variable "tags" {
  type    = map(string)
  default = {}
}
