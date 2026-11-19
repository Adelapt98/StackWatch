terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0, < 7.0" }
  }
}
provider "aws" { region = var.aws_region }
variable "aws_region" { type = string }
variable "bucket_name" { type = string }
resource "aws_s3_bucket" "reports" { bucket = var.bucket_name }
resource "aws_s3_bucket_public_access_block" "private" {
  bucket = aws_s3_bucket.reports.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "versions" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.reports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
output "bucket_name" { value = aws_s3_bucket.reports.id }
