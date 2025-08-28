import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import cast
from aws_cdk import (
    Aws,
    CfnOutput,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    TimeZone,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    aws_scheduler_alpha as scheduler,
    aws_scheduler_targets_alpha as targets,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_certificatemanager as acm,
    custom_resources as cr
)
from constructs import Construct
from cdk_nag import NagSuppressions
from pii_redaction.helpers.index import stackPrefix
from pii_redaction.libs.lambda_integration_no_permission import LambdaIntegrationNoPermission

class PortalStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        vpc_id: str, 
        resource_prefix: str,
        environment: str,
        secret_name: str,
        auto_reply_from_email: str,
        api_domain_name: str,
        api_domain_cert_arn: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import values from other stacks
        email_table_name = Fn.import_value("EmailInventoryTableName")
        email_table_arn = Fn.import_value("EmailInventoryTableArn")
        raw_bucket = Fn.import_value("RawBucket")
        redacted_bucket_name = Fn.import_value("RedactedBucket")
        security_group_id = Fn.import_value("SecurityGroupID")
        s3_access_logs_bucket_name = Fn.import_value("AccessLogsBucket")
        
        # Reference existing access logs bucket
        access_logs_bucket = s3.Bucket.from_bucket_name(self, 'ImportedS3AccessLogsBucket', s3_access_logs_bucket_name)
        
        # S3 bucket that contains the static HTML/CSS/JS files for the portal
        private_hosting_bucket = s3.Bucket(self, 'PrivateWebHostingAssets',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix="private-web-hosting-assets/"
        )

        access_logs_bucket.add_to_resource_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject"],
            resources=[
                private_hosting_bucket.bucket_arn,
                f"{private_hosting_bucket.bucket_arn}/*"
            ],
            principals=[iam.AccountPrincipal("logging.s3.amazonaws.com")]
        ))

        # Reference existing DynamoDB table for email messages
        messages_tbl = dynamodb.TableV2.from_table_name(self, 'MessagesTable', email_table_name)

        # Create new DynamoDB table for folders
        folders_tbl = dynamodb.TableV2(self, 'FoldersTable', 
            table_name=stackPrefix(resource_prefix, "FoldersTable"),
            table_class=dynamodb.TableClass.STANDARD,
            partition_key=dynamodb.Attribute(name='ID', type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=True)
        )
        
        # Create new DynamoDB table for email rules
        rules_tbl = dynamodb.TableV2(self, 'ProcessingRulesTable', 
            table_name=stackPrefix(resource_prefix, "ProcessingRulesTable"),
            table_class=dynamodb.TableClass.STANDARD,
            partition_key=dynamodb.Attribute(name='ID', type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=True)
        )

        # Add GSI to easily query rules by assigned FolderID
        rules_tbl.add_global_secondary_index(
            index_name="RulesIndexFolderID",
            partition_key=dynamodb.Attribute(
                name="FolderID",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Create new DynamoDB table for users
        users_tbl = dynamodb.TableV2(self, 'UsersTable', 
            table_name=stackPrefix(resource_prefix, "UsersTable"),
            table_class=dynamodb.TableClass.STANDARD,
            partition_key=dynamodb.Attribute(name='ID', type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=True)
        )

        # Initialize folders table with default folder
        cr.AwsCustomResource(self, "InitFoldersTable",
            on_create=cr.AwsSdkCall(
                action="putItem",
                service="DynamoDB",
                parameters={
                    "TableName": folders_tbl.table_name,
                    "Item": {
                        "ID": {"S": "general_inbox"},
                        "Name": {"S": "General Inbox"},
                        "Description": {"S": "Default folder for all new messages."},
                        "Creator": {"S": "System - AWS CDK"},
                        "CreatedAt": {"S": datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S")}
                    }
                },
                physical_resource_id=cr.PhysicalResourceId.of("initFoldersTable")
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=[folders_tbl.table_arn]
            ),
            removal_policy=RemovalPolicy.RETAIN,
            timeout=Duration.minutes(1),
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        redacted_bucket = s3.Bucket.from_bucket_name(self, 'RedactedAttachmentsBucket', redacted_bucket_name)

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)
        security_group = ec2.SecurityGroup.from_security_group_id(self, "SecurityGroup", security_group_id)

        # Lambda Powertools layer
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            id='lambda-powertools',
            layer_version_arn=f"arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86:1",
        )

        # Lambda layer from the provided ZIP file location for additional PyPI packages
        packages_layer = lambda_.LayerVersion(
            self, 
            "piiRedactionPyPackagesLambdaLayer",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda/lambda-layer/pypackages_lambda_layer.zip')),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12]
        )

        # Lambda function for processing rules and categorizing messages in folders
        rules_processing_lambda = lambda_.Function(self, 'RulesProcessingHandler',
            function_name=stackPrefix(resource_prefix, "RulesProcessingHandler"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda')),
            handler='rules_processing.handler',
            environment={
                'MESSAGES_TABLE_NAME': email_table_name,
                'RULES_TABLE_NAME': rules_tbl.table_name,
                'ENVIRONMENT': environment
            },
            layers=[powertools_layer],
            memory_size=512,
            timeout=Duration.seconds(30),
            logging_format=lambda_.LoggingFormat.TEXT,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[security_group],
            log_group=logs.LogGroup(self, 'RulesProcessingHandlerLogGroup', 
                log_group_name=stackPrefix(resource_prefix, "RulesProcessingHandlerLogGroup"),
                removal_policy=RemovalPolicy.DESTROY
            ),
            tracing=lambda_.Tracing.ACTIVE
        )

        rules_processing_handler_role = rules_processing_lambda.role
        redacted_bucket.grant_read(rules_processing_handler_role)
        rules_tbl.grant_read_data(rules_processing_lambda)
        messages_tbl.grant_read_data(rules_processing_lambda)
        messages_tbl.grant_write_data(rules_processing_lambda)

        rules_processing_handler_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:GetItem",
                "dynamodb:BatchGetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:DescribeTable"
            ],
            resources=[
                f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{messages_tbl.table_name}/index/*",
                f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{rules_tbl.table_name}/index/*",
                f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{folders_tbl.table_name}/index/*"
            ]
        ))

        # Lambda function that handles all API requests initiated from the portal
        portal_lambda_handler = lambda_.Function(self, 'PortalLambdaHandler',
            function_name=stackPrefix(resource_prefix, "PortalLambdaHandler"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda')),
            handler='portal_api.handler',
            environment={
                'MESSAGES_TABLE_NAME': email_table_name,
                'FOLDERS_TABLE_NAME': folders_tbl.table_name,
                'RULES_TABLE_NAME': rules_tbl.table_name,
                'RULES_PROCESSING_LAMBDA_ARN': rules_processing_lambda.function_arn,
                'ENVIRONMENT': environment
            },
            layers=[powertools_layer, packages_layer],
            memory_size=512,
            timeout=Duration.seconds(30),
            logging_format=lambda_.LoggingFormat.TEXT,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[security_group],
            log_group=logs.LogGroup(self, 'PortalLambdaHandlerLogGroup', 
                log_group_name=stackPrefix(resource_prefix, "PortalLambdaHandlerLogGroup"),
                removal_policy=RemovalPolicy.DESTROY
            ),
            tracing=lambda_.Tracing.ACTIVE
        )

        # Create a email forwarding Lambda function
        if auto_reply_from_email != "":
            # Create an IAM role for the Lambda function
            email_forwarding_lambda_role = iam.Role(
                self, 
                "piiRedactionForwardingLambdaRole",
                role_name=stackPrefix(resource_prefix, "piiRedactionForwardingLambdaRole"),
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ]
            )

            email_forwarding_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["ec2:DescribeInstances",
                            "ec2:CreateNetworkInterface",
                            "ec2:AttachNetworkInterface",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DeleteNetworkInterface"],
                    resources=["*"],
                    effect=iam.Effect.ALLOW
                )
            )

            # Add inline policies for S3 PutObject, ListBucket, and Comprehend DetectPiiEntities/RedactPiiEntities
            email_forwarding_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject", 
                        "s3:ListBucket",
                        "s3:PutBucketNotification"
                    ],
                    resources=[
                        f"arn:aws:s3:::{raw_bucket}",
                        f"arn:aws:s3:::{raw_bucket}/*",
                        f"arn:aws:s3:::{redacted_bucket}",
                        f"arn:aws:s3:::{redacted_bucket}/*"
                    ],
                    effect=iam.Effect.ALLOW
                )
            )

            email_forwarding_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{secret_name}*"],
                    effect=iam.Effect.ALLOW
                )
            )

            email_forwarding_lambda_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["dynamodb:UpdateItem","dynamodb:GetItem","dynamodb:PutItem"],
                    resources=[email_table_arn],
                    effect=iam.Effect.ALLOW
                )
            )
            
            email_forwarding_lambda = lambda_.Function(
                self, 
                "piiRedactionemailForwardingLambda",
                function_name=stackPrefix(resource_prefix, "piiRedactionemailForwardingLambda"),
                runtime=lambda_.Runtime.PYTHON_3_12,
                handler="emailForwarding.lambda_handler",
                code=lambda_.Code.from_asset("./pii_redaction/lambda/emailForwarding"),
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                security_groups=[security_group],
                environment={
                    "INVENTORY_TABLE_NAME": email_table_name,
                    "SECRET_NAME": secret_name,
                    "AUTO_REPLY_FROM_EMAIL": auto_reply_from_email
                },
                role=email_forwarding_lambda_role,
                timeout=Duration.seconds(900),
                log_group=logs.LogGroup(self, 'piiRedactionemailForwardingLambdaLogGroup'),
            )

        # Lambda function that is the authorizer for the API Gateway
        lambda_auth_security_group = ec2.SecurityGroup(self, "LambdaAuthSecurityGroup",
            security_group_name=stackPrefix(resource_prefix, "LambdaAuthSecurityGroup"),
            vpc=vpc,
            description="Security group for Lambda Authorizer",
            allow_all_outbound=False
        )

        lambda_auth_security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS"
        )

        # Secret that contains the Basic Auth credentials to access the portal
        secret = secretsmanager.Secret(self, 'PiiRedactionPortalAuthSecret',
            secret_name=stackPrefix(resource_prefix, "PiiRedactionPortalAuthSecret"),
            description='Credentials for PII Redaction using Amazon Bedrock portal application',
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({'username': 'pii_redaction_email_admin'}),
                generate_string_key='password',
                exclude_punctuation=True,
                include_space=False
            )
        )
        
        # Basic Auth
        lambda_auth_handler = lambda_.Function(self, 'LambdaAuthHandler',
            function_name=stackPrefix(resource_prefix, "LambdaAuthHandler"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda')),
            handler='basic_auth_authorizer.handler',
            environment={
                'ENVIRONMENT': 'development',
                'SECRET_ARN': secret.secret_full_arn
            },
            layers=[powertools_layer],
            memory_size=512,
            timeout=Duration.seconds(60),
            logging_format=lambda_.LoggingFormat.TEXT,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[lambda_auth_security_group],
            log_group=logs.LogGroup(self, 'LambdaAuthHandlerLogGroup', 
                log_group_name=stackPrefix(resource_prefix, "LambdaAuthHandlerLogGroup"),
                removal_policy=RemovalPolicy.DESTROY
            ),
            tracing=lambda_.Tracing.ACTIVE
        )
        lambda_auth_handler_role = lambda_auth_handler.role
        secret.grant_read(lambda_auth_handler_role)

        portal_api_handler_role = portal_lambda_handler.role
        redacted_bucket.grant_read(portal_api_handler_role)
        portal_api_handler_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        portal_api_handler_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
        )

        if auto_reply_from_email != "":
            portal_api_handler_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['lambda:InvokeFunction'],
                resources=[
                    email_forwarding_lambda.function_arn,
                    f"{email_forwarding_lambda.function_arn}:*",
                ]
            ))

        portal_api_handler_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:GetItem",
                "dynamodb:BatchGetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:DescribeTable"
            ],
            resources=[
                f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{messages_tbl.table_name}/index/*",
                f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{rules_tbl.table_name}/index/*",
                f"arn:aws:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{folders_tbl.table_name}/index/*"
            ]
        ))

        rules_processing_lambda.grant_invoke(portal_api_handler_role)
        messages_tbl.grant_read_write_data(portal_api_handler_role)
        folders_tbl.grant_read_write_data(portal_api_handler_role)
        rules_tbl.grant_read_write_data(portal_api_handler_role)

        api_gw_s3_role = iam.Role(self, 'ApiGwS3Role',
            role_name=stackPrefix(resource_prefix, "ApiGwS3Role"),
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com'),
            description='Role for API Gateway to access S3 assets'
        )
        private_hosting_bucket.grant_read(api_gw_s3_role)

        # Lambda token authorizer
        authorizer = apigateway.TokenAuthorizer(self, 'LambdaAuthorizer',
            authorizer_name=stackPrefix(resource_prefix, "LambdaAuthorizer"),
            handler=lambda_auth_handler,
            identity_source=apigateway.IdentitySource.header('Authorization'),
            results_cache_ttl=Duration.seconds(300),
        )

        apigw_log_group = logs.LogGroup(self, "ApiGatewayAccessLogs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        api = apigateway.RestApi(self, 'PiiRedactionInfraAPI',
            rest_api_name=stackPrefix(resource_prefix, "PiiRedactionInfraAPI"),
            description='API for PII Redaction using Amazon Bedrock portal',
            deploy=True,
            deploy_options=apigateway.StageOptions(
                stage_name='portal',
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(apigw_log_group),
                tracing_enabled=True,
                throttling_rate_limit=1000,
                throttling_burst_limit=5000
            ),
            default_method_options=apigateway.MethodOptions(
                authorizer=authorizer,
                method_responses=[
                    apigateway.MethodResponse(
                        status_code='200',
                        response_models={
                            'application/json': apigateway.Model.EMPTY_MODEL,
                        }
                    )
                ]
            ),
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['lambda:InvokeFunction'],
                        resources=[
                            lambda_auth_handler.function_arn,
                            f"{lambda_auth_handler.function_arn}:*",
                            portal_lambda_handler.function_arn,
                            f"{portal_lambda_handler.function_arn}:*"
                        ],
                        principals=[iam.ServicePrincipal('apigateway.amazonaws.com')],
                    )
                ]
            )
        )

        private_hosting_bucket.add_to_resource_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[
                private_hosting_bucket.bucket_arn,
                f"{private_hosting_bucket.bucket_arn}/*"
            ],
            principals=[iam.ServicePrincipal("apigateway.amazonaws.com")]
        ))

        portal_lambda_handler.add_permission('ApiGatewayInvokeLambdaPermission',
            principal=iam.ServicePrincipal('apigateway.amazonaws.com'),
            action='lambda:InvokeFunction',
            source_arn=f"arn:aws:execute-api:{Aws.REGION}:{Aws.ACCOUNT_ID}:{api.rest_api_id}/*/*/*"
        )

        if len(api_domain_name) > 0:
            # Set up custom domain for API Gateway
            api_domain = apigateway.DomainName(self, 'ApiDomain',
                domain_name=api_domain_name,
                certificate=acm.Certificate.from_certificate_arn(self, 'Certificate', certificate_arn=api_domain_cert_arn),
                security_policy=apigateway.SecurityPolicy.TLS_1_2,
                mapping=api,
                endpoint_type=apigateway.EndpointType.REGIONAL
            )

            api_domain.apply_removal_policy(RemovalPolicy.DESTROY)

        # API Gateway gateway response that initiates Basic Auth request
        apigateway.GatewayResponse(self, 'GatewayResponse',
            rest_api=api,
            type=apigateway.ResponseType.UNAUTHORIZED,
            response_headers={
                'method.response.header.WWW-Authenticate': "'Basic'"
            },
            status_code='401',
            templates={
                'application/json': "{ 'message': $context.error.messageString }"
            }
        )

        # Integration for UI-related endpoints that service static assets
        static_hosting_integration = apigateway.AwsIntegration(
            service='s3',
            integration_http_method='GET',
            path=f"{private_hosting_bucket.bucket_name}/index.html",
            options=apigateway.IntegrationOptions(
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
                credentials_role=api_gw_s3_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code='200',
                        response_parameters={
                            'method.response.header.Content-Type': 'integration.response.header.Content-Type'
                        }
                    )
                ]
            )
        )

        static_hosting_method_responses = [
            apigateway.MethodResponse(
                status_code='200',
                response_parameters={
                    'method.response.header.Content-Type': True,
                }
            )
        ]

        mock_integration = apigateway.MockIntegration(
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_templates={
                        "application/json": '{"statusCode": 200, "message": "Success"}'
                    }
                )
            ],
            passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
            request_templates={
                "application/json": '{"statusCode": 200}'
            }
        )

        # Add method response for the mock integration
        method_responses = [
            apigateway.MethodResponse(
                status_code="200",
                response_models={
                    "application/json": apigateway.Model.EMPTY_MODEL
                }
            )
        ]

        # API Gateway resources
        api.root.add_method(
            'GET', 
            integration=static_hosting_integration,
            method_responses=static_hosting_method_responses,
        )
        api.root.add_method(
            'POST',
            method_responses=method_responses,
            integration=mock_integration
        )
        api.root.add_resource("{proxy+}").add_method(
            'GET', 
            integration=static_hosting_integration,
            method_responses=static_hosting_method_responses
        )
        assetsResource = api.root.add_resource('assets')
        assetsResource.add_resource('{asset}').add_method(
            'GET',
            integration=apigateway.AwsIntegration(
                service='s3',
                integration_http_method='GET',
                path=private_hosting_bucket.bucket_name + '/assets/{asset}',
                options=apigateway.IntegrationOptions(
                    passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
                    credentials_role=api_gw_s3_role,
                    request_parameters={
                        'integration.request.path.asset': 'method.request.path.asset',
                        'integration.request.header.x-ocloud-apigateway': "'private'"
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(
                            status_code='200',
                            response_parameters={
                                'method.response.header.Content-Type': 'integration.response.header.Content-Type'
                            }
                        )
                    ]
                ),
            ),
            method_responses=static_hosting_method_responses,
            request_parameters={
                'method.request.path.asset': True
            }
        )

        apiResources = api.root.add_resource("api", 
            default_integration=LambdaIntegrationNoPermission(portal_lambda_handler), 
            default_method_options=apigateway.MethodOptions(
                authorizer=None,
                authorization_type=None
            )
        )
        messages = apiResources.add_resource('messages')
        messages.add_method('GET',  operation_name='getMessages')
        messages.add_resource('export', default_method_options=apigateway.MethodOptions(
            request_parameters={
                'method.request.header.Accept': True,
                'method.request.header.Content-Type': True,
            },
        )).add_method('POST', operation_name='exportMessages', method_responses=[apigateway.MethodResponse(
            status_code='200',
            response_models={
                'application/json': apigateway.Model.EMPTY_MODEL,
                'text/csv': apigateway.Model.EMPTY_MODEL,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': apigateway.Model.EMPTY_MODEL,
            },
            response_parameters={
                'method.response.header.Content-Disposition': True,
                'method.response.header.Content-Type': True,
            }
        )])

        singleMessage = messages.add_resource('{identifier}', default_method_options=apigateway.MethodOptions(
                request_parameters={
                    'method.request.path.identifier': True
                }
            )
        )
        singleMessage.add_method('GET', operation_name='getMessage')
        singleMessage.add_resource('forward').add_method('POST', operation_name='forwardMessage')

        folders = apiResources.add_resource('folders')
        folders.add_method('GET', operation_name='getFolders')
        folders.add_method('POST', operation_name='createFolder')
        
        singleFolder = folders.add_resource("{folder_id}", default_method_options=apigateway.MethodOptions(
                request_parameters={
                    'method.request.path.folder_id': True
                }
            )
        )
        singleFolder.add_method('GET', operation_name='getFolder')
        singleFolder.add_method('DELETE', operation_name='deleteFolder')
        singleFolder.add_resource('messages').add_method('GET', operation_name='getFolderMessages')

        rules = apiResources.add_resource('rules')
        rules.add_method('GET', operation_name='getRules')
        rules.add_method('POST', operation_name='createRule')

        singleRule = rules.add_resource('{rule_id}', default_method_options=apigateway.MethodOptions(
                request_parameters={
                    'method.request.path.rule_id': True
                }
            )
        )
        singleRule.add_method('GET', operation_name='getRule')
        singleRule.add_method('DELETE', operation_name='deleteRule')
        singleRule.add_method('PATCH', operation_name='patchRule')

        # EventBridge scheduler to run email rules processing lambda every day at 2:00 AM EST
        scheduler.Schedule(self, 'RulesProcessingSchedule',
            schedule=scheduler.ScheduleExpression.cron(
                minute='0',
                hour='2',
                day='*',
                month='*',
                year='*',
                time_zone=TimeZone.AMERICA_NEW_YORK
            ),
            target=targets.LambdaInvoke(rules_processing_lambda),
            description='Runs daily at 2:00 AM EST to process rules',
            enabled=True,
            schedule_name=stackPrefix(resource_prefix, "RulesProcessingSchedule"),
        )

        self.private_web_hosting_s3_bucket = CfnOutput(self, "S3PrivateWebHostingBucket", value=private_hosting_bucket.bucket_name, export_name="S3PrivateWebHostingBucket")

        # if len(api_domain_name) > 0:
        #     self.apigw_domain_name_alias = CfnOutput(self, "ApiGwDomainNameAliasOutput", value=api_domain.domain_name_alias_domain_name, export_name="ApiGwDomainNameAlias")