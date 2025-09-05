from aws_cdk import (
    App,
    Stack,
    Fn,
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_ecr as ecr,
    aws_kms as kms,
    aws_logs as logs,
    aws_s3_notifications as s3n,
    aws_ses as ses,
    CfnOutput,
    aws_bedrock as bedrock,
    custom_resources as cr
)
import aws_cdk.aws_bedrock as bedrock 
import aws_cdk.aws_ecr_assets as ecr_assets
from cdk_nag import NagSuppressions, NagPackSuppression
from pii_redaction.helpers.index import stackPrefix
import os

class ConsumerStack(Stack):

    def __init__(
        self, 
        scope: App, 
        construct_id: str, 
        # secret_name: str,
        vpc_id: str, 
        retention: int,
        resource_prefix: str,
        domain: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the resource details from the S3Stack output
        raw_bucket_name = Fn.import_value("RawBucket")
        redacted_bucket_name = Fn.import_value("RedactedBucket")
        inventory_table_name = Fn.import_value("EmailInventoryTableName")
        lambda_role_arn = Fn.import_value("LambdaRole")
        ses_role_arn = Fn.import_value("SESRole")
        security_group_id = Fn.import_value("SecurityGroupID")
        # Create an IAM role from the imported Lambda role ARN
        lambda_role = iam.Role.from_role_arn(self, "LambdaRole", lambda_role_arn)
        # Get the VPC and create an instance of the security group from the imported ID
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)
        security_group = ec2.SecurityGroup.from_security_group_id(self, "SecurityGroup", security_group_id)
        # Get the KMS key from the alias ARN
        kms_key = kms.Key.from_key_arn(self, "KMSKey", f"arn:aws:kms:{self.region}:{self.account}:alias/aws/sns")
        #create project with custom settings for bedrock data automation
        cfn_bda = bedrock.CfnDataAutomationProject(self, "piiRedactionBedrockProject",
                                                   project_name=stackPrefix(resource_prefix, "piiBedrockDataAutomationProject"),
                                         standard_output_configuration = bedrock.CfnDataAutomationProject.StandardOutputConfigurationProperty(
                                             document=bedrock.CfnDataAutomationProject.DocumentStandardOutputConfigurationProperty(
                                                extraction=bedrock.CfnDataAutomationProject.DocumentStandardExtractionProperty(
                                                    bounding_box=bedrock.CfnDataAutomationProject.DocumentBoundingBoxProperty(
                                                                    state="ENABLED"
                                                                ),
                                                    granularity=bedrock.CfnDataAutomationProject.DocumentExtractionGranularityProperty(
                                                                    types=["PAGE", "ELEMENT","WORD"]
                                                                )
                                                    ),
                                                output_format=bedrock.CfnDataAutomationProject.DocumentOutputFormatProperty(
                                                    additional_file_format=bedrock.CfnDataAutomationProject.DocumentOutputAdditionalFileFormatProperty(
                                                          state="ENABLED"
                                                    ),
                                                    text_format=bedrock.CfnDataAutomationProject.DocumentOutputTextFormatProperty(
                                                        types=["PLAIN_TEXT"]
                                                    )
                                                )
                                            )
                                        )
                                    )
        #                                         {"Document": 
        #                                             {"Extraction": {"BoundingBox": {"State": "ENABLED"}, "Granularity": {"Types": ["PAGE", "ELEMENT", "WORD"]}},
        #                                              "OutputFormat": {"AdditionalFileFormat": {"State": "DISABLED"},"TextFormat": {"Types": ["PLAIN_TEXT"]}}}, 
        #                                          "Image": {"Extraction": {"BoundingBox": {"State": "ENABLED"}, "Category": {"State": "DISABLED"}}}})
        # bedrock.
        #create bedrock guardrail to mask PII entities supported by bedrock guardrail currently
        cfn_guardrail = bedrock.CfnGuardrail(self, "piiRedactionGuardrail",
                            blocked_input_messaging="Guardrail applied based on the input.",
                            blocked_outputs_messaging="Guardrail applied based on output.",
                            name=stackPrefix(resource_prefix, "piiRedactionGuardrail"),
                            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                            pii_entities_config=[
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="NAME",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="PHONE",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="EMAIL",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="ADDRESS",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="AGE",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="USERNAME",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="PASSWORD",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="DRIVER_ID",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="LICENSE_PLATE",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="VEHICLE_IDENTIFICATION_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="CREDIT_DEBIT_CARD_CVV",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="CREDIT_DEBIT_CARD_EXPIRY",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="CREDIT_DEBIT_CARD_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="PIN",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="INTERNATIONAL_BANK_ACCOUNT_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="SWIFT_CODE",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="IP_ADDRESS",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="MAC_ADDRESS",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="URL",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="AWS_ACCESS_KEY",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="AWS_SECRET_KEY",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="US_PASSPORT_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="US_SOCIAL_SECURITY_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="US_BANK_ACCOUNT_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="US_BANK_ROUTING_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="CA_HEALTH_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="CA_SOCIAL_INSURANCE_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="UK_NATIONAL_INSURANCE_NUMBER",
                                output_action="ANONYMIZE"
                            ),
                            bedrock.CfnGuardrail.PiiEntityConfigProperty(
                                action="ANONYMIZE",
                                type="UK_NATIONAL_HEALTH_SERVICE_NUMBER",
                                output_action="ANONYMIZE"
                            )],
                ))
        #create bedrock guardrail version
        cfn_guardrail_version = bedrock.CfnGuardrailVersion(self, "piiRedactionGuardrailVersion",
            guardrail_identifier = cfn_guardrail.attr_guardrail_id
        )
        #create sns topics success and failure with default encryption enabled
        success_topic = sns.Topic(
            self, 
            "piiRedactionSuccessTopic",
            #topic_name=stackPrefix(resource_prefix, "piiRedactionSuccessTopic"),
            master_key=kms_key
        )

        failure_topic = sns.Topic(
            self, 
            "piiRedactionFailureTopic",
            #topic_name=stackPrefix(resource_prefix, "piiRedactionFailureTopic"),
            master_key=kms_key
        )
        
        crm_topic = sns.Topic(
            self, 
            "piiRedactionCRMTopic",
            #topic_name=stackPrefix(resource_prefix, "piiRedactionCRMTopic"),
            master_key=kms_key
        )

        lambda_role.attach_inline_policy(
            iam.Policy(
                self, 
                "SNSPublishPolicy",
                statements=[
                    iam.PolicyStatement(
                        actions=["sns:Publish"],
                        resources=[success_topic.topic_arn, failure_topic.topic_arn, crm_topic.topic_arn],
                        effect=iam.Effect.ALLOW
                    )
                ]
            )
        )

        # Create a Lambda layer for email procesing lambda
        layer_email_processing = lambda_.LayerVersion(
            self, 
            "piiRedactionEmailProcessingLambdaLayer",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda/emailProcessing/lambda-layer/layer_content.zip')),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12]
        )
        # Create a Lambda layer for attachment procesing lambda
        layer_attachment_processing = lambda_.LayerVersion(
            self, 
            "piiRedactionAttachmentProcessingLambdaLayer",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), 'lambda/attachmentProcessing/lambda-layer/layer_content.zip')),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12]
        )

        # Create a email processing Lambda function
        emailProcessing_Lambda = lambda_.Function(
            self, 
            "piiRedactionemailProcessingLambda",
            #function_name=stackPrefix(resource_prefix, "piiRedactionemailProcessingLambda"),
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="emailExtractRedact.lambda_handler",
            code=lambda_.Code.from_asset("./pii_redaction/lambda/emailProcessing"),
            memory_size=4096,
            vpc=vpc,
            #vpc_subnets=ec2.SubnetSelection(subnets=supported_subnet_ids),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[security_group],
            layers=[layer_email_processing],
            environment={
                "RAW_BUCKET_NAME": raw_bucket_name,
                "REDACTED_BUCKET_NAME": redacted_bucket_name,
                "INVENTORY_TABLE_NAME": inventory_table_name,
                # "SECRET_NAME": secret_name,
                "SUCCESS_TOPIC_ARN": success_topic.topic_arn,
                "FAILURE_TOPIC_ARN": failure_topic.topic_arn,
                "CRM_TOPIC_ARN": crm_topic.topic_arn,
                "RETENTION": str(retention),
                "GUARDRAIL_ID": cfn_guardrail.attr_guardrail_id,
                "GUARDRAIL_VERSION": cfn_guardrail_version.attr_version
            },
            role=lambda_role,
            timeout=Duration.seconds(900),
            log_group=logs.LogGroup(self, 'piiRedactionemailProcessingLambdaLogGroup'
                    #,log_group_name=stackPrefix(resource_prefix, "piiRedactionemailProcessingLambdaLogGroup")
            ),
        )
        # Create a attachment processing Lambda function
        attachmentProcessing_Lambda = lambda_.Function(
            self, 
            "piiRedactionAttachmentProcessingLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="attachmentProcessing.lambda_handler",
            code=lambda_.Code.from_asset("./pii_redaction/lambda/attachmentProcessing"),
            memory_size=4096,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[security_group],
            layers=[layer_attachment_processing],
            environment={
               "REDACTED_BUCKET_NAME": redacted_bucket_name,
               "INVENTORY_TABLE_NAME": inventory_table_name,
               "FAILURE_TOPIC_ARN": failure_topic.topic_arn,
               "CRM_TOPIC_ARN": crm_topic.topic_arn,
               "HOME": "/tmp",
               "PROJECT_NAME": cfn_bda.project_name,
               "GUARDRAIL_ID": cfn_guardrail.attr_guardrail_id,
               "GUARDRAIL_VERSION": cfn_guardrail_version.attr_version
            },
            role=lambda_role,
            timeout=Duration.seconds(900),
            log_group=logs.LogGroup(self, 'piiRedactionAttachmentProcessingLambdaLogGroup'
            ),
        )
        #subscribe to success to sns topic
        success_topic.add_subscription(sns_subscriptions.LambdaSubscription(attachmentProcessing_Lambda))
        #Get the S3 bucket resource
        raw_bucket = s3.Bucket.from_bucket_name(self, "RawBucket", raw_bucket_name)
        # Grant the necessary permissions for S3 to invoke your Lambda function
        raw_bucket.grant_read(emailProcessing_Lambda)
        # Add S3 Event Source to trigger the Lambda function on PUT events
        raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT, 
            s3n.LambdaDestination(emailProcessing_Lambda),
            s3.NotificationKeyFilter(prefix="domain_emails/")
        )
        if domain != "":
            # Create SES Rule Set and Rule for Incoming Emails
            rule_set = ses.CfnReceiptRuleSet(self, "RuleSet", rule_set_name=stackPrefix(resource_prefix, "rule-set"))
            # Define the receipt rule
            receipt_rule = ses.CfnReceiptRule(
                self,
                "EmailReceiptRule",
                rule_set_name=rule_set.rule_set_name,
                rule={
                    "name": "emailProcessingRule",
                    "enabled": True,
                    "scan_enabled": True,
                    "recipients": [f"{domain}"],
                    "actions": [
                        # Store email in S3
                        {
                            "s3Action": {
                                "bucketName": raw_bucket_name,
                                "objectKeyPrefix": "domain_emails/",
                                "iam_role_arn": ses_role_arn
                            }
                        }
                    ]
                }
            )
            # Set dependency to ensure rule set is created before the rule
            receipt_rule.node.add_dependency(rule_set)
            # Step 3: Lambda function to activate the rule set
            activate_rule_set_lambda = lambda_.Function(
                self,
                "ActivateRuleSetLambda",
                runtime=lambda_.Runtime.PYTHON_3_12,
                handler="index.handler",
                code=lambda_.Code.from_inline(
                    """
    import boto3
    def handler(event, context):
        client = boto3.client('ses')
        rule_set_name = event['rule_set_name']
        # Set the rule set as active
        client.set_active_receipt_rule_set(RuleSetName=rule_set_name)

        return {"status": "Activated", "rule_set_name": rule_set_name}
                    """
                ),
                timeout=Duration.seconds(900),
            )
            # Trigger Lambda to activate the rule set
            custom_resource = cr.AwsCustomResource(
                self,
                "ActivateRuleSet",
                policy=cr.AwsCustomResourcePolicy.from_statements([
                    iam.PolicyStatement(
                        actions=["ses:SetActiveReceiptRuleSet"],
                        resources=["*"]
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                        resources=["arn:aws:logs:*:*:*"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["lambda:InvokeFunction"],
                        resources=[activate_rule_set_lambda.function_arn],
                    )
                ]),
                on_create=cr.AwsSdkCall(
                    action="invoke",
                    service="Lambda",
                    region=self.region,
                    parameters={
                        "FunctionName": activate_rule_set_lambda.function_name,
                        "InvocationType": "RequestResponse",
                        "Payload": "{\"rule_set_name\": \"" + rule_set.rule_set_name + "\"}"
                    },
                    physical_resource_id=cr.PhysicalResourceId.of("ActivateRuleSet"),
                )
            )

        # cdk-nag
        # NagSuppressions.add_resource_suppressions(
        #     lambda_role, 
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM5",
        #             "reason": "Suppress for email processing lambda IAM role to grant the necessary permissions for S3 to invoke the Lambda function",
        #             "appliesTo": [
        #                 "Action::s3:GetBucket*",
        #                 "Action::s3:GetObject*",
        #                 "Action::s3:List*",
        #                 "Resource::arn:aws:s3:::RawBucket/*"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions_by_path(
        #     self,
        #     path=f"/{self.stack_name}/ActivateRuleSet/CustomResourcePolicy/Resource",
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM5",
        #             "reason": "Suppress for necessary permissions to trigger Lambda to activate the rule set",
        #             "appliesTo": [
        #                 "Resource::*",
        #                 "Resource::arn:aws:logs:*:*:*"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions(
        #     activate_rule_set_lambda, 
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM4",
        #             "reason": "Lambda requires basic execution role",
        #             "appliesTo": [
        #                 "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions_by_path(
        #     self,
        #     path=f"/{self.stack_name}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/Role/Resource",
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM4",
        #             "reason": "Lambda requires basic execution role",
        #             "appliesTo": [
        #                 "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions_by_path(
        #     self,
        #     path=f"/{self.stack_name}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/Role/DefaultPolicy/Resource",
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM5",
        #             "reason": "Lambda function IAM role policy used for AWS CloudFormation handler for \"Custom::S3BucketNotifications\" resources",
        #             "appliesTo": [
        #                 "Resource::*"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )

        # NagSuppressions.add_resource_suppressions_by_path(
        #     self,
        #     path=f"/{self.stack_name}/AWS679f53fac002430cb0da5b7982bd2287/ServiceRole/Resource",
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM4",
        #             "reason": "Lambda requires basic execution role for ActivateRuleSet custom resource",
        #             "appliesTo": [
        #                 "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        #             ]
        #         }
        #     ],
        #     apply_to_children=True
        # )
