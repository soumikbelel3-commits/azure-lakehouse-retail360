# Premium workspace (required for Unity Catalog, RBAC and private networking), injected into
# our VNet with secure cluster connectivity (no public IPs on cluster nodes).

resource "azurerm_databricks_workspace" "this" {
  name                        = "dbw-${var.prefix}"
  location                    = var.location
  resource_group_name         = var.resource_group_name
  sku                         = "premium"
  managed_resource_group_name = "rg-${var.prefix}-dbx-managed"

  public_network_access_enabled         = var.public_network_access
  network_security_group_rules_required = var.public_network_access ? "AllRules" : "NoAzureDatabricksRules"

  custom_parameters {
    no_public_ip                                         = true
    virtual_network_id                                   = var.virtual_network_id
    public_subnet_name                                   = var.public_subnet_name
    private_subnet_name                                  = var.private_subnet_name
    public_subnet_network_security_group_association_id  = var.public_subnet_nsg_assoc
    private_subnet_network_security_group_association_id = var.private_subnet_nsg_assoc
  }

  tags = var.tags
}

# Managed identity that Unity Catalog uses to reach ADLS (storage credential).
resource "azurerm_databricks_access_connector" "this" {
  name                = "dbac-${var.prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  identity {
    type = "SystemAssigned"
  }
}
