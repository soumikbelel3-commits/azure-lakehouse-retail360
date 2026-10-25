variable "subscription_id" {
  description = "Azure subscription that hosts this environment."
  type        = string
}

variable "project" {
  description = "Short project name used in resource names."
  type        = string
  default     = "retail360"
}

variable "environment" {
  description = "Deployment environment."
  type        = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be one of: dev, test, prod."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "westeurope"
}

variable "location_short" {
  description = "Short region code used in resource names."
  type        = string
  default     = "weu"
}

variable "vnet_address_space" {
  description = "Address space of the data platform virtual network."
  type        = string
  default     = "10.10.0.0/16"
}

variable "storage_replication_type" {
  description = "ADLS Gen2 replication: ZRS for dev, GZRS or RAGZRS for production."
  type        = string
  default     = "ZRS"
}

variable "log_retention_days" {
  description = "Log Analytics retention."
  type        = number
  default     = 30
}

variable "alert_email" {
  description = "Mailbox that receives pipeline failure alerts."
  type        = string
}

variable "databricks_public_network_access" {
  description = "Allow browser access to the workspace over the internet (disable once Front-end Private Link is in place)."
  type        = bool
  default     = true
}

variable "key_vault_purge_protection" {
  description = "Enable purge protection on Key Vault (always true for production)."
  type        = bool
  default     = false
}

variable "adf_github" {
  description = "Optional GitHub integration for Data Factory. Set to null to disable."
  type = object({
    account_name    = string
    repository_name = string
    branch_name     = string
    root_folder     = string
  })
  default = null
}

variable "tags" {
  description = "Extra tags merged into the standard tag set."
  type        = map(string)
  default     = {}
}
