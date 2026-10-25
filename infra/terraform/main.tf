data "azurerm_client_config" "current" {}

locals {
  prefix = "${var.project}-${var.environment}-${var.location_short}"

  tags = merge(
    {
      project     = var.project
      environment = var.environment
      managed_by  = "terraform"
      repository  = "azure-lakehouse-retail360"
    },
    var.tags,
  )
}

resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.prefix}"
  location = var.location
  tags     = local.tags
}

# ---------------------------------------------------------------------------------------
# Foundation: network, observability, secrets
# ---------------------------------------------------------------------------------------
module "network" {
  source              = "./modules/network"
  prefix              = local.prefix
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  address_space       = var.vnet_address_space
  tags                = local.tags
}

module "monitoring" {
  source              = "./modules/monitoring"
  prefix              = local.prefix
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  retention_days      = var.log_retention_days
  alert_email         = var.alert_email
  tags                = local.tags
}

module "key_vault" {
  source                     = "./modules/key_vault"
  name                       = "kv-${var.project}-${var.environment}-${random_string.suffix.result}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  purge_protection_enabled   = var.key_vault_purge_protection
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  private_dns_zone_id        = module.network.private_dns_zone_ids["vault"]
  tags                       = local.tags
}

# ---------------------------------------------------------------------------------------
# Storage: ADLS Gen2 lakehouse
# ---------------------------------------------------------------------------------------
module "storage" {
  source                     = "./modules/storage"
  name                       = "st${var.project}${var.environment}${random_string.suffix.result}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  replication_type           = var.storage_replication_type
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  private_dns_zone_ids       = module.network.private_dns_zone_ids
  tags                       = local.tags
}

# ---------------------------------------------------------------------------------------
# Compute and orchestration
# ---------------------------------------------------------------------------------------
module "databricks" {
  source                   = "./modules/databricks"
  prefix                   = local.prefix
  location                 = var.location
  resource_group_name      = azurerm_resource_group.this.name
  virtual_network_id       = module.network.vnet_id
  public_subnet_name       = module.network.databricks_public_subnet_name
  private_subnet_name      = module.network.databricks_private_subnet_name
  public_subnet_nsg_assoc  = module.network.databricks_public_nsg_association_id
  private_subnet_nsg_assoc = module.network.databricks_private_nsg_association_id
  public_network_access    = var.databricks_public_network_access
  tags                     = local.tags
}

module "data_factory" {
  source              = "./modules/data_factory"
  name                = "adf-${local.prefix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  storage_account_id  = module.storage.id
  github              = var.adf_github
  tags                = local.tags
}

module "event_hubs" {
  source                     = "./modules/event_hubs"
  name                       = "evhns-${local.prefix}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  capture_storage_account_id = module.storage.id
  capture_container_name     = module.storage.container_names["archive"]
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  private_dns_zone_id        = module.network.private_dns_zone_ids["servicebus"]
  tags                       = local.tags
}

# ---------------------------------------------------------------------------------------
# Least-privilege access (managed identities only, no keys or passwords)
# ---------------------------------------------------------------------------------------
resource "azurerm_role_assignment" "adf_storage" {
  scope                = module.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.data_factory.principal_id
}

resource "azurerm_role_assignment" "databricks_connector_storage" {
  scope                = module.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.databricks.access_connector_principal_id
}

resource "azurerm_role_assignment" "eventhubs_capture_storage" {
  scope                = module.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.event_hubs.principal_id
}

resource "azurerm_role_assignment" "adf_key_vault" {
  scope                = module.key_vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.data_factory.principal_id
}

# ---------------------------------------------------------------------------------------
# Diagnostics to Log Analytics and pipeline failure alerting
# ---------------------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "adf" {
  name                       = "diag-adf"
  target_resource_id         = module.data_factory.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  name                       = "diag-kv"
  target_resource_id         = module.key_vault.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "audit"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage_blob" {
  name                       = "diag-st-blob"
  target_resource_id         = "${module.storage.id}/blobServices/default"
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "Transaction"
  }
}

resource "azurerm_monitor_diagnostic_setting" "event_hubs" {
  name                       = "diag-evhns"
  target_resource_id         = module.event_hubs.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_metric_alert" "adf_pipeline_failures" {
  name                = "alert-${local.prefix}-adf-pipeline-failed"
  resource_group_name = azurerm_resource_group.this.name
  scopes              = [module.data_factory.id]
  description         = "At least one Data Factory pipeline run failed in the last 15 minutes."
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.DataFactory/factories"
    metric_name      = "PipelineFailedRuns"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = module.monitoring.action_group_id
  }
}
