environment    = "prod"
location       = "westeurope"
location_short = "weu"

vnet_address_space       = "10.20.0.0/16"
storage_replication_type = "GZRS"
log_retention_days       = 90
alert_email              = "data-eng-oncall@example.com"

# Flip to false once Front-end Private Link and a jump host / VPN are in place.
databricks_public_network_access = true
key_vault_purge_protection       = true

adf_github = {
  account_name    = "soumikbelel3-commits"
  repository_name = "azure-lakehouse-retail360"
  branch_name     = "main"
  root_folder     = "/adf"
}

tags = {
  cost_center = "data-platform"
  criticality = "high"
}
