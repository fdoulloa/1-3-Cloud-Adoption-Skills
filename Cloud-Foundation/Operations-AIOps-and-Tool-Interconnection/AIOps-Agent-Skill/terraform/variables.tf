variable "region" {
  description = "Huawei Cloud region"
  type        = string
  default     = "la-north-2"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_cidr" {
  description = "Subnet CIDR block"
  type        = string
  default     = "192.168.0.0/24"
}

variable "operator_cidr" {
  description = "CIDR block for operator access (SSH, HTTPS)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "css_node_count" {
  description = "Number of CSS data nodes"
  type        = number
  default     = 3
}

variable "css_flavor" {
  description = "CSS node flavor"
  type        = string
  default     = "ess.spec-4u8g"
}

variable "css_volume_size" {
  description = "CSS node volume size in GB"
  type        = number
  default     = 40
}

variable "css_engine_version" {
  description = "CSS engine version"
  type        = string
  default     = "7.10.2"
}

variable "ecs_flavor" {
  description = "ECS flavor for agent runtime"
  type        = string
  default     = "c7.large.2"
}

variable "ecs_image_id" {
  description = "ECS image ID (Ubuntu 22.04)"
  type        = string
  default     = ""
}

variable "approval_email" {
  description = "Email for approval notifications"
  type        = string
}

variable "project_id" {
  description = "Huawei Cloud project ID"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "aiops"
}
