output "id" {
  value = azurerm_eventhub_namespace.this.id
}

output "name" {
  value = azurerm_eventhub_namespace.this.name
}

output "principal_id" {
  value = azurerm_eventhub_namespace.this.identity[0].principal_id
}

output "eventhub_name" {
  value = azurerm_eventhub.pos_events.name
}
