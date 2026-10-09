output "tfstate_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}

output "init_command" {
  value = "terraform -chdir=.. init -backend-config=\"bucket=${aws_s3_bucket.tfstate.bucket}\" -backend-config=\"region=${var.region}\""
}
