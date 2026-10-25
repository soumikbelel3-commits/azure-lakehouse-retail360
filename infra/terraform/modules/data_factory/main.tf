resource "azurerm_data_factory" "this" {
  name                            = var.name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  managed_virtual_network_enabled = true
  public_network_enabled          = true # authoring from the portal; data movement stays on the managed VNet
  tags                            = var.tags

  identity {
    type = "SystemAssigned"
  }

  dynamic "github_configuration" {
    for_each = var.github == null ? [] : [var.github]
    content {
      account_name    = github_configuration.value.account_name
      repository_name = github_configuration.value.repository_name
      branch_name     = github_configuration.value.branch_name
      root_folder     = github_configuration.value.root_folder
    }
  }
}

# Azure IR inside the ADF managed virtual network: all copy activity traffic uses private links.
resource "azurerm_data_factory_integration_runtime_azure" "managed" {
  name                    = "ir-managed-vnet"
  data_factory_id         = azurerm_data_factory.this.id
  location                = "AutoResolve"
  virtual_network_enabled = true
}

# Managed private endpoint to ADLS Gen2 (dfs). Needs one-time approval on the storage account,
# see docs/deployment.md.
resource "azurerm_data_factory_managed_private_endpoint" "adls" {
  name               = "mpe-adls-dfs"
  data_factory_id    = azurerm_data_factory.this.id
  target_resource_id = var.storage_account_id
  subresource_name   = "dfs"
}

# Self-hosted IR for the on-premises ERP SQL Server. Install the runtime on a VM in the
# source network and register it with the key from `az datafactory integration-runtime
# list-auth-key` (see docs/deployment.md).
resource "azurerm_data_factory_integration_runtime_self_hosted" "erp" {
  name            = "ir-onprem-shir"
  data_factory_id = azurerm_data_factory.this.id
  description     = "Reaches the on-premises ERP SQL Server."
}
