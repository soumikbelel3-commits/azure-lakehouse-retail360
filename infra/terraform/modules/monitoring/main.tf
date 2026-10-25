resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days
  tags                = var.tags
}

resource "azurerm_monitor_action_group" "data_platform" {
  name                = "ag-${var.prefix}-data-platform"
  resource_group_name = var.resource_group_name
  short_name          = "dataplat"
  tags                = var.tags

  email_receiver {
    name                    = "data-engineering-oncall"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}
