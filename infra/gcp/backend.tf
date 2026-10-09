# Estado remoto no GCS. O bucket é criado por infra/gcp/bootstrap (estado local).
# Inicialize com:
#   terraform init -backend-config="bucket=<PROJECT_ID>-tfstate"
# ou descomente `bucket` abaixo depois do bootstrap.
terraform {
  backend "gcs" {
    # bucket = "<PROJECT_ID>-tfstate"
    prefix = "def/prd"
  }
}
