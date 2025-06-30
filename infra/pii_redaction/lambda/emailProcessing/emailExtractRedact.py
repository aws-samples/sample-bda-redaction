import boto3
import os
import pytz
from email import policy
from email.parser import BytesParser
from datetime import datetime, date
import json
import random
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

import time
import re

# Initialize AWS clients
s3 = boto3.client('s3')
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')
bedrock_runtime = boto3.client('bedrock-runtime')
my_session = boto3.session.Session()
my_region = my_session.region_name
eastern_tz = pytz.timezone('US/Eastern')
# Get values from environment variables
processed_bucket = os.environ['REDACTED_BUCKET_NAME']
table_name = os.environ['INVENTORY_TABLE_NAME']
# secret_name = os.environ['SECRET_NAME']
SNS_SUCCESS_TOPIC_ARN = os.environ['SUCCESS_TOPIC_ARN']
SNS_FAILURE_TOPIC_ARN = os.environ['FAILURE_TOPIC_ARN']
CRM_TOPIC_ARN = os.environ['CRM_TOPIC_ARN']
retention = int(os.environ['RETENTION'])
guardrail_id = os.environ['GUARDRAIL_ID']
guardrail_version = os.environ['GUARDRAIL_VERSION']
# DynamoDB table name
table = dynamodb.Table(table_name)
#set ttl for dynamodb records based on retention period mentioned in context file
ttl_value = int(time.time()) + (int(retention) * 24 * 60 * 60)


def extract_text_from_html(html_content):
    """
    Extracts and returns clean text content from HTML.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ')
def replace_text_in_html(original_html, redacted_text):

    """
    Replaces the original text content in the HTML with the redacted text while keeping the HTML structure intact.
    """
    soup = BeautifulSoup(original_html, 'html.parser')
    # Split redacted text by sentences or blocks to match with HTML tags
    redacted_chunks = redacted_text.split()
    # Iterate over text nodes in the HTML and replace them with the redacted text
    for element in soup.find_all(text=True):
        text_content = element.string.strip()
        if text_content:
            # Replace the text node with the redacted chunk
            element.replace_with(' '.join(redacted_chunks[:len(text_content.split())]))
            # Remove the processed chunk from the redacted_chunks list
            redacted_chunks = redacted_chunks[len(text_content.split()):]
    return str(soup)

    
def redact_pii(text_content, html_content, content_type):
    output_text=""
    content = [
        {
            "text": {
                "text": text_content
            }
        }
    ]
    response = bedrock_runtime.apply_guardrail(
                    guardrailIdentifier=guardrail_id,
                    guardrailVersion=guardrail_version,
                    source='OUTPUT',  # or 'INPUT' depending on your use case
                    content=content
                )
    for output in response['outputs']:
        output_text += output['text']
    if content_type == 'html':
        redacted_html = replace_text_in_html(html_content, output_text)
        return redacted_html
    else:
        return output_text
    

def insert_dynamodb(case_id,object_key,bucket_name,email_receive_time):
    item = {
            'CaseID': int(case_id),
            'RawFilePath': object_key,
            'RawBucketName': bucket_name,
            'EmailSubject': 'NA',
            'EmailBody': 'NA',
            'FromAddress': 'NA',
            'DominantLanguage': 'NA',
            'ProcessedBucketName': 'NA',
            "ProcessedFilePath": 'NA',
            'BodyStatus': 'Open',
            'FolderID': 'general_inbox',
            'EmailReceiveTime': email_receive_time,
            'BodyProcessedTime': email_receive_time,
            'AttachmentStatus': 'Open',
            'AttachmentProcessedTime': email_receive_time,
            'ExpirationTime': ttl_value
            }
    try:
        table.put_item(Item=item)
        print(f"Item added to DynamoDB table: {item}")
    except ClientError as e:
        print(f"Error adding item to DynamoDB table: {e.response['Error']['Message']}")
        
def update_dynamodb(case_id, email_subject, email_body, from_email, dominant_language, processed_bucket, processed_file_key, base_path, attachment_status, body_status, bucket_name):
    try:
        current_timestamp = datetime.now(eastern_tz).isoformat()
        # Update the item in the DynamoDB table
        response = table.update_item(
            Key={'CaseID': int(case_id)},
            UpdateExpression="SET RawFilePath=:base_path, RawBucketName=:bucket_name,EmailSubject=:subject, EmailBody=:body,FromAddress=:from_email,DominantLanguage=:dominant_language,ProcessedBucketName=:processed_bucket, ProcessedFilePath=:processed_key, BodyStatus=:body_status, BodyProcessedTime=:current_timestamp, AttachmentStatus=:attachment_status",
            ExpressionAttributeValues={
                ':base_path': base_path,
                ':bucket_name': bucket_name,
                ':subject': email_subject,
                ':body': email_body,
                ':from_email': from_email,
                ':dominant_language': dominant_language,
                ':processed_bucket': processed_bucket,
                ':processed_key': processed_file_key,
                ':body_status': body_status,
                ':current_timestamp': current_timestamp,
                ':attachment_status': attachment_status
            },
            ReturnValues="UPDATED_NEW"
        )

        print(f"DynamoDB table updated for case_id {case_id}: {response['Attributes']}")
    except ClientError as e:
        print(f"Error updating DynamoDB table for case_id {case_id}: {e.response['Error']['Message']}")
        raise
        
def generate_case_id():
    # Generate a unique 6-digit case ID
    case_id=0
    case_id_exists = True
    while case_id_exists:
        case_id = ''.join(random.choices('0123456789', k=6))
        print("case id is:", case_id)
        # Check if the case ID already exists in the DynamoDB table
        try:
            response = table.get_item(Key={'CaseID': case_id})
            item = response.get('Item')
            if not item:
                # Case ID is unique, break out of the loop
                case_id_exists = False
        except ClientError as e:
            print(f"Error checking for existing case ID: {e.response['Error']['Message']}")
            case_id_exists = False
    return case_id


def extract_email_from_s3(bucket_name, object_key, case_id):
    """
    Extract the raw email from S3.
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        email_content = response['Body'].read()
        return email_content
    except Exception as e:
        error_message = f"Failed to extract email from S3 for case_id {case_id}: {str(e)}"
        publish_failure_notification(case_id, 'extract_email_from_s3', error_message)
        raise

