provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

# Certificados do CloudFront precisam estar em us-east-1, seja qual for a região principal.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.tags
  }
}
