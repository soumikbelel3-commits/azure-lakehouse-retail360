output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "storage_account_name" {
  description = "ADLS Gen2 account holding landing, bronze, silver, gold and supporting containers."
  value       = module.storage.name
}

output "landing_root" {
  description = "Value for the bundle variable landing_root."
  value       = "abfss://landing@${module.storage.name}.dfs.core.windows.net"
}

output "checkpoint_root" {
  description = "Value for the bundle variable checkpoint_root."
  value       = "abfss://checkpoints@${module.storage.name}.dfs.core.windows.net"
}

output "databricks_workspace_url" {
  value = module.databricks.workspace_url
}

output "databricks_access_connector_id" {
  description = "Use as the managed identity when creating the Unity Catalog storage credential."
  value       = module.databricks.access_connector_id
}

output "data_factory_name" {
  value = module.data_factory.name
}

output "event_hubs_namespace" {
  value = module.event_hubs.name
}

output "key_vault_name" {
  value = module.key_vault.name
}

output "log_analytics_workspace_id" {
  value = module.monitoring.workspace_id
}