def parse_email(email_content, case_id):
    """
    Parse the email content to extract the body (plain text and HTML) and attachments.
    """
    try:
        msg = BytesParser(policy=policy.default).parsebytes(email_content)
       
        # Extract subject
        email_subject = msg.get('Subject', '')
       
        #Extract from email address
        from_email = msg.get('From', '')
 
        # Extract plain text and HTML body
        body_plain = None
        body_html = None
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    if 'attachment' in part.get('Content-Disposition', ''):
                        # This is a text attachment, not the body
                        attachments.append({
                            'filename': part.get_filename(),
                            'content': part.get_payload(decode=True),
                            'content_type': part.get_content_type()
                            })
                    else:
                        # This is the plain text body
                        body_plain = part.get_payload(decode=True).decode(part.get_content_charset(), errors='ignore')
                elif part.get_content_type() == 'text/html':
                    if 'attachment' in part.get('Content-Disposition', ''):
                        # This is a html attachment, not the body
                        attachments.append({
                            'filename': part.get_filename(),
                            'content': part.get_payload(decode=True),
                            'content_type': part.get_content_type()
                        })
                    else:
                        body_html = part.get_payload(decode=True).decode(part.get_content_charset(), errors='ignore')
                elif part.get_filename():
                    # This is a non-text attachment
                    attachments.append({
                        'filename': part.get_filename(),
                        'content': part.get_payload(decode=True),
                        'content_type': part.get_content_type()
                    })
        else:
            charset = msg.get_content_charset()
            if charset is None:
                charset = 'utf-8'
            body_plain = msg.get_payload(decode=True).decode(charset, errors='ignore')
        return body_plain, body_html, attachments, email_subject, from_email
    except Exception as e:
        error_message = f"Failed to parse email for case_id {case_id}: {str(e)}"
        publish_failure_notification(case_id, 'parse_email', error_message)
        raise

def save_to_s3(bucket_name, case_id, email_body_plain, email_body_html, attachments, file_type='raw'):
    """
    Save email body (plain text and HTML) and attachments to S3 under the folder structure 'raw_email/today_date/case_id'.
    """
    today_date = datetime.now(eastern_tz).strftime('%Y-%m-%d')
    if file_type == 'raw':
        base_path = f'raw_email/{today_date}/{case_id}'
    else:
        base_path = f'redacted/{today_date}/{case_id}'
    try:
        # Save plain text email body
        if email_body_plain:
            body_plain_key = f'{base_path}/body/email_body.txt'
            s3.put_object(Bucket=bucket_name, Key=body_plain_key, Body=email_body_plain)
            print(f'Plain text email body saved to: {body_plain_key}')
        # Save HTML email body
        if email_body_html:
            body_html_key = f'{base_path}/body/email_body.html'
            s3.put_object(Bucket=bucket_name, Key=body_html_key, Body=email_body_html, ContentType='text/html')
            print(f'HTML email body saved to: {body_html_key}')
        # Save attachments
        if file_type == 'raw':
            for attachment in attachments:
                attachment_key = f'{base_path}/attachments/{attachment["filename"]}'
                s3.put_object(
                    Bucket=bucket_name,
                    Key=attachment_key,
                    Body=attachment['content'],
                    ContentType=attachment['content_type']
                )
                print(f'Attachment saved to: {attachment_key}')
    except Exception as e:
        error_message = f"Failed to save data to S3 for case_id {case_id}: {str(e)}"
        publish_failure_notification(case_id, 'save_to_s3', error_message)
        raise
    return base_path

def publish_success_notification(case_id, bucket_name, base_path, push_message, topic_arn):
    """
    Publish a success message to an SNS topic after email body and attachments are saved.
    """
    try:
        message = {
            'case_id': case_id,
            'bucket_name': bucket_name,
            'base_path': base_path,
            'message': push_message
        }

        response = sns.publish(
            TopicArn=topic_arn,
            Message=json.dumps(message),
            Subject=f'Email Processed for Case ID {case_id}'
        )

        print(f"SNS Success Notification sent with message ID: {response['MessageId']} in topic {topic_arn}")
    except Exception as e:
        print(f"Failed to send success notification for case_id {case_id}: {str(e)} in {topic_arn}")
        raise

