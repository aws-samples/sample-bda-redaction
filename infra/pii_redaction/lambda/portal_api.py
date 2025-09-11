import base64
import boto3
import csv
import json
import os
import jwt
import uuid

from http import HTTPStatus
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver, 
    CORSConfig,
    Response,
    content_types
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    InternalServerError,
    NotFoundError,
)
from botocore.exceptions import ClientError

logger = Logger(
    log_record_order=["message", "operation", "service", "namespace"],
    log_uncaught_exceptions=True,
    serialize_stacktrace=False,
    level="DEBUG" if os.environ['ENVIRONMENT'] in ['local', 'development'] else "INFO"
)
logger.append_keys(namespace="PII-Redaction")

dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
lambda_client = boto3.client('lambda', region_name=os.environ['AWS_REGION'])
s3_client = boto3.client('s3', region_name=os.environ['AWS_REGION'])
sts_client = boto3.client('sts', region_name=os.environ['AWS_REGION'])
logs_client = boto3.client('logs', region_name=os.environ['AWS_REGION'])

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="*"), debug=True if os.environ['ENVIRONMENT'] in ['local', 'development'] else False)

def get_email_body(message: dict) -> str:
    try:
        email_body = s3_client.get_object(Bucket=message['ProcessedBucketName'], Key=message['ProcessedFilePath'] + '/body/email_body.txt')
        logger.debug(email_body)
        return email_body['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Error retrieving email body: {e}")
        return message['EmailBody']

def record_user_activity(details: str):
    if app.current_event.headers.get('Authorization') and not app.current_event.headers.get('Authorization').startswith('Basic'):
        auth_token = app.current_event.headers.get('Authorization').split(' ')[1]
        decoded_token = jwt.decode(auth_token, algorithms=["RS256"], options={"verify_signature": True})
        logger.info(f"User {decoded_token['sub']} {details}.")

@app.exception_handler(Exception)
def handle_general_exception(ex: Exception):  # receives exception raised
    metadata = {
        "path": app.current_event.path, 
        "query_strings": app.current_event.query_string_parameters,
        "path_parameters": app.current_event.path_parameters,
    }
    logger.exception(f"Error: {ex}", extra=metadata)

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    
    if isinstance(ex, BadRequestError):
        status_code=HTTPStatus.BAD_REQUEST
    elif isinstance(ex, NotFoundError):
        status_code=HTTPStatus.NOT_FOUND

    return Response(
        status_code=status_code,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps({"message": "Internal server error"}),
    )

@app.get("/api/messages")
def list_messages():
    table = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    results = table.query(
        IndexName='EmailIndexBodyStatus',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('BodyStatus').eq('Processed')
    )
    logger.debug(results['Items'])

    for result in results['Items']:
        result['RedactedBody'] = get_email_body(result)

    record_user_activity('viewed all messages')

    return results['Items']
    
@app.get("/api/messages/<case_id>")
def get_message(case_id: int):
    table = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    result = table.get_item(Key={'CaseID': int(case_id)})

    if 'Item' not in result:
        raise NotFoundError(f"Message with case ID {case_id} not found")
    
    result['Item']['RedactedBody'] = get_email_body(result['Item'])
    logger.debug(result)
    folders_tbl = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
    folder = folders_tbl.get_item(Key={'ID': result['Item']['FolderID']})
    logger.debug(folder)
    result['Item']['folder'] = folder['Item']

    try:
        attachments = s3_client.list_objects_v2(Bucket=result['Item']['ProcessedBucketName'], Prefix='redacted')
        logger.debug(attachments)

        fileObjects = [file for file in attachments['Contents'] if int(file['Size']) > 0 and file['Key'].startswith(result['Item']['ProcessedFilePath'] + '/attachments')]

        if fileObjects:
            result['Item']['files'] = []
            for content in fileObjects:
                url = s3_client.generate_presigned_url('get_object', Params={'Bucket': result['Item']['ProcessedBucketName'],'Key': content['Key']})
                logger.debug(url)
                result['Item']['files'].append({
                    'name': content['Key'].split('/')[-1],
                    'url': url
                })
    except Exception as e:
        logger.error(f"Error retrieving attachments: {e}")

    logger.debug(result['Item'])
    record_user_activity(f"viewed message {case_id}")
    return result['Item']

@app.post("/api/messages/<case_id>/forward")
def forward_message(case_id: int):
    print("here in forwarding function")
    table = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    result = table.get_item(Key={'CaseID': int(case_id)})

    if 'Item' not in result:
        raise NotFoundError(f"Message with case ID {case_id} not found")
    logger.info("forwarding email logs")
    logger.debug(result)
    response = lambda_client.invoke(
        FunctionName=os.environ['FORWARD_EMAIL_LAMBDA_ARN'],
        InvocationType='RequestResponse',
        Payload=json.dumps({
            'case_id': case_id,
            'forwarding_email': app.current_event.json_body['emails']
        })
    )
    
    logger.info(response)
    record_user_activity(f"forwarded message {case_id}")
    return result['Item']

@app.post("/api/messages/export")
def export_messages():
    table = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    body = app.current_event.json_body
    logger.debug(body)
    int_case_ids = [int(case_id) for case_id in body['case_id']]
    results = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('CaseID').is_in(int_case_ids)
    )
    logger.debug(results)

    if results['Items']:
        with open('/tmp/messages.csv', 'w+', newline='') as csvfile:
            fieldnames = ['case_id', 'from', 'subject', 'body', 'dominant_language', 'date_sent']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in results['Items']:
                writer.writerow({
                    'case_id': item['CaseID'],
                    'from': item['FromAddress'],
                    'subject': item['EmailSubject'],
                    'body': get_email_body(item),
                    'dominant_language': item['DominantLanguage'],
                    'date_sent': datetime.fromisoformat(item['EmailReceiveTime']).strftime("%Y-%m-%d %H:%M:%S")
                })

        with open('/tmp/messages.csv', 'rb') as f:
            content = f.read()
            body = base64.b64encode(content).decode('utf-8')
        
        record_user_activity(f"exported messages")

        return {
            "statusCode": 200,
            "headers": {
                'Content-Type': 'text/csv',
            },
            "body": body,
            "isBase64Encoded": True
        }
    raise BadRequestError('No messages found')

@app.get("/api/folders")
def list_folders():
    table = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
    folders = table.scan()

    messages_tbl = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    for folder in folders['Items']:
        messages = messages_tbl.query(
            IndexName='EmailIndexFolderID',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('FolderID').eq(folder['ID']),
            FilterExpression=boto3.dynamodb.conditions.Attr('BodyStatus').eq('Processed')
        )
        folder['MessagesCount'] = len(messages['Items'])

    logger.debug(folders['Items'])
    record_user_activity(f"viewed all folders")
    return folders['Items']

@app.post("/api/folders")
def create_folder():
    table = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
    body = app.current_event.json_body
    body['ID'] = uuid.uuid4().hex
    body['CreatedAt'] = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S")
    table.put_item(Item=body)

    record_user_activity(f"created new folder {body['ID']}")

    return Response(
        status_code=HTTPStatus.CREATED,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(body),
    )

@app.get("/api/folders/<folder_id>")
def get_folder(folder_id: str):
    table = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
    result = table.get_item(Key={'ID': folder_id})
    logger.debug(result)

    if 'Item' not in result:
        raise NotFoundError(f"Folder with ID {folder_id} not found")

    logger.debug(result['Item'])
    return result['Item']

@app.get("/api/folders/<folder_id>/messages")
def list_folder_messages(folder_id: str):
    table = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
    folder = table.get_item(Key={'ID': folder_id})
    
    if 'Item' not in folder:
        raise NotFoundError(f"Folder with ID {folder_id} not found")
        
    messages_tbl = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    results = messages_tbl.query(
        IndexName='EmailIndexFolderID',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('FolderID').eq(folder_id),
        FilterExpression=boto3.dynamodb.conditions.Attr('BodyStatus').eq('Processed')
    )
    
    logger.debug(results['Items'])
    record_user_activity(f"viewed messages in folder {folder_id}")
    return results['Items']

@app.delete("/api/folders/<folder_id>")
def delete_folder(folder_id: str):
    table = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
    folder = table.delete_item(Key={'ID': folder_id})
    messages_tbl = dynamodb.Table(os.environ['MESSAGES_TABLE_NAME'])
    messages = messages_tbl.query(
        IndexName='EmailIndexFolderID',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('FolderID').eq(folder_id)
    )
    logger.debug(messages)

    # Reassign affected messages to the General Inbox
    updated_messages_count = 0
    for message in messages['Items']:
        messages_tbl.update_item(
            Key={'CaseID': message['CaseID']},
            UpdateExpression='SET FolderID = :folder_id',
            ExpressionAttributeValues={':folder_id': 'general_inbox'},
            ReturnValues="UPDATED_NEW"
        )
        updated_messages_count += 1
    logger.info(f"Messages reassigned to the general inbox: {updated_messages_count}")

    # Disable rules with the folder
    rules_tbl = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
    rules = rules_tbl.query(
        IndexName='RulesIndexFolderID',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('FolderID').eq(folder_id)
    )
    logger.debug(rules)
    for rule in rules['Items']:
        rules_tbl.update_item(
            Key={'ID': rule['ID']},
            UpdateExpression='SET Enabled = :enabled',
            ExpressionAttributeValues={':enabled': False},
            ReturnValues="UPDATED_NEW"
        )
        logger.info(f"Rule '{rule['Description']}' has been disabled because folder {folder['Attributes']['Name']} has been deleted")

    record_user_activity(f"deleted folder {folder_id}")

    return Response(
        status_code=HTTPStatus.NO_CONTENT,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps({
            'message': f"Folder {folder_id} deleted. Number of messages that were reassigned to the general inbox: {updated_messages_count}"
        }),
    )

@app.get("/api/rules")
def list_rules():
    table = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
    results = table.scan()
    logger.debug(results['Items'])

    if results['Items']:
        folder_ids = [item['FolderID'] for item in results['Items']]
        folders_tbl = dynamodb.Table(os.environ['FOLDERS_TABLE_NAME'])
        folders = folders_tbl.meta.client.batch_get_item(
            RequestItems={
                folders_tbl.name: {'Keys': [{'ID': folder_id} for folder_id in folder_ids]}
            }
        )
        folders = folders['Responses'][folders_tbl.name]
        logger.debug(folders)
    
        for rule in results['Items']:
            rule['FolderName'] = next((item['Name'] for item in folders if item['ID'] == rule['FolderID']), None)

    record_user_activity(f"viewed all rules")
    return results['Items']
    
@app.post("/api/rules")
def create_rule():
    table = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
    body = app.current_event.json_body
    rule_id = uuid.uuid4().hex
    table.put_item(Item={
        'ID': rule_id,
        'FolderID': body['folderId'],
        'Description': body['description'],
        'Criteria': json.dumps(body['criteria']),
        'Enabled': True,
        'Creator': '',
        'CreatedAt': datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S")
    })

    # Run lambda to process emails according to new rule criteria immediately
    response = lambda_client.invoke(
        FunctionName=os.environ['RULES_PROCESSING_LAMBDA_ARN'],
        InvocationType='RequestResponse',
        Payload=json.dumps({
            'rule_id': rule_id
        })
    )

    if response['StatusCode'] == 200:
        logger.info(response['Payload'].read())
    else:
        raise InternalServerError('Error invoking email rules filtering lambda')
    
    record_user_activity(f"created new rule {rule_id}")
    
    return Response(
        status_code=HTTPStatus.CREATED,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps({
            'message': 'New email filtering rule has been created'
        }),
    )

@app.patch("/api/rules/<rule_id>")
def update_rule(rule_id: str):
    table = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
    rule = app.current_event.json_body
    table.update_item(
        Key={'ID': rule_id},
        UpdateExpression='SET Enabled = :enabled',
        ExpressionAttributeValues={':enabled': rule['enabled']},
        ReturnValues="UPDATED_NEW"
    )
    status = 'enabled' if rule['enabled'] is True else 'disabled'
    record_user_activity(f"updated rule {rule_id}")
    return f"Rule status updated to {status}"
    
@app.get("/api/rules/<rule_id>")
def get_rule(rule_id: str):
    table = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
    result = table.get_item(Key={'ID': rule_id})

    if 'Item' not in result:
        raise NotFoundError(f"Rule with ID {rule_id} not found")
    
    logger.debug(result)
    return result['Item']

@app.delete("/api/rules/<rule_id>")
def delete_rule(rule_id: str):
    table = dynamodb.Table(os.environ['RULES_TABLE_NAME'])
    table.delete_item(Key={'ID': rule_id})

    record_user_activity(f"deleted rule {rule_id}")

    return Response(
        status_code=HTTPStatus.NO_CONTENT,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps({
            'message': f"Rule {rule_id} deleted"
        }),
    )

# @logger.inject_lambda_context(log_event=True)
# @event_source(data_class=APIGatewayProxyEvent)
def handler(event: dict, context: LambdaContext) -> dict:
    logger.debug('Received event: ' + json.dumps(event))
    return app.resolve(event, context)
