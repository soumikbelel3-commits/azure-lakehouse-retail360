# Hub-less, single-VNet layout for the data platform:
#   snet-dbx-host       Databricks "public" (host) subnet, delegated, no public IPs
#   snet-dbx-container  Databricks "private" (container) subnet, delegated
#   snet-private-endpoints  PaaS private endpoints (ADLS, Key Vault, Event Hubs)

locals {
  private_dns_zones = {
    vault      = "privatelink.vaultcore.azure.net"
    servicebus = "privatelink.servicebus.windows.net"
    dfs        = "privatelink.dfs.core.windows.net"
    blob       = "privatelink.blob.core.windows.net"
  }

  databricks_delegation_actions = [
    "Microsoft.Network/virtualNetworks/subnets/join/action",
    "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
    "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
  ]
}

resource "azurerm_virtual_network" "this" {
  name                = "vnet-${var.prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.address_space]
  tags                = var.tags
}

resource "azurerm_network_security_group" "databricks" {
  name                = "nsg-${var.prefix}-dbx"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
  # Required Databricks rules are injected by the service through the subnet delegation.
}

resource "azurerm_subnet" "dbx_public" {
  name                 = "snet-dbx-host"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [cidrsubnet(var.address_space, 8, 1)]

  delegation {
    name = "databricks"
    service_delegation {
      name    = "Microsoft.Databricks/workspaces"
      actions = local.databricks_delegation_actions
    }
  }
}

resource "azurerm_subnet" "dbx_private" {
  name                 = "snet-dbx-container"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [cidrsubnet(var.address_space, 8, 2)]

  delegation {
    name = "databricks"
    service_delegation {
      name    = "Microsoft.Databricks/workspaces"
      actions = local.databricks_delegation_actions
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                              = "snet-private-endpoints"
  resource_group_name               = var.resource_group_name
  virtual_network_name              = azurerm_virtual_network.this.name
  address_prefixes                  = [cidrsubnet(var.address_space, 8, 3)]
  private_endpoint_network_policies = "Enabled"
}

resource "azurerm_subnet_network_security_group_association" "dbx_public" {
  subnet_id                 = azurerm_subnet.dbx_public.id
  network_security_group_id = azurerm_network_security_group.databricks.id
}

resource "azurerm_subnet_network_security_group_association" "dbx_private" {
  subnet_id                 = azurerm_subnet.dbx_private.id
  network_security_group_id = azurerm_network_security_group.databricks.id
}

resource "azurerm_private_dns_zone" "this" {
  for_each            = local.private_dns_zones
  name                = each.value
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each             = local.private_dns_zones
  name                 = "link-${each.key}"
  private_dns_zone_id  = azurerm_private_dns_zone.this[each.key].id
  virtual_network_id   = azurerm_virtual_network.this.id
  registration_enabled = false
  tags                 = var.tags
}
