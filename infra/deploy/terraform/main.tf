locals {
  tags = {
    app         = "meal-planner-v02"
    environment = var.environment_name
    managed_by  = "terraform"
  }
}

data "azurerm_resource_group" "app" {
  name = var.resource_group_name
}
