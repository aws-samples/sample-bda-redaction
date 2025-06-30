## Install Prerequisites

This application requires the installation of the following software tools:
* [Python v3.7 or higher](https://www.python.org/downloads/)
* [Node v18 or higher](https://nodejs.org/en/download/package-manager)
* [NPM v9.8 or higher](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
* [Yarn 1.22 or higher](https://yarnpkg.com/getting-started/install)
* [Docker](https://docs.docker.com/engine/install/)
* [AWS CDK v2.166 or higher](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)

VPC with 3 private subnets with no internet access

Setup Amazon SES with prod access and verify the domain/email identities for which the solution is to work. We also need to add the MX records in the DNS provider maintaining the domain. Please refer below links.

https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html

https://docs.aws.amazon.com/ses/latest/dg/receiving-email-setting-up.html


Create credentials for SMTP and save it in secrets manager secret with name "SmtpCredentials". If using any other name for secret update the context.json line "secret_name" with the name of the secret created.
Key for the user name in the secret should be "smtp_username" and key for password should be "smtp_password" when storing the same in secrets manager

https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html

## Production Deployment

The `cdk.json` file tells the CDK Toolkit how to execute your app.

```
$ pip install -r requirements.txt
```

Install NPM packages
```
yarn install
```

Create ```context.json``` file
```sh
cp context.json.example context.json
```

Update the ```context.json``` file with the correct configuration options for the environment.

| Property Name | Default | Description |
| ------ | ---- | -------- |
| vpc_id | | VPC ID where resources will be deployed |
| raw_bucket | pii-redacted-raw-test-bucket | S3 bucket storing raw emails and attachments |
| redacted_bucket_name | pii-redacted-redacted-test-bucket | S3 bucket storing redacted emails and attachments |
| inventory_table_name | pii-redacted-email-inventory | DynamoDB table name storing redacted message details |
| secret_name | piiRedactedSmtpCredentials | AWS Secrets Manager secret containing SMTP credentials |
| auto_reply_from_email | | Email address of the "from" field of the email message |
| retention | 1 | Number of days for the ttl of DynamoDB email message records and days of retention for emails in the redacted and raw S3 buckets |
| resource_name_prefix | oopcip | Prefix used when naming resources during the provisioning |
| domain | | The domain name that is used for AWS SES |
| environment | | The type of environment where resources will be provisioned. Valid options are "local", "development", "production" |
| oidc_audience | | The unique identifier of the API |
| oidc_jwks_uri | | The OIDC JWKS URI |
| oidc_issuer | | The URI of the OIDC OP |
| authorized_users | | List of users identifiers that are authorized to use this application |
| auth_type | basic | The type of authentication used. Values are either "oidc" or "basic" |
| api_gateway_vpc_endpoint_id |  | VPC Endpoint ID for API Gateway |
| kms_cmk_arn |  | ARN of customer-managed KMS key |
| api_domain_name |  | API Gateway custom domain name (must be registered as a CNAME within a Route 53 Hosted Zone that references the domain_name_alias_domain_name) |
| api_domain_cert_arn |  | ARN of ACM certificate to be used with the API Gateway custom domain name (required with usage of api_domain_name) |

### Update Lambda Layer that contains additional PyPI packages

Update packages (if necessary) by updating below 3 requirements files.

1. ```pii_redaction/lambda/lambda-layer/requirements.txt```
2. ```pii_redaction/lambda/emailProcessing/lambda-layer/requirements.txt```
3. ```pii_redaction/lambda/attachmentProcessing/lambda-layer/requirements.txt```

Build the lambda layer

```sh
cd pii_redaction/lambda/lambda-layer
chmod +x build_layer.sh
./build_layer.sh
```

### Deploy Infrastructure

Bootstrap the AWS account to use AWS CDK
```sh
$ cdk bootstrap
```

At this point you can now synthesize the CloudFormation template for this code.

```sh
$ cdk synth
```

The generated CloudFormation templates should be run in the account(s) where the resources should be launched.

## Local Deployment

If you are deploying the through a local environment that is outside of a pipeline, follow the instructions from the **Production Deployment** section. After those steps have been completed, run the following command:

```sh
cdk deploy --all
```

## API Gateway Custom Domain Setup

This is needed for deployment within a non-production or production environment.

1. Enter the name of the domain or subdomain
2. Select the "Private" option
3. Choose the proper ACM Certificate

Next, configure the API Mappings:

1. Select your API from the dropdown
2. Select the stage for the API
3. DO NOT enter a path

Once you have completed these two sets of steps, navigate to the "Domain name access associations" area of API Gateway.

1. Select the ARN of the newly-created API Gateway Domain Name
2. Select the VPC Endpoint ID. The VPC Endpoint should reference the endpoint used for API Gateway.

## Validation

### Local Deployment
Running the CDK deployment through a local environment will notify the user if there is a failure through the CLI. 

### Production Deployment
Validating in a production environment through a pipeline, you will be notified of a failure through the pipeline action/stage.

### Rollback Procedures
Deployment failures will always rollback the current deployment and return the CloudFormation stack(s) to their previous revision without an impact to current operations, configuration and existing resources. The exact error will be displayed in the CLI output and also in the CloudFormation stack events tab.