output "id" {
  value = azurerm_storage_account.this.id
}

output "name" {
  value = azurerm_storage_account.this.name
}

output "container_names" {
  value = { for k, c in azurerm_storage_container.this : k => c.name }
}
