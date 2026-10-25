output "vnet_id" {
  value = azurerm_virtual_network.this.id
}

output "private_endpoint_subnet_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "private_dns_zone_ids" {
  description = "Map of zone key (vault, servicebus, dfs, blob) to private DNS zone id."
  value       = { for k, z in azurerm_private_dns_zone.this : k => z.id }
}

output "databricks_public_subnet_name" {
  value = azurerm_subnet.dbx_public.name
}

output "databricks_private_subnet_name" {
  value = azurerm_subnet.dbx_private.name
}

output "databricks_public_nsg_association_id" {
  value = azurerm_subnet_network_security_group_association.dbx_public.id
}

output "databricks_private_nsg_association_id" {
  value = azurerm_subnet_network_security_group_association.dbx_private.id
}
