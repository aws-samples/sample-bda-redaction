import boto3
import json
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

logger = Logger(
    log_record_order=["message", "operation", "service", "namespace"],
    log_uncaught_exceptions=True,
    serialize_stacktrace=False,
    level="DEBUG" if os.environ['ENVIRONMENT'] in ['local', 'development'] else "WARNING"
)
logger.append_keys(namespace="PII-Redaction-RulesProcessing")

dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
s3_client = boto3.client('s3', region_name=os.environ['AWS_REGION'])
messagesTbl = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])

def process_rules(rule: dict):
    criteria = json.loads(rule['Criteria'])
    logger.info(criteria)
    filters = None
    for criterion in criteria:
        if criterion['fieldCondition'] == "equals":
            if filters is None:
                filters = boto3.dynamodb.conditions.Attr(criterion['fieldName']).eq(criterion['fieldValue'])
            else:
                filters = filters & boto3.dynamodb.conditions.Attr(criterion['fieldName']).eq(criterion['fieldValue'])
        elif criterion['fieldCondition'] == "contains" and criterion['fieldName'] != 'RedactedBody':
            if filters is None:
                filters = boto3.dynamodb.conditions.Attr(criterion['fieldName']).contains(criterion['fieldValue'])
            else:
                filters = filters & boto3.dynamodb.conditions.Attr(criterion['fieldName']).contains(criterion['fieldValue'])
        elif criterion['fieldCondition'] == 'between':
            date_range = criterion['fieldValue'].split('-')
            start_date = f"{date_range[0]}-{date_range[1]}-{date_range[2]}"
            end_date = f"{date_range[3]}-{date_range[4]}-{date_range[5]}"
            if filters is None:
                filters = boto3.dynamodb.conditions.Attr(criterion['fieldName']).between(start_date, end_date)
            else:
                filters = filters & boto3.dynamodb.conditions.Attr(criterion['fieldName']).between(start_date, end_date)
        # else:
        #     logger.error(criterion)
        #     raise ValueError(f"Unsupported field condition: {criterion['fieldCondition']}")
    
    if(filters is None):
        messages = messagesTbl.query(
            IndexName='EmailIndexBodyStatus',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('BodyStatus').eq('Processed')
        )
    else:
        messages = messagesTbl.query(
            IndexName='EmailIndexBodyStatus',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('BodyStatus').eq('Processed'),
            FilterExpression=filters
        )
    logger.info(f"Number of messages found: {len(messages['Items'])}")
    
    # Scan text in email body
    messagesWithBody = []
    for criterion in criteria:
        if criterion['fieldName'] == 'RedactedBody':
            for message in messages['Items']:
                email_body = s3_client.get_object(Bucket=message['ProcessedBucketName'], Key=message['ProcessedFilePath'] + '/body/email_body.txt')
                text = email_body['Body'].read().decode('utf-8')
                if criterion['fieldValue'] in text:
                    messagesWithBody.append(message)

    if len(messagesWithBody):
        logger.info(f"Number of messages with body: {len(messagesWithBody)}")
        messages['Items'] = messagesWithBody
    
    # Message has attachments check
    messagesWithAttachments = []
    for criterion in criteria:
        if criterion['fieldName'] == 'has_attachments':
            for message in messages['Items']:
                attachments = s3_client.list_objects_v2(Bucket=message['ProcessedBucketName'], Prefix='redacted')
                fileObjects = [file for file in attachments['Contents'] if int(file['Size']) > 0 and file['Key'].startswith(message['ProcessedFilePath'] + '/attachments')]
                if fileObjects:
                    messagesWithAttachments.append(message)

    if len(messagesWithAttachments):
        logger.info(f"Number of messages with attachments: {len(messagesWithAttachments)}")
        messages['Items'] = messagesWithAttachments
    
    messages_updated = 0
    for message in messages['Items']:
        updated = messagesTbl.update_item(
            Key={'CaseID': message['CaseID']},
            UpdateExpression='SET FolderID = :folder_id',
            ExpressionAttributeValues={':folder_id': rule['FolderID']},
            ReturnValues="UPDATED_NEW"
        )
        messages_updated += 1
        logger.info(updated)
    logger.info(f"Email filtering rules processing completed for rule '{rule['Description']}'")
    logger.info(f"Number of messages updated for '{rule['Description']}': {messages_updated}")

@logger.inject_lambda_context(log_event=True)
def handler(event: dict, context: LambdaContext) -> dict:
    try:
        rulesTbl = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
        if 'rule_id' in event:
            rule = rulesTbl.get_item(Key={'ID': event['rule_id']})
            logger.info(rule)
            process_rules(rule['Item'])
        else:
            rules = rulesTbl.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('Enabled').eq(True)
            )
            logger.info(rules)
            for rule in rules['Items']:
                process_rules(rule)

        print('Completed email rule filtering processing')
    except Exception as e:
        logger.exception(e)
        print('Error processing email filtering rules. Check logs!')