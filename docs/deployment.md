# Deployment Guide

This repo now includes:

- a Docker image for the Streamlit UI,
- Terraform for the GCP runtime and GitHub OIDC wiring, and
- GitHub Actions for CI and Cloud Run deployment.

The workflows are configured to run when:

- you push directly to a branch,
- you open or update a pull request targeting `dev`, and
- that pull request is merged into `dev`.

## 1. Validate Locally

Create a Python 3.11 environment and run the tests:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Build and smoke-test the container locally:

```bash
docker build -t gcp-rag-demo:local .
docker run --rm -p 8080:8080 --env-file .env gcp-rag-demo:local
```

Then open `http://localhost:8080`.

## 2. Prepare Terraform Inputs

Copy the example variables file and fill in your values:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

At minimum, set:

- `project_id`
- `bucket_name`
- `github_owner`
- `github_repository`

## 3. Authenticate to Google Cloud

Use credentials that can create project resources:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## 4. Review and Apply Terraform

Initialize, validate, plan, and apply:

```bash
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
```

The first apply creates the Cloud Run service with a bootstrap image. The GitHub deploy workflow replaces that revision with your app image on the first successful deployment.

## 5. Capture the Important Outputs

After `terraform apply`, record these values:

```bash
terraform output
```

You will need:

- `artifact_registry_repository`
- `cloud_run_service_name`
- `github_workload_identity_provider`
- `github_deploy_service_account_email`

## 6. Configure GitHub Repository Settings

Add these repository variables in GitHub Actions settings:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `CLOUD_RUN_SERVICE`
- `IMAGE_NAME` set to `gcp-rag-demo` unless you want a different image name

Add these repository secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`

Use the Terraform outputs for the two secret values.

## 7. Test CI

Push a branch or open a pull request. Confirm that:

- the `CI` workflow passes, and
- the `Terraform Checks` workflow passes if you changed infrastructure files.

## 8. Test CD

Merge a pull request into `dev`, or run the `Deploy` workflow manually. Confirm that the workflow:

1. authenticates with Workload Identity Federation,
2. builds and pushes the Docker image to Artifact Registry, and
3. deploys the new image to Cloud Run.

Verify the service URL:

```bash
gcloud run services describe gcp-rag-demo \
  --region us-central1 \
  --format='value(status.url)'
```

If you changed the service name or region, use your Terraform values instead.

## 9. Verify the Running App

Open the Cloud Run URL, upload a PDF, and confirm that:

- the file lands in the configured bucket,
- index artifacts are written to Cloud Storage,
- Vertex AI Vector Search resources are created or updated, and
- the app returns grounded answers.

You can also inspect the latest revision:

```bash
gcloud run revisions list --service gcp-rag-demo --region us-central1
```

## 10. Day-Two Workflow

Use this flow after the first setup:

1. Make code changes.
2. Run `python -m pytest`.
3. If you changed deployment files, run `docker build -t gcp-rag-demo:local .`.
4. If you changed Terraform, run `terraform fmt -recursive && terraform validate`.
5. Push a branch and let CI validate the change.
6. Open a PR to `dev` for review and final validation.
7. Merge that PR to `dev` to ship the updated revision.
