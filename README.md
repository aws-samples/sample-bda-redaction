# Multimodal PII Redaction Using Amazon Bedrock

## Infrastructure

### Install Prerequisites

This application requires the installation of the following software tools:
* [Python v3.7 or higher](https://www.python.org/downloads/)
* [Node v18 or higher](https://nodejs.org/en/download/package-manager)
* [NPM v9.8 or higher](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
* [Docker](https://docs.docker.com/engine/install/)
* [AWS CDK v2.166 or higher](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)

VPC with 3 private subnets with no internet access

**Below Amazon SES Setup is optional. One can test the code without this setup as well. Code however expects email file to test the solution. To test the solution without setting up Amazon SES we should upload email file to be redacted to the raw S3 bucket created as part of CDK deployment under the folder domain_emails inside the bucket. Move directly to Deployment section if not using Amazon SES**

Setup Amazon SES with prod access and verify the domain/email identities for which the solution is to work. We also need to add the MX records in the DNS provider maintaining the domain. Please refer to the links below:

* [Request SES Production Access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
* [Setting up Amazon SES email receiving](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-setting-up.html)


Create credentials for SMTP and save it in secrets manager secret with name "SmtpCredentials". If using any other name for secret update the context.json line "secret_name" with the name of the secret created.
Key for the user name in the secret should be "smtp_username" and key for password should be "smtp_password" when storing the same in secrets manager

[Obtaining Amazon SES SMTP credentials](https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html)

### Deployment

Run all of the following commands from within a terminal/CLI environment which can include [AWS CloudShell](https://aws.amazon.com/cloudshell/).

The `infra/cdk.json` file tells the CDK Toolkit how to execute your app.

```sh
cd infra
```

**Optional:** Create and activate a new Python virutal environment

```sh
python3 -m venv .venv
./.venv/bin/activate
```

```sh
pip install -r requirements.txt
```

Create ```context.json``` file
```sh
cp context.json.example context.json
```

Update the ```context.json``` file with the correct configuration options for the environment.

| Property Name | Default | Description | Created |
| ------ | ---- | -------- | ---- |
| vpc_id | | VPC ID where resources will be deployed | VPC needs to be created prior to execution |
| raw_bucket | | S3 bucket storing raw messages and attachments | Created during CDK deployment |
| redacted_bucket_name | | S3 bucket storing redacted messages and attachments | Created during CDK deployment |
| inventory_table_name | | DynamoDB table name storing redacted message details | Created during CDK deployment |
| resource_name_prefix | | Prefix used when naming resources during the stack creation |
| retention | ```90``` | Number of days for retention of the messages in the redacted and raw S3 buckets |

The following properties are only required when the portal is being provisioned:

| Property Name | Default | Description |
| ------ | ---- | -------- |
| environment | ```development``` | The type of environment where resources will be provisioned. Valid options are ```local```, ```development```, ```production``` |
| auth_type | ```basic``` | The type of authentication used. Values are either ```oidc``` or ```basic``` |

The following set of configuration variables are only required if ```auth_type``` is set to ```oidc``` and the portal is being provisioned:

| Property Name | Default | Description |
| ------ | ---- | -------- |
| oidc_audience | | The unique identifier of the API |
| oidc_jwks_uri | | The OIDC JWKS URI |
| oidc_issuer | | The URI of the OIDC OP |
| authorized_users | ```[]``` | List of users identifiers that are authorized to use this application |

Use cases that require the usage of AWS SES to manage redacted email messages will need to set the following configuration variables. Otherwise, they are optional:

| Property Name | Default | Description | Comment |
| ------ | ---- | -------- | ---------|
| domain | | The domain name that is used for AWS SES | This can be left blank if not setting up Amazon SES
| auto_reply_from_email | | Email address of the "from" field of the email message | This can be left blank if not setting up the Portal
| secret_name | | AWS Secrets Manager secret containing SMTP credentials for forward email functionality from the portal | This can be left blank if not setting up the Portal

The following set of configuration variables are optional:

| Property Name | Default | Description | Required |
| ------ | ---- | -------- | ------- |
| api_gateway_vpc_endpoint_id |  | VPC Endpoint ID for API Gateway. Created if no value is provided. | No |
| kms_cmk_arn |  | ARN of customer-managed KMS key. Created if no value is provided. | No |
| api_domain_name |  | API Gateway custom domain name (must be registered as a CNAME within a Route 53 Hosted Zone that references the domain_name_alias_domain_name). | No |
| api_domain_cert_arn |  | ARN of ACM certificate to be used with the API Gateway custom domain name (required with usage of api_domain_name). | Yes, if ```api_domain_name``` is set |

#### Update Lambda Layer that contains additional PyPI packages

Update packages (if necessary) by updating the 3 requirements files listed below:

1. ```infra/pii_redaction/lambda/lambda-layer/requirements.txt```
2. ```infra/pii_redaction/lambda/emailProcessing/lambda-layer/requirements.txt```
3. ```infra/pii_redaction/lambda/attachmentProcessing/lambda-layer/requirements.txt```

Build the lambda layers

```sh
cd pii_redaction/lambda

cd lambda-layer
chmod +x build_layer.sh
./build_layer.sh

cd ..
cd attachmentProcessing/lambda-layer
chmod +x build_layer.sh
./build_layer.sh

cd ../..
cd emailProcessing/lambda-layer
chmod +x build_layer.sh
./build_layer.sh

# Navigate back to the root of the infra directory
cd ../../../..
```

#### Deploy Infrastructure

Run the following commands from the root of the ```infra``` directory:

Bootstrap the AWS account to use AWS CDK
```sh
cdk bootstrap
```

At this point you can now synthesize the CloudFormation template for this code.

```sh
cdk synth
```

The generated CloudFormation templates should be run in the account(s) where the resources should be launched.

### Local Deployment

If you are deploying the through a local environment that is outside of a pipeline, follow the instructions from the **Deployment** section. After those steps have been completed, run:

```sh
cdk deploy [resource_name_prefix]-S3Stack [resource_name_prefix]-ConsumerStack
```

To deploy the React-based portal optionally:

```sh
cdk deploy [resource_name_prefix]-PortalStack
```

### API Gateway Custom Domain Setup

This is needed for deployment within a non-production or production environment. Within your AWS Console, navigate to API Gateway and click on _Custom domain names_ link in the API Gateway navigation menu on the left-hand side of the screen. [Learn more information about API Gateway custom domain names](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html?icmpid=apigateway_console_help)

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

### Validation

#### Local Deployment
Running the CDK deployment through a local environment will notify the user if there is a failure through the CLI. 

#### Production Deployment
Validating in a production environment through a pipeline, you will be notified of a failure through the pipeline action/stage.

#### Rollback Procedures
Deployment failures will always rollback the current deployment and return the CloudFormation stack(s) to their previous revision without an impact to current operations, configuration and existing resources. The exact error will be displayed in the CLI output and also in the CloudFormation stack events tab.

## Portal

**IMPORTANT:** The installation of the portal is completely optional. It is only required if you want a user interface to view the redacted emails. You can skip this section and check the AWS console of the AWS account where the solution is deployed to view the resources created.

### Install Prerequisites

This application requires the installation of the following software tools:
* [TypeScript](https://www.typescriptlang.org/)
* [Node v18 or higher](https://nodejs.org/en/download/package-manager)
* [NPM v9.8 or higher](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)

### Authentication

The portal is protected by Basic Authentication or authentication using OIDC. When using Basic Access Authentication the credentials are stored in Secrets Manager using the secret provisioned in the PortalStack that was created via CDK.

### Environment Variables

Navigate to the root of the ```app``` directory and update the following variables in the ```.env``` file (by copying the ```.env.example``` file to ```.env```) using the following command to create the ```.env``` file using a terminal/CLI or AWS CloudShell:

```sh
cp .env.example .env
```

| Environment Variable Name | Default | Description | Required |
| ------ | ---- | -------- | --------- |
| VITE_APIGW | | URL of API Gateway (without the path part of "/portal") generated in the PortalStack CloudFormation stack | Yes

Authentication through OpenID Connect (OIDC) requires the following environment variables to be set. Otherwise, they are optional if using Basic Access Authentication.

| Environment Variable Name | Default | Description |
| ------ | ---- | -------- |
| VITE_OIDC_DOMAIN |  | FQDN for the OIDC OP |
| VITE_OIDC_CLIENT_ID |  | Unique identifier for the OIDC RP |
| VITE_OIDC_AUDIENCE |  | The unique identifier (FQDN) of the API |
| VITE_OIDC_SCOPES | ```openid email profile user_alias username``` | The OIDC scopes that provide access to standard claims |

Include the ```VITE_OIDC_METADATA_URL``` environment variable if all necessary OIDC configuration values are provided through it:

| Environment Variable Name | Default | Description |
| ------ | ---- | -------- |
| VITE_OIDC_METADATA_URL | | OIDC Metadata URL |

Otherwise, do not provide a value for ```VITE_OIDC_METADATA_URL``` and provide these additional environment variables to help configure access to your OIDC provider:

| Environment Variable | OIDC Parameter | Description | Default |
|---------------------|----------------|-------------|---------|
| VITE_OIDC_METADATA_ISSUER | issuer | URL that the OpenID Provider asserts as its Issuer Identifier | None |
| VITE_OIDC_METADATA_AUTHORIZATION_ENDPOINT | authorization_endpoint | URL of the OP's OAuth 2.0 Authorization Endpoint where authentication and authorization occurs | None |
| VITE_OIDC_METADATA_TOKEN_ENDPOINT | token_endpoint | URL of the OP's OAuth 2.0 Token Endpoint where access tokens are obtained | None |
| VITE_OIDC_METADATA_USERINFO_ENDPOINT | userinfo_endpoint | URL of the OP's UserInfo Endpoint where claims about the authenticated end-user can be obtained | None |
| VITE_OIDC_METADATA_JWKS_URI | jwks_uri | URL of the OP's JSON Web Key Set document containing signing keys | None |
| VITE_OIDC_METADATA_INTROSPECTION_ENDPOINT | introspection_endpoint | URL of the OP's OAuth 2.0 Token Introspection Endpoint for validating tokens | None |
| VITE_OIDC_METADATA_REVOCATION_ENDPOINT | revocation_endpoint | URL of the OP's OAuth 2.0 Token Revocation Endpoint for revoking tokens | None |
| VITE_OIDC_METADATA_END_SESSION_ENDPOINT | end_session_endpoint | URL of the OP's End Session Endpoint for logging out | None |
| VITE_OIDC_METADATA_RESPONSE_TYPES_SUPPORTED | response_types_supported | List of OAuth 2.0 response_type values supported by the OP | token,id_token,token id_token,code,code id_token,code token id_token,code token,none |
| VITE_OIDC_METADATA_SUBJECT_TYPES_SUPPORTED | subject_types_supported | List of Subject Identifier types supported by the OP | public |

Control the OIDC logout flow by assigning values to the following environment variables. These variables are optional otherwise:

| Environment Variable | OIDC Parameter | Description | Default |
|---------------------|----------------|-------------|---------|
| VITE_OIDC_LOGOUT_URL | | OIDC Logout URL (if not available through OIDC Metadata URL) |
| VITE_OIDC_LOGOUT_RETURN_URL | | OIDC Logout Return URL (if not available through OIDC Metadata URL) |

### Local Development

Run all of the following commands from within a terminal/CLI environment which can include [AWS CloudShell](https://aws.amazon.com/cloudshell/).

Navigate to the root of the ```app``` directory before running any of the following commands to run the local development server by running the following commands:

- Install NPM packages
```sh
npm install
```

- Create an environment file and fill in the values for the necessary environment variables as described in the **Environment Variables** section above (if you have not performed this action previously):
```sh
cp .env.example .env
```

- Start the local development server

```sh
npm run dev
```

The local development server is managed by [Vite](https://vite.dev/) and will begin running locally on port **5173** by default. If you need [to customize the port, you can follow these directions](https://vite.dev/guide/cli).

#### Preview Production Build

The production build of the application can also be viewed locally by running
```sh
npm run preview
```

By default, the preview of the production build will run locally on port **4173**. If you need [to customize the port, you can follow these instructions](https://vite.dev/guide/cli#vite-preview).

### Production Deployment

Run all of the following commands from within a terminal environment which can include [AWS CloudShell](https://aws.amazon.com/cloudshell/).

Navigate to the root of the ```app``` directory before running any of the following commands to build this application for production by running the following commands:

- Install NPM packages
```sh
npm install
```

- Create an environment file and fill in the values for the necessary environment variables as described in the **Environment Variables** section above (if you have not performed this action previously):
```sh
cp .env.example .env
```

- Build the files
```sh
npm run build
```

After the build succeeds, transfer all of the files within the _dist/_ directory into the Amazon S3 bucket that is designated for these assets (specified in the PortalStack provisioned via CDK).

Example:
```sh
aws s3 sync dist/ s3://[name-of-bucket] --delete
```

Once the files have been transferred successfully, you can view the portal using either the API Gateway URL or the domain name that is configured to serve requests.
