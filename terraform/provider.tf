terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {

  # eval "$(aws configure export-credentials --profile default --format env)"
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "learning"
      ManagedBy   = "terraform"
    }
  }
}