def publish_failure_notification(case_id, step, error_message):
    """
    Publish a failure message to an SNS topic if any step fails.
    """
    try:
        message = {
            'case_id': case_id,
            'step': step,
            'error': error_message
        }

        response = sns.publish(
            TopicArn=SNS_FAILURE_TOPIC_ARN,
            Message=json.dumps(message),
            Subject=f'Failure in processing email'
        )

        print(f"SNS Failure Notification sent with message ID: {response['MessageId']} in topic {SNS_FAILURE_TOPIC_ARN}")
    except Exception as e:
        print(f"Failed to send failure notification for case_id {case_id}: {str(e)} in topic {SNS_FAILURE_TOPIC_ARN}")
        raise

def lambda_handler(event, context):
    # Inputs from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']
    current_timestamp = datetime.now(eastern_tz).isoformat()
    attachment_status='Open'
    step=""
    case_id=0
    body_table = ""
    dominant_language = "en"
    base_path=""
    try:
        step = "Step 1: Generate unique case id"
        case_id = generate_case_id()
        step = "Step 2: Initial entry into DynamoDB"
        insert_dynamodb(case_id,object_key,bucket_name,current_timestamp)
        step = "Step 3: Extract email content from S3"
        email_content = extract_email_from_s3(bucket_name, object_key, case_id)
        step = "Step 4: Parse the email to extract plain text body, HTML body, and attachments"
        email_body_plain, email_body_html, attachments, email_subject, from_email = parse_email(email_content, case_id)
        email_body_plain = extract_text_from_html(email_body_html)
        step = "Step 5: Save the extracted plain text body, HTML body, and attachments to S3 in the desired folder structure"
        base_path = save_to_s3(bucket_name, case_id, email_body_plain, email_body_html, attachments)
        
        if len(attachments) == 0:
            attachment_status='No attachment'
            
        if len(email_body_plain) > 0:
            step = "Step 6: Redact email plain body"
            redacted_plain_body = redact_pii(email_body_plain, email_body_html, 'plain')
            body_table = redacted_plain_body[:100] + '...' if len(redacted_plain_body) > 100 else redacted_plain_body
        if len(email_body_html) > 0:
            step = "Step 7: Redact email html body"
            redacted_html_body = redact_pii(email_body_plain, email_body_html, 'html')
        if len(email_subject) > 0:
            step = "Step 8: Redact email subject"
            redacted_subject = redact_pii(email_subject, email_body_html, 'plain')
            # Append case ID to the redacted email subject
            updated_subject = f"[Case ID: {case_id}] - {redacted_subject}"
        else:
            step = "Step 8: Redact email subject"
            updated_subject = f"[Case ID: {case_id}]"
        
        step = "Step 9: Save redacted email body in redacted s3 bucket"
        processed_path = save_to_s3(processed_bucket, case_id, redacted_plain_body, redacted_html_body, attachments,'redacted')
        
        step = "Step 10: Update dynamodb post processing"
        update_dynamodb(case_id, updated_subject, body_table, from_email, 'en', processed_bucket, processed_path, base_path,attachment_status,'Processed',bucket_name )
        
        if attachment_status == 'No attachment':
            step = "Step 12: Send notification to CRM topic in case of no attachments"
            push_message = "Email is ready for CRM processing"
            publish_success_notification(case_id, processed_bucket, processed_path, push_message, CRM_TOPIC_ARN)
        else:
            step = "Step 12: Send a success SNS notification after saving everything for attachment redaction. Check attachment redaction lambda for update on attachment redaction"
            push_message = "Email body and attachments have been successfully saved to S3."
            publish_success_notification(case_id, bucket_name, base_path, push_message, SNS_SUCCESS_TOPIC_ARN)
        
    except Exception as e:
        if case_id != 0:
            update_dynamodb(case_id,'NA','NA','NA','NA','NA','NA',object_key,'Open','Failed',bucket_name)
        if base_path == "":
            error_message = f"Unhandled error for case_id {case_id}: with raw file at {object_key} in bucket {bucket_name}. Error: {str(e)}"
        else:
            error_message = f"Unhandled error for case_id {case_id}: with raw file at {base_path} in bucket {bucket_name}. Error: {str(e)}"
        publish_failure_notification(case_id, step, error_message)
        print(f'Failed to process email for case_id: {case_id} at {step}')
        return {
            'statusCode': 500,
            'body': f'Failed to process email for case_id: {case_id} at {step}'
        }
    print(f'Email body and attachments saved for case_id: {case_id}! Also redaction of PII data completed for body and attachment if any redaction process initiated')
    return {
            'statusCode': 200,
            'body': f'Email body and attachments saved for case_id: {case_id}! Also redaction of PII data completed for body and attachment if any redaction process initiated'
        }