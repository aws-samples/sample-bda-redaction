# Multimodal PII Redaction Using Amazon Bedrock

## Solution Architecture 
The following diagram outlines the solution architecture. 

<img alt="PII Detection   Redaction Amazon Bedrock" src="https://github.com/user-attachments/assets/a57f9fa2-f02b-44cd-92dc-39e1f8c09e8b" />

The diagram illustrates the backend PII detection and redaction workflow and the frontend application user interface orchestrated by [AWS Lambda](https://aws.amazon.com/lambda/) and [Amazon EventBridge](https://aws.amazon.com/eventbridge/). The process follows these steps:
1.	The workflow starts with the user sending an email to the incoming email server hosted on [Amazon Simple Email Service](https://aws.amazon.com/ses/) (Amazon SES)(optional). 
2.	Amazon SES then stores the emails and attachments in an [Amazon Simple Storage Service](https://aws.amazon.com/s3/) (S3) landing bucket. 
3.	An S3 event notification triggers the initial processing AWS Lambda function that generates a unique case ID and creates a tracking record in [Amazon DynamoDB](https://aws.amazon.com/dynamodb/).
4.	Lambda orchestrates the PII detection and redaction workflow by extracting email body and attachments from the email and saving in raw email bucket followed by invoking [Amazon Bedrock Data Automation](https://aws.amazon.com/bedrock/bda/) and [Amazon Bedrock Guardrails](https://aws.amazon.com/bedrock/guardrails/) for detecting and redacting PII. 
5.	Amazon Bedrock Data Automation processes attachments to extract text from the files.
6.	Amazon Bedrock Guardrails detects and redacts the PII from both email body and text from attachments, and then stores the redacted content in another S3 bucket.
7.	DynamoDB tables are updated with email messages, folders metadata, and email filtering rules. 
8.	An Amazon EventBridge Scheduler is used to run the Rules Engine Lambda on a schedule which will process new emails that have yet to be categorized into folders based on enabled email filtering rules criteria. 
9.	The Rules Engine Lambda also communicates with DynamoDB to access the messages table and the rules table.
10.	Users access the application user interface with OpenID Connect or Basic Authentication through [AWS Web Application Firewall](https://aws.amazon.com/waf/). 
11.	[Amazon API Gateway](https://aws.amazon.com/api-gateway/) manages user API requests.
12.	A Portal API Lambda fetches the case details based on user requests.
13.	The static assets served by API Gateway are stored in a private S3 bucket.
14.	[Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [AWS CloudTrail](https://aws.amazon.com/cloudtrail/) provide visibility into the PII detection and redaction process, while [Amazon Simple Notification Service](https://aws.amazon.com/sns/) delivers real-time alerts for any failures, ensuring immediate attention to issues.

## Infrastructure

### Install Prerequisites

This application requires the installation of the following software tools:
* [Python v3.7 or higher](https://www.python.org/downloads/)
* [Node v18 or higher](https://nodejs.org/en/download/package-manager)
* [NPM v9.8 or higher](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
* [AWS CDK v2.166 or higher](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
* Terminal/CLI such as macOS Terminal, PowerShell or Windows Terminal, or the Linux command line. [AWS CloudShell](https://aws.amazon.com/cloudshell/) can also be used when all code is located within an AWS account.

### Infrastructure Prerequites
An existing [VPC](https://docs.aws.amazon.com/vpc/latest/userguide/create-vpc.html) that contains 3 private subnets with no internet access is needed.

### CloudFormation Stacks

When deploying this solution, there will be 2-3 CloudFormation stacks that will be deployed in your AWS account:
* **S3Stack** - Provisions the core infrastructure including S3 buckets for raw and redacted email storage with automatic lifecycle policies, a DynamoDB table for email metadata tracking with time-to-live (TTL) and global secondary indexes, and VPC security groups for secure Lambda function access. It also creates IAM roles with comprehensive permissions for S3, DynamoDB, and Bedrock services, forming the secure foundation for the entire PII detection and redaction workflow.

* **ConsumerStack** - Provisions the core processing infrastructure including Amazon Bedrock Data Automation projects for document text extraction and Bedrock Guardrails configured to anonymize comprehensive PII entities, along with Lambda functions for email and attachment processing with SNS topics for success/failure notifications. It also creates SES receipt rules for incoming email handling when a domain is configured, Lambda layers for dependency management, and S3 event notifications to trigger the email processing workflow automatically.

* **PortalStack (optional)** - Provisions the optional web interface including a private API Gateway with Lambda authorizers for Basic Auth or OIDC authentication, DynamoDB tables for folders and rules management, and S3 buckets for static web assets with WAF protection. It also creates EventBridge schedulers for automated rules processing, CloudTrail logging for DynamoDB data plane operations, and Lambda functions for portal API handling and email forwarding functionality when configured.

### Amazon SES (optional)

**Move directly to the Deployment section below if you are not using Amazon SES**

Below Amazon SES Setup is optional. One can test the code without this setup as well. The code, however, expects an email file to test the solution. To test the solution without setting up Amazon SES we should upload email file to be redacted to the raw S3 bucket created as part of CDK deployment under the folder ```domain_emails``` inside the S3 bucket.

Set up Amazon SES with prod access and verify the domain/email identities for which the solution is to work. We also need to add the MX records in the DNS provider maintaining the domain. Please refer to the links below:

* [Request SES Production Access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
* [Setting up Amazon SES email receiving](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-setting-up.html)

Create credentials for SMTP and save it in secrets manager secret with name ```SmtpCredentials```. If using any other name for secret update the ```context.json``` line ```secret_name``` with the name of the secret created.
Key for the user name in the secret should be ```smtp_username``` and key for password should be ```smtp_password``` when storing the same in secrets manager

* [Obtaining Amazon SES SMTP credentials](https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html)

### Deployment

Run all of the following commands from within a terminal/CLI environment.

Clone the repository

```sh
git clone https://github.com/aws-samples/sample-bda-redaction.git
```

The `infra/cdk.json` file tells the CDK Toolkit how to execute your app.

```sh
cd sample-bda-redaction/infra/
```

**Optional:** Create and activate a new Python virutal environment

```sh
python3 -m venv .venv
. .venv/bin/activate
```

```sh
pip install -r requirements.txt
```

Create ```context.json``` file
```sh
cp context.json.example context.json
```

Update the ```context.json``` file with the correct configuration options for the environment.

| Property Name | Default | Description | When to Create |
| ------ | ---- | -------- | ---- |
| vpc_id |N/A| VPC ID where resources will be deployed | VPC needs to be created prior to execution |
| raw_bucket |N/A| S3 bucket storing raw messages and attachments | Created during CDK deployment |
| redacted_bucket_name |N/A| S3 bucket storing redacted messages and attachments | Created during CDK deployment |
| inventory_table_name |N/A| DynamoDB table name storing redacted message details | Created during CDK deployment |
| resource_name_prefix |N/A| Prefix used when naming resources during the stack creation | During stack creation |
| retention | ```90``` | Number of days for retention of the messages in the redacted and raw S3 buckets | During stack creation|

The following properties are only required when the portal is being provisioned:

| Property Name | Default | Description | Comments |
| ------ | ---- | -------- | ----- |
| environment | ```development``` | The type of environment where resources will be provisioned. Values are ```local```, ```development```, ```production``` | Setting this property to ```local``` will make create a regional API Gateway. Otherwise, it will be a Private API Gateway |
| auth_type | ```basic``` | The type of authentication used. Values are either ```oidc``` or ```basic``` | |

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
| auto_reply_from_email | | Email address of the "from" field of the email message. Also used as the email address where emails are forwarded from the Portal application | This can be left blank if not setting up the Portal
| secret_name | | AWS Secrets Manager secret containing SMTP credentials for forward email functionality from the portal | This can be left blank if not setting up the Portal

The following set of configuration variables are optional:

| Property Name | Default | Description | Required |
| ------ | ---- | -------- | ------- |
| api_gateway_vpc_endpoint_id |  | VPC Endpoint ID for API Gateway. Created if no value is provided. | No |
| kms_cmk_arn |  | ARN of customer-managed KMS key. Created if no value is provided. | No |
| api_domain_name |  | API Gateway custom domain name (must be registered as a CNAME within a Route 53 Hosted Zone that references the domain_name_alias_domain_name). | No |
| api_domain_cert_arn |  | ARN of ACM certificate to be used with the API Gateway custom domain name (required with usage of api_domain_name). | Yes, if ```api_domain_name``` is set |

#### Update Lambda Layer that contains additional PyPI packages

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

At this point you can now synthesize the CloudFormation template for this code. Additional environment variables before the cdk synth suppresses the warnings

```sh
JSII_DEPRECATED=quiet JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=quiet cdk synth --no-notices
```

```sh
JSII_DEPRECATED=quiet JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=quiet cdk deploy <<resource_name_prefix>>-S3Stack <<resource_name_prefix>>-ConsumerStack --no-notices
```

To deploy the React-based portal optionally:

```sh
JSII_DEPRECATED=quiet JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=quiet cdk deploy <<resource_name_prefix>>-PortalStack --no-notices
```

### Validation

#### Deployment
Running the CDK deployment through a Terminal/CLI environment will notify the user if there is a deployment failure through ```stderr``` in the Terminal/CLI enviroment.

#### Rollback Procedures
Deployment failures will always rollback the current deployment and return the CloudFormation stack(s) to their previous revision without an impact to current operations, configuration and existing resources. The exact error will be displayed in the CLI output and also in the CloudFormation stack events tab.

## Portal

**IMPORTANT:** The installation of the portal is completely optional. It is only required if you want a user interface to view the redacted emails. You can skip this section and check the AWS console of the AWS account where the solution is deployed to view the resources created.

### Install Prerequisites

This application requires the installation of the following software tools:
* [TypeScript](https://www.typescriptlang.org/)
* [Node v18 or higher](https://nodejs.org/en/download/package-manager)
* [NPM v9.8 or higher](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)

### API Gateway Custom Domain Setup

An API Gateway Custom Domain is required for deployment since the API Gateway provisioned by the ```PortalStack``` CloudFormation stack is a private API Gateway. 

Within your AWS Console, navigate to API Gateway and click on **_Custom domain names_** link in the API Gateway navigation menu on the left-hand side of the screen.

To complete this process you will need a custom domain name. [Learn more about creating a private custom domain name](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-private-custom-domains-tutorial.html).

1. Enter the name of the domain or subdomain
2. Select the **_Private_** option
3. Select **_API mappings only_** for the routing mode
3. Choose the proper ACM (AWS Certificate Manager) Certificate

Next, configure the API Mappings:

1. Select your API that was provisioned from the ```PortalStack``` CloudFormation stack from the dropdown
2. Select the stage for the API
3. **DO NOT** enter a path

Once you have completed these two sets of steps, navigate to the **_Domain name access associations_** area of API Gateway.

1. Enter the Domain name ARN from the Endpoint configuration of the custom domain you created previously as the value of the **_Domain name ARN_**
2. Select the VPC Endpoint ID. The VPC Endpoint should reference the endpoint used for API Gateway.


### Authentication

The portal is protected by Basic Authentication or authentication using OIDC. When using Basic Access Authentication the credentials are stored in [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) using the secret provisioned in the ```PortalStack``` CloudFormation stack that was created via AWS CDK. The CloudFormation stack resource is named ```PiiRedactionPortalAuthSecret```.

### Environment Variables

Create a new environment file by navigating to the root of the ```app``` directory and update the following variables in the ```.env``` file (by copying the ```.env.example``` file to ```.env```) using the following command to create the ```.env``` file using a terminal/CLI environment:

```sh
cp .env.example .env
```

You can also create the file using your preferred text editor as well.

| Environment Variable Name | Default | Description | Required |
| ------ | ---- | -------- | --------- |
| VITE_APIGW | | URL of domain or subdomain that was used to create an API Gateway custom domain (described above) | Yes
| VITE_EMAIL_ENABLED | false | Enables/disables the forward email function. Values are ```true``` to enable the feature or ```false``` to disable it | Yes

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

<!-- ### Local Development

Run all of the following commands from within a terminal/CLI environment.

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

By default, the preview of the production build will run locally on port **4173**. If you need [to customize the port, you can follow these instructions](https://vite.dev/guide/cli#vite-preview). -->

### Deployment

**IMPORTANT:** This portal is designed to be run within an environment that has access to the AWS VPC that was set in the ```context.json``` file. Access to this portal from another environment or publicly will be denied.

To bypass the creation of a private API Gateway, set the ```environment``` property in ```context.json``` to ```local``` to create a regional API Gateway.

Run all of the following commands from within a terminal/CLI environment.

Change the value of ```VITE_BASE``` in the ```.env``` file:
```sh
VITE_BASE=
```

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
aws s3 sync dist/ s3://<<resource_name_prefix>>-private-web-hosting-assets --delete
```

Once the files have been transferred successfully, you can view the portal using either the API Gateway URL or the domain name that is configured to serve requests.
