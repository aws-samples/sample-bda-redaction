#!/usr/bin/env python3
import aws_cdk as cdk
import os
import json
from pii_redaction.portal_stack import PortalStack
from pii_redaction.s3_stack import S3Stack
from pii_redaction.consumer_stack import ConsumerStack
from pii_redaction.helpers.index import stackPrefix
from cdk_nag import AwsSolutionsChecks

app = cdk.App()

# Add the CDK Nag pack to your CDK app
#cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Read context values from context.json file
with open('context.json', 'r') as file:
    context_values = json.load(file)

if context_values:
    raw_bucket_name = context_values['resource_names'].get('raw_bucket', 'RawBucket')
    redacted_bucket_name = context_values['resource_names'].get('redacted_bucket_name', 'RedactedBucket')
    inventory_table_name = context_values['resource_names'].get('inventory_table_name', 'EmailInventoryTable')
    vpc_id = context_values['resource_names'].get('vpc_id', 'MyVPC')
    secret_name = context_values['resource_names'].get('secret_name', 'MySecret')
    auto_reply_email = context_values['resource_names'].get('auto_reply_email', 'MyAutoReplyEmail')
    auto_reply_from_email = context_values['resource_names'].get('auto_reply_from_email', 'MyAutoReplyFromEmail')
    retention = context_values['resource_names'].get('retention', 'MyRetention')
    resource_name_prefix = context_values['resource_names'].get('resource_name_prefix', 'ResourceNamePrefix')
    domain = context_values['resource_names'].get('domain', 'domain')
    environment = context_values['resource_names'].get('environment', 'environment')
    oidc_audience = context_values['resource_names'].get('oidc_audience', 'oidc_audience')
    oidc_jwks_uri = context_values['resource_names'].get('oidc_jwks_uri', 'oidc_jwks_uri')
    oidc_issuer = context_values['resource_names'].get('oidc_issuer', 'oidc_issuer')
    authorized_users = context_values['resource_names'].get('authorized_users', 'authorized_users')
    auth_type = context_values['resource_names'].get('auth_type', 'auth_type')
    kms_cmk_arn = context_values['resource_names'].get('kms_cmk_arn')
    api_domain_name = context_values['resource_names'].get('api_domain_name')
    api_domain_cert_arn = context_values['resource_names'].get('api_domain_cert_arn')
else:
    print("No context values found. Please provide the same")
    exit(1)  # Exit with an error code

s3_stack = S3Stack(app, stackPrefix(resource_name_prefix, "S3Stack"), 
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    raw_bucket_name=raw_bucket_name,
    redacted_bucket_name=redacted_bucket_name,
    table_name=inventory_table_name,
    vpc_id=vpc_id,
    # secret_name=secret_name,
    retention=retention,
    resource_prefix=resource_name_prefix,
    environment=environment
)

consumer_stack = ConsumerStack(app, stackPrefix(resource_name_prefix, "ConsumerStack"), 
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    # secret_name=secret_name,
    vpc_id=vpc_id,
    retention=retention,
    resource_prefix=resource_name_prefix,
    domain=domain
)

portal_stack = PortalStack(app, stackPrefix(resource_name_prefix, "PortalStack"),
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    vpc_id=vpc_id,
    resource_prefix=resource_name_prefix,
    environment=environment,
    oidc_audience=oidc_audience,
    oidc_jwks_uri=oidc_jwks_uri,
    oidc_issuer=oidc_issuer,
    authorized_users=authorized_users,
    auth_type=auth_type,
    secret_name=secret_name,
    auto_reply_from_email=auto_reply_from_email,
    kms_cmk_arn=kms_cmk_arn,
    api_domain_name=api_domain_name,
    api_domain_cert_arn=api_domain_cert_arn
)

# Add dependency between the stacks
consumer_stack.add_dependency(s3_stack)
portal_stack.add_dependency(consumer_stack)
app.synth()