output "id" {
  value = azurerm_data_factory.this.id
}

output "name" {
  value = azurerm_data_factory.this.name
}

output "principal_id" {
  value = azurerm_data_factory.this.identity[0].principal_id
}

output "self_hosted_ir_name" {
  value = azurerm_data_factory_integration_runtime_self_hosted.erp.name
}
