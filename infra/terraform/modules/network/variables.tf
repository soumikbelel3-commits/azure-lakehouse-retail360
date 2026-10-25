variable "prefix" {
  type        = string
  description = "Naming prefix, e.g. retail360-dev-weu."
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "address_space" {
  type        = string
  description = "CIDR of the data platform VNet (a /16 is expected; /24 subnets are carved from it)."
}

variable "tags" {
  type    = map(string)
  default = {}
}
