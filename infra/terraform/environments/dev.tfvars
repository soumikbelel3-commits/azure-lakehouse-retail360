# Non-secret settings for the dev environment. Pass the subscription id at plan time:
#   terraform plan -var-file=environments/dev.tfvars -var "subscription_id=$ARM_SUBSCRIPTION_ID"
environment    = "dev"
location       = "westeurope"
location_short = "weu"

vnet_address_space       = "10.10.0.0/16"
storage_replication_type = "ZRS"
log_retention_days       = 30
alert_email              = "data-eng-dev@example.com"

databricks_public_network_access = true
key_vault_purge_protection       = false

adf_github = null

tags = {
  cost_center = "data-platform"
  criticality = "low"
}
