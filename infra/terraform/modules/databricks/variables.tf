variable "prefix" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "virtual_network_id" {
  type = string
}

variable "public_subnet_name" {
  type = string
}

variable "private_subnet_name" {
  type = string
}

variable "public_subnet_nsg_assoc" {
  type = string
}

variable "private_subnet_nsg_assoc" {
  type = string
}

variable "public_network_access" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
