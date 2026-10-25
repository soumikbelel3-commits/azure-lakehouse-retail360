# Streaming ingestion for POS events. Standard tier is the minimum that supports Capture and
# Kafka. Entra-only authentication (local SAS keys are disabled).

resource "azurerm_eventhub_namespace" "this" {
  name                          = var.name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  sku                           = "Standard"
  capacity                      = 1
  auto_inflate_enabled          = true
  maximum_throughput_units      = 4
  local_authentication_enabled  = false
  public_network_access_enabled = false
  minimum_tls_version           = "1.2"
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_eventhub" "pos_events" {
  name              = "pos-events"
  namespace_id      = azurerm_eventhub_namespace.this.id
  partition_count   = var.partition_count
  message_retention = 1

  # Raw copy of every event as Avro for replay and audit. Authorised through the namespace
  # managed identity (role assignment lives in the root module).
  capture_description {
    enabled             = true
    encoding            = "Avro"
    interval_in_seconds = 300
    size_limit_in_bytes = 104857600

    destination {
      name                = "EventHubArchive.AzureBlockBlob"
      archive_name_format = "{Namespace}/{EventHub}/{PartitionId}/{Year}/{Month}/{Day}/{Hour}/{Minute}/{Second}"
      blob_container_name = var.capture_container_name
      storage_account_id  = var.capture_storage_account_id
    }
  }
}

resource "azurerm_eventhub_consumer_group" "databricks" {
  name                = "databricks"
  namespace_name      = azurerm_eventhub_namespace.this.name
  eventhub_name       = azurerm_eventhub.pos_events.name
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_endpoint" "namespace" {
  name                = "pep-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.name}"
    private_connection_resource_id = azurerm_eventhub_namespace.this.id
    subresource_names              = ["namespace"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}
