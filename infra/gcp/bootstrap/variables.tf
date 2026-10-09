variable "project_id" {
  description = "ID do projeto GCP."
  type        = string
}

variable "region" {
  description = "Região do bucket de estado."
  type        = string
  default     = "southamerica-east1"
}
