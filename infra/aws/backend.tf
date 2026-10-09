# Estado remoto em S3 com lock nativo (Terraform >= 1.10, sem DynamoDB).
# O bucket é criado por infra/aws/bootstrap. `bucket` e `region` entram por
# -backend-config para não fixar nomes aqui:
#
#   terraform init \
#     -backend-config="bucket=$(terraform -chdir=bootstrap output -raw tfstate_bucket)" \
#     -backend-config="region=us-east-1"
terraform {
  backend "s3" {
    key          = "aws/prd/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
