variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "storage_account_id" {
  type        = string
  description = "ADLS account that the managed private endpoint targets."
}

variable "github" {
  type = object({
    account_name    = string
    repository_name = string
    branch_name     = string
    root_folder     = string
  })
  default = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
