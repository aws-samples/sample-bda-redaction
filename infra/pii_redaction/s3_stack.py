import boto3
from aws_cdk import (
    App,
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_ec2 as ec2,
)
from cdk_nag import NagSuppressions
from pii_redaction.helpers.index import stackPrefix

class S3Stack(Stack):
    def __init__(
        self, 
        scope: App, 
        construct_id: str, 
        raw_bucket_name: str, 
        redacted_bucket_name: str, 
        table_name: str, 
        vpc_id: str, 
        # secret_name: str, 
        retention: int,
        resource_prefix: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ec2_boto3 = boto3.client('ec2')
        # Get the VPC ID from user input
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)
        response_dynamo_prefix = ec2_boto3.describe_managed_prefix_lists(
            Filters=[
                {
                    'Name': 'prefix-list-name',
                    'Values': [f'com.amazonaws.{self.region}.dynamodb']
                }
            ]
        )

        if not response_dynamo_prefix['PrefixLists']:
            raise ValueError(f"DynamoDB prefix list not found in region {self.region}")

        dynamodb_prefix_list_id = response_dynamo_prefix['PrefixLists'][0]['PrefixListId']
        #get s3 prefix list
        response_s3_prefix = ec2_boto3.describe_managed_prefix_lists(
            Filters=[
                {
                    'Name': 'prefix-list-name',
                    'Values': [f'com.amazonaws.{self.region}.s3']
                }
            ]
        )
        if not response_s3_prefix['PrefixLists']:
            raise ValueError(f"DynamoDB prefix list not found in region {self.region}")

        s3_prefix_list_id = response_s3_prefix['PrefixLists'][0]['PrefixListId']
        
        # Create a security group
        security_group = ec2.SecurityGroup(self, "LambdaSecurityGroup",
            security_group_name=stackPrefix(resource_prefix, "LambdaSecurityGroup"),
            vpc=vpc,
            description="Security group for Lambda function",
            allow_all_outbound=False
        )

        # Add rules to allow communication with S3, ECR, DynamoDB, Comprehend, and Textract
        security_group.add_egress_rule(
            peer=ec2.Peer.prefix_list(s3_prefix_list_id),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS access to AWS services"
        )
        security_group.add_egress_rule(
            peer=ec2.Peer.prefix_list(dynamodb_prefix_list_id),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS access to AWS services"
        )
        security_group.add_egress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS access to AWS services"
        )
        security_group.add_egress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(587),
            description="Allow HTTPS access to AWS services"
        )

        # S3 bucket for access logs
        s3_access_logs_bucket = s3.Bucket(
            self,
            "s3AccessLogsBucket",
            bucket_name=stackPrefix(resource_prefix, "s3-access-logs-bucket"),
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
            auto_delete_objects=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        raw_bucket = s3.Bucket(
            self,
            raw_bucket_name,
            bucket_name=stackPrefix(resource_prefix, raw_bucket_name),
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(retention)
                )
            ],
            enforce_ssl=True,
            server_access_logs_bucket=s3_access_logs_bucket,
            server_access_logs_prefix=f"{raw_bucket_name}-logs/",
        )
        
        # Create S3 bucket to save redacted email data
        redacted_bucket = s3.Bucket(
            self,
            redacted_bucket_name,
            bucket_name=stackPrefix(resource_prefix, redacted_bucket_name),
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(retention)
                )
            ],
            enforce_ssl=True,
            server_access_logs_bucket=s3_access_logs_bucket,
            server_access_logs_prefix=f"{redacted_bucket_name}-logs/",
        )
        
        # Create a DynamoDB table with Time to Live (TTL) enabled
        email_dynamodb_table = dynamodb.Table(
            self, 
            table_name,
            table_name=stackPrefix(resource_prefix, table_name),
            partition_key=dynamodb.Attribute(
                name="CaseID",
                type=dynamodb.AttributeType.NUMBER
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ExpirationTime",  # Attribute to store the expiration time
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # Set billing mode to pay-per-request
            # Enable point-in-time recovery
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=True)
        )

        email_dynamodb_table.add_global_secondary_index(
            index_name="EmailIndexBodyStatus",
            partition_key=dynamodb.Attribute(
                name="BodyStatus",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        email_dynamodb_table.add_global_secondary_index(
            index_name="EmailIndexFolderID",
            partition_key=dynamodb.Attribute(
                name="FolderID",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Create an IAM role for the Lambda function
        lambda_role = iam.Role(
            self, 
            "piiRedactionBackendLambdaRole",
            role_name=stackPrefix(resource_prefix, "piiRedactionBackendLambdaRole"),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add inline policies for S3 PutObject, ListBucket, and Comprehend DetectPiiEntities/RedactPiiEntities
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject","s3:PutObject", "s3:ListBucket","s3:PutBucketNotification"],
                resources=[
                    f"arn:aws:s3:::{raw_bucket.bucket_name}",
                    f"arn:aws:s3:::{raw_bucket.bucket_name}/*",
                    f"arn:aws:s3:::{redacted_bucket.bucket_name}",
                    f"arn:aws:s3:::{redacted_bucket.bucket_name}/*"
                ],
                effect=iam.Effect.ALLOW
            )
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["comprehend:DetectPiiEntities", 
                         "comprehend:RedactPiiEntities",
                         "comprehend:DetectDominantLanguage",
                         "comprehend:DetectEntities",
                         "textract:GetDocumentAnalysis",
                         "textract:GetDocumentTextDetection",
                         "textract:StartDocumentTextDetection",
                         "textract:StartDocumentAnalysis",
                         "ec2:DescribeInstances",
                         "ec2:CreateNetworkInterface",
                         "ec2:AttachNetworkInterface",
                         "ec2:DescribeNetworkInterfaces",
                         "autoscaling:CompleteLifecycleAction",
                         "ec2:DeleteNetworkInterface",
                         "bedrock:InvokeDataAutomationAsync",
                         "bedrock:GetDataAutomationStatus",
                         "bedrock:ApplyGuardrail",
                         "bedrock:ListDataAutomationProjects"],
                resources=["*"],
                effect=iam.Effect.ALLOW
            )
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:UpdateItem","dynamodb:GetItem","dynamodb:PutItem"],
                resources=[email_dynamodb_table.table_arn],
                effect=iam.Effect.ALLOW
            )
        )

        # Create an IAM role for the SES
        ses_role = iam.Role(
            self, 
            "piiRedactionSESServiceRole",
            role_name=stackPrefix(resource_prefix, "piiRedactionSESServiceRole"),
            assumed_by=iam.ServicePrincipal("ses.amazonaws.com")
        )

        # Add inline policies for S3 PutObject, ListBucket, and Comprehend DetectPiiEntities/RedactPiiEntities
        ses_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[
                    f"arn:aws:s3:::{raw_bucket.bucket_name}",
                    f"arn:aws:s3:::{raw_bucket.bucket_name}/*",
                ],
                effect=iam.Effect.ALLOW
            )
        )
        
        # Add bucket policy to allow specific permissions for the Lambda role
        raw_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
                resources=[raw_bucket.bucket_arn, f"{raw_bucket.bucket_arn}/*"],
                principals=[iam.ServicePrincipal("lambda.amazonaws.com")],
                conditions={"StringEquals": {"AWS:SourceArn": lambda_role.role_arn}}
            )
        )

        # raw_bucket.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.ALLOW,
        #         actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        #         resources=[raw_bucket.bucket_arn, f"{raw_bucket.bucket_arn}/*"],
        #         principals=[iam.ServicePrincipal("lambda.amazonaws.com")],
        #         conditions={"StringEquals": {"AWS:SourceArn": ses_role.role_arn}}
        #     )
        # )
        raw_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[f"{raw_bucket.bucket_arn}/*"],
                principals=[iam.ServicePrincipal("ses.amazonaws.com")],
                conditions={"StringEquals": {"AWS:SourceAccount": self.account}}
            )
        )
        
        # Add bucket policy to allow specific permissions for the Lambda role
        redacted_bucket.add_to_resource_policy(
           iam.PolicyStatement(
               effect=iam.Effect.ALLOW,
               actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
               resources=[redacted_bucket.bucket_arn, f"{redacted_bucket.bucket_arn}/*"],
               principals=[iam.ServicePrincipal("lambda.amazonaws.com")],
               conditions={"StringEquals": {"AWS:SourceArn": lambda_role.role_arn}}
           )
        )

        # Get the AZs supported by BDA VPC Endpoint
        endpoint_response_bda = ec2_boto3.describe_vpc_endpoint_services(
            ServiceNames=[f'com.amazonaws.{self.region}.bedrock-data-automation']
        )
        supported_azs_bda = endpoint_response_bda['ServiceDetails'][0]['AvailabilityZones']
        # Get the AZs supported by BDA Runtime VPC Endpoint
        endpoint_response_bda_runtime = ec2_boto3.describe_vpc_endpoint_services(
            ServiceNames=[f'com.amazonaws.{self.region}.bedrock-data-automation-runtime']
        )
        supported_azs_bda_rumtime = endpoint_response_bda_runtime['ServiceDetails'][0]['AvailabilityZones']
        # Get all subnets in the VPC
        subnet_response = ec2_boto3.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'state', 'Values': ['available']}
            ]
        )
        route_table_response = ec2_boto3.describe_route_tables(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ]
        )
        supported_subnet_ids_list_bda=[]
        all_subnets = []
        for subnet in subnet_response['Subnets']:
            if 'Tags' in subnet:
                for tag in subnet['Tags']:
                    if tag['Key'] == 'Name' and 'public' not in tag['Value'].lower():
                        all_subnets.append(subnet['SubnetId'])
            for supported_az in supported_azs_bda:
                if subnet['AvailabilityZone'] == supported_az and 'Tags' in subnet:
                    for tag in subnet['Tags']:
                        if tag['Key'] == 'Name' and 'public' not in tag['Value'].lower():
                            # Add the subnet ID to the list
                            supported_subnet_ids_list_bda.append(subnet['SubnetId'])
        supported_subnet_ids_list_bda_runtime=[]
        all_subnets = []
        for subnet in subnet_response['Subnets']:
            if 'Tags' in subnet:
                for tag in subnet['Tags']:
                    if tag['Key'] == 'Name' and 'public' not in tag['Value'].lower():
                        all_subnets.append(subnet['SubnetId'])
            for supported_az in supported_azs_bda_rumtime:
                if subnet['AvailabilityZone'] == supported_az and 'Tags' in subnet:
                    for tag in subnet['Tags']:
                        if tag['Key'] == 'Name' and 'public' not in tag['Value'].lower():
                            # Add the subnet ID to the list
                            supported_subnet_ids_list_bda_runtime.append(subnet['SubnetId'])
        #supported_subnet_ids_str= ','.join(supported_subnet_ids_list)
        # Get the AZs supported by smtp VPC Endpoint
        smtp_endpoint_response = ec2_boto3.describe_vpc_endpoint_services(
            ServiceNames=[f'com.amazonaws.{self.region}.email-smtp']
        )
        smtp_supported_azs = smtp_endpoint_response['ServiceDetails'][0]['AvailabilityZones']
        #smtp subnets
        smtp_supported_subnet_ids_list=[]
        for subnet in subnet_response['Subnets']:
            for supported_az in smtp_supported_azs:
                if subnet['AvailabilityZone'] == supported_az:
                    if 'Tags' in subnet:
                        for tag in subnet['Tags']:
                            if tag['Key'] == 'Name' and 'public' not in tag['Value'].lower():
                                # Add the subnet ID to the list
                                smtp_supported_subnet_ids_list.append(subnet['SubnetId'])
        #subnet_final_list = list(set(supported_subnet_ids_list) & set(smtp_supported_subnet_ids_list))
        # Convert the comma-separated string to a list of ISubnet objects
        supported_subnet_ids = [
            ec2.Subnet.from_subnet_id(self, f"SupportedSubnet{i}", subnet_id)
            for i, subnet_id in enumerate(supported_subnet_ids_list_bda)
        ]
        # Convert the comma-separated string to a list of ISubnet objects
        supported_subnet_ids_bda_runtime = [
            ec2.Subnet.from_subnet_id(self, f"BDASupportedSubnet{i}", subnet_id)
            for i, subnet_id in enumerate(supported_subnet_ids_list_bda_runtime)
        ]
        # Convert the comma-separated string to a list of ISubnet objects
        smtp_supported_subnet_ids = [
            ec2.Subnet.from_subnet_id(self, f"SmtpSupportedSubnet{i}", subnet_id)
            for i, subnet_id in enumerate(smtp_supported_subnet_ids_list)
        ]
        supported_route_table_ids = set([rt['RouteTableId'] for rt in route_table_response['RouteTables']])
        supported_route_tables=[]
        for id in supported_route_table_ids:
            supported_route_tables.append(id)
        s3_endpoint = ec2.CfnVPCEndpoint(
            self, 
            "piiRedactionS3GatewayEndpoint",
            vpc_id=vpc.vpc_id,
            service_name=f"com.amazonaws.{self.region}.s3",
            vpc_endpoint_type="Gateway",
            route_table_ids=supported_route_tables
        )
        dynamodb_endpoint = ec2.CfnVPCEndpoint(
            self, 
            "piiRedactionDynamoDBGatewayEndpoint",
            vpc_id=vpc.vpc_id,
            service_name=f"com.amazonaws.{self.region}.dynamodb",
            vpc_endpoint_type="Gateway",
            route_table_ids=supported_route_tables
        )

        lambda_endpoint = ec2.InterfaceVpcEndpoint(
            self, 
            "piiRedactionLambdaInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.lambda"),
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[security_group],
            private_dns_enabled=True
        )

        lambda_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountRootPrincipal()],
                actions=["lambda:InvokeFunction"],
                resources=["*"]
            )
        )

        ecr_endpoint = ec2.InterfaceVpcEndpoint(self,
            "piiRedactionECRInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            subnets=ec2.SubnetSelection(subnets=supported_subnet_ids),
            security_groups=[security_group],
            private_dns_enabled=True
        )

        ecr_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ecr:*"],
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        )

        bda_endpoint = ec2.InterfaceVpcEndpoint(self,
            "piiRedactionBDAInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock-data-automation"),
            subnets=ec2.SubnetSelection(subnets=supported_subnet_ids),
            security_groups=[security_group],
            private_dns_enabled=True
        )

        bda_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        )

        bedrock_runtime_endpoint = ec2.InterfaceVpcEndpoint(self,
            "piiRedactionBedrockRuntimeInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock-runtime"),
            subnets=ec2.SubnetSelection(subnets=supported_subnet_ids),
            security_groups=[security_group],
            private_dns_enabled=True
        )
        bedrock_runtime_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        )

        bda_runtime_endpoint = ec2.InterfaceVpcEndpoint(self,
            "piiRedactionBDARuntimeInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock-data-automation-runtime"),
            subnets=ec2.SubnetSelection(subnets=supported_subnet_ids_bda_runtime),
            security_groups=[security_group],
            private_dns_enabled=True
        )
        bda_runtime_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        )

        secrets_manager_endpoint = ec2.InterfaceVpcEndpoint(self,
            "piiRedactionSecretsManagerInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=ec2.SubnetSelection(subnets=supported_subnet_ids),
            security_groups=[security_group],
            private_dns_enabled=True
        )
        
        secrets_manager_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:*"],
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        )
        
        sns_endpoint = ec2.InterfaceVpcEndpoint(self,
            "piiRedactionSNSInterfaceEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SNS,
            subnets=ec2.SubnetSelection(subnets=supported_subnet_ids),
            security_groups=[security_group],
            private_dns_enabled=True
        )
        
        sns_endpoint.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:*"],
                resources=["*"],
                principals=[iam.AccountRootPrincipal()]
            )
        )
        
        # Create SES SMTP Endpoint
        ses_smtp_endpoint = ec2.InterfaceVpcEndpoint(
            self, 
            "piiRedactionSESSmtpEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.email-smtp", 587),  # Adjust region as needed
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnets=smtp_supported_subnet_ids),
            security_groups=[security_group]
        )

        # cdk-nag
        # NagSuppressions.add_resource_suppressions_by_path(
        #     self, 
        #     f"/{self.stack_name}/piiRedactionBackendLambdaRole/Resource",
        #     [
        #         {
        #             "id": "AwsSolutions-IAM4",
        #             "reason": "Lambda requires basic execution role and VPC access role for core functionality",
        #             "appliesTo": [
        #                 "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
        #                 "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions_by_path(
        #     self, 
        #     f"/{self.stack_name}/piiRedactionBackendLambdaRole/DefaultPolicy/Resource",
        #     [
        #         {
        #             "id": "AwsSolutions-IAM4",
        #             "reason": "Lambda requires basic execution role",
        #             "appliesTo": [
        #                 "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        #             ]
        #         },
        #         {
        #             "id": "AwsSolutions-IAM5",
        #             "reason": "Lambda IAM role permissions needed for email redaction Lambda",
        #             "appliesTo": [
        #                 "Resource::arn:aws:s3:::<attkanarawtestbucket0DAD3E78>/*",
        #                 "Resource::arn:aws:s3:::<attkanaredactedtestbucketB156356E>/*",
        #                 "Resource::*",
        #                 "Resource::arn:aws:secretsmanager:us-east-1:640446525652:secret:attSmtpCredentials*",
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions_by_path(
        #     self, 
        #     f"/{self.stack_name}/piiRedactionSESServiceRole/DefaultPolicy/Resource",
        #     [
        #         {
        #             "id": "AwsSolutions-IAM5",
        #             "reason": "Suppress AwsSolutions-IAM5 for Lambda execution role"
        #         }
        #     ]
        # )

        # Export the bucket names, table name, and repository URI as outputs
        self.raw_bucket_name_output = CfnOutput(self, "RawBucketNameOutput", value=raw_bucket.bucket_name, export_name="RawBucket")
        self.redacted_bucket_name_output = CfnOutput(self, "RedactedBucketNameOutput", value=redacted_bucket.bucket_name, export_name="RedactedBucket")
        self.inventory_table_name_output = CfnOutput(self, "EmailInventoryTableNameOutput", value=email_dynamodb_table.table_name, export_name="EmailInventoryTableName")
        self.inventory_table_arn_output = CfnOutput(self, "EmailInventoryTableARNOutput", value=email_dynamodb_table.table_arn, export_name="EmailInventoryTableArn")
        self.lambda_role_output = CfnOutput(self, "LambdaRoleOutput", value=lambda_role.role_arn, export_name="LambdaRole")
        self.ses_role_output = CfnOutput(self, "SESRoleOutput", value=ses_role.role_arn, export_name="SESRole")
        self.vpc_id_output = CfnOutput(self, "VPCIDOutput", value=vpc_id, export_name="VPCID")
        self.security_group_id_output = CfnOutput(self, "SecurityGroupIDOutput", value=security_group.security_group_id, export_name="SecurityGroupID")
        self.s3_access_logs_bucket_output = CfnOutput(self, "AccessLogsBucketOutput", value=s3_access_logs_bucket.bucket_name, export_name="AccessLogsBucket")
        #self.supported_subnets_output = CfnOutput(self, "SupportedSubnetsOutput", value=supported_subnet_ids_str, export_name="SupportedSubnets")