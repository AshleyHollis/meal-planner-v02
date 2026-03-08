variable "environment_name" {
  description = "Environment name such as local, preview, or prod."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that hosts app-owned infrastructure."
  type        = string
}

variable "location" {
  description = "Azure location for app-owned infrastructure."
  type        = string
}
