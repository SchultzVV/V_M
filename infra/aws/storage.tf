# ------------------------------------------------------------------
# S3: media (imagens dos produtos, chave = <plataforma>/<arquivo>) e
# frontend (dist do React). Ambos privados, lidos só pelo CloudFront (OAC).
# ------------------------------------------------------------------
resource "random_id" "bucket_suffix" {
  byte_length = 3
}

locals {
  buckets = {
    media    = "${local.name}-media-${random_id.bucket_suffix.hex}"
    frontend = "${local.name}-frontend-${random_id.bucket_suffix.hex}"
  }
}

resource "aws_s3_bucket" "media" {
  bucket        = local.buckets.media
  force_destroy = !var.deletion_protection
  tags          = { Name = local.buckets.media }
}

resource "aws_s3_bucket" "frontend" {
  bucket        = local.buckets.frontend
  force_destroy = true
  tags          = { Name = local.buckets.frontend }
}

locals {
  bucket_ids = {
    media    = aws_s3_bucket.media.id
    frontend = aws_s3_bucket.frontend.id
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = local.bucket_ids

  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "this" {
  for_each = local.bucket_ids

  bucket = each.value

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = local.bucket_ids

  bucket = each.value

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = local.bucket_ids

  bucket = each.value

  rule {
    id     = "abort-multipart"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [for h in local.aliases : "https://${h}"]
    max_age_seconds = 3600
  }
}

# Leitura pelo CloudFront (OAC) — a distribuição é a única principal permitida.
data "aws_iam_policy_document" "bucket_cloudfront" {
  for_each = {
    media    = aws_s3_bucket.media.arn
    frontend = aws_s3_bucket.frontend.arn
  }

  statement {
    sid       = "AllowCloudFrontOAC"
    actions   = ["s3:GetObject"]
    resources = ["${each.value}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  policy = data.aws_iam_policy_document.bucket_cloudfront["media"].json

  depends_on = [aws_s3_bucket_public_access_block.this]
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.bucket_cloudfront["frontend"].json

  depends_on = [aws_s3_bucket_public_access_block.this]
}
