variable "prefix" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "retention_days" {
  type    = number
  default = 30
}

variable "alert_email" {
  type        = string
  description = "Mailbox that receives alert notifications."
}

variable "tags" {
  type    = map(string)
  default = {}
}
