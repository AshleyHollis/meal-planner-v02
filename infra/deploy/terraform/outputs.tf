output "resource_group_id" {
  description = "Resource group identifier for downstream modules."
  value       = data.azurerm_resource_group.app.id
}
