import time
import os
import boto3
import json
import fitz  # PyMuPDF for PDF processing
from botocore.exceptions import ClientError
from datetime import datetime, date
from PIL import Image, ImageDraw
import pytz
from urllib.parse import urlparse


s3 = boto3.client('s3')
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

bda = boto3.client('bedrock-data-automation')
bda_client = boto3.client('bedrock-data-automation-runtime')
bedrock_runtime = boto3.client('bedrock-runtime')
redacted_bucket = os.environ['REDACTED_BUCKET_NAME']
table_name = os.environ['INVENTORY_TABLE_NAME']
project_name = os.environ['PROJECT_NAME']
table = dynamodb.Table(table_name)
eastern_tz = pytz.timezone('US/Eastern')



# Define SNS Topic ARNs for success and failure
SNS_FAILURE_TOPIC_ARN = os.environ['FAILURE_TOPIC_ARN']
CRM_TOPIC_ARN = os.environ['CRM_TOPIC_ARN']
guardrail_id = os.environ['GUARDRAIL_ID']
guardrail_version = os.environ['GUARDRAIL_VERSION']
projects = bda.list_data_automation_projects()
project_arn = ""
for project in projects['projects']:
    if project['projectName'].lower() == project_name.lower():
        project_arn = project['projectArn']
        break


def update_dynamodb(case_id,attachment_status):
    try:
        current_timestamp = datetime.now(eastern_tz).isoformat()
        # Update the item in the DynamoDB table
        response = table.update_item(
            Key={'CaseID': int(case_id)},
            UpdateExpression="SET AttachmentProcessedTime=:current_timestamp,AttachmentStatus=:attachment_status",
            ExpressionAttributeValues={
                ':current_timestamp': current_timestamp,
                ':attachment_status': attachment_status
            },
            ReturnValues="UPDATED_NEW"
        )

        print(f"DynamoDB table updated for case_id {case_id}: {response['Attributes']}")
    except ClientError as e:
        print(f"Error updating DynamoDB table for case_id {case_id}: {e.response['Error']['Message']}")
        raise
def extract_pii_entities_from_pdf(bucket_name, input_pdf_key, profile_arn):
    """
    Extract PII from a PDF and return it back
    """
    s3_path = f"s3://{bucket_name}/{input_pdf_key}"
    s3_output_path = f"s3://{redacted_bucket}/working_dir"
    response = bda_client.invoke_data_automation_async(
                inputConfiguration={"s3Uri": s3_path},
                outputConfiguration={
                    "s3Uri": s3_output_path
                },
                dataAutomationConfiguration={
                    "dataAutomationProjectArn": project_arn,
                    "stage": "LIVE",
                },
                dataAutomationProfileArn= profile_arn
            )
    invocation_arn=response['invocationArn']
    while True:
        response = bda_client.get_data_automation_status(invocationArn=invocation_arn)
        if response['status'] == 'Success':
            job_id = invocation_arn.split("/")[-1]
            output_s3_uri = s3_output_path
            parsed_uri = urlparse(output_s3_uri)
            bucket = parsed_uri.netloc
            prefix = parsed_uri.path.lstrip("/").rstrip("/") + "/" + job_id

            #This does not support multi document
            prefix = os.path.join(
                        prefix, "0", "standard_output", "0", "result.json"
            )
            invocation_output = json.loads(
                                s3.get_object(Bucket=bucket, Key=prefix)["Body"]
                                .read()
                                .decode("utf-8")
                            )
            break
        time.sleep(30)
    pii_entities = []
    for element in invocation_output['elements']:
        for location in element['locations']:
            content = [
                    {
                        "text": {
                        "text": element['representation']['text']
                         }
                    }   
                ]
            response = bedrock_runtime.apply_guardrail(
                            guardrailIdentifier=guardrail_id,
                            guardrailVersion=guardrail_version,
                            source='OUTPUT',
                            content=content
                        )
        for assessment in response['assessments']:
            if 'sensitiveInformationPolicy' in assessment:
                for pii_entity in assessment['sensitiveInformationPolicy']['piiEntities']:
                    pii_entities.append({'text': pii_entity['match'], 'type' : pii_entity['type']})
    return pii_entities

def extract_pii_entities_from_images(bucket_name, input_image_key, profile_arn):
    """
    Extract bounding box of PII text from a JPEG or PNG and return it back
    """
    s3_path = f"s3://{bucket_name}/{input_image_key}"
    s3_output_path = f"s3://{redacted_bucket}/working_dir"
    response = bda_client.invoke_data_automation_async(
                inputConfiguration={"s3Uri": s3_path},
                outputConfiguration={
                    "s3Uri": s3_output_path
                },
                dataAutomationConfiguration={
                    "dataAutomationProjectArn": project_arn,
                    "stage": "LIVE",
                },
                dataAutomationProfileArn= profile_arn
            )
    invocation_arn=response['invocationArn']
    while True:
        response = bda_client.get_data_automation_status(invocationArn=invocation_arn)
        if response['status'] == 'Success':
            job_id = invocation_arn.split("/")[-1]
            output_s3_uri = s3_output_path
            parsed_uri = urlparse(output_s3_uri)
            bucket = parsed_uri.netloc
            prefix = parsed_uri.path.lstrip("/").rstrip("/") + "/" + job_id

            #This does not support multi document
            prefix = os.path.join(
                        prefix, "0", "standard_output", "0", "result.json"
            )
            invocation_output = json.loads(
                                s3.get_object(Bucket=bucket, Key=prefix)["Body"]
                                .read()
                                .decode("utf-8")
                            )
            break
        time.sleep(30)
    pii_entities = []
    bounding_boxes = []
    for element in invocation_output['elements']:
        for location in element['locations']:
            content = [
                    {
                        "text": {
                        "text": element['representation']['text']
                         }
                    }   
                ]
            response = bedrock_runtime.apply_guardrail(
                            guardrailIdentifier=guardrail_id,
                            guardrailVersion=guardrail_version,
                            source='OUTPUT',
                            content=content
                        )
        for assessment in response['assessments']:
            if 'sensitiveInformationPolicy' in assessment:
                for pii_entity in assessment['sensitiveInformationPolicy']['piiEntities']:
                    pii_entities.append({'text': pii_entity['match'], 'type' : pii_entity['type']})
    for word in invocation_output['text_words']:
        for entity in pii_entities:
            split_entity = entity['text'].split()
            if word['text'] in split_entity:
                for location in word['locations']:
                    bounding_boxes.append({'text': word['text'],'page_index': location['page_index'],'left': location['bounding_box']['left'], 'top': location['bounding_box']['top'], 'width': location['bounding_box']['width'], 'height': location['bounding_box']['height']})
    return bounding_boxes

def redact_pdf(bucket_name, redacted_bucket, input_pdf_key, output_pdf_key, pii_entities):
    """
    Redact PII in a PDF stored in S3 and save the redacted version back to S3.
    """
    # Download the PDF from S3
    local_file_name = input_pdf_key.split('/')[-1]
    local_input_pdf = f'/tmp/{local_file_name}'
    s3.download_file(bucket_name, input_pdf_key, local_input_pdf)
    # Open the PDF using PyMuPDF (fitz)
    pdf_document = fitz.open(local_input_pdf)
    # Loop through each page and redact PII
    for page_num in range(int(pdf_document.page_count)):
        page = pdf_document[page_num]
        page_text = page.get_text("text")
        # Redact PII by adding black boxes over the sensitive words
        for word in page.get_text("words"):
            word_text = word[4]
            word_bbox=fitz.Rect(word[:4])
            for entity in pii_entities: # Check if word is PII
                split_entity = entity['text'].split()
                if word_text in split_entity:
                    expanded_bbox = fitz.Rect(word_bbox.x0, word_bbox.y0, word_bbox.x1, word_bbox.y1)
                    page.draw_rect(expanded_bbox,fill=(0,0,0))
    # Save the redacted PDF
    local_output_pdf = f'/tmp/output_{local_file_name}'
    pdf_document.save(local_output_pdf)
    pdf_document.close()
    # Upload the redacted PDF back to S3
    s3.upload_file(local_output_pdf, redacted_bucket, output_pdf_key)

def redact_image(bucket_name, redacted_bucket, input_image_key, output_image_key, bounding_boxes, response):
    """
    Redact PII in a JPEG/JPG/PNG image stored in S3 and save the redacted version back to S3.
    """
    # Download the image from S3
    local_file_name = input_image_key.split('/')[-1]
    local_input_image = f'/tmp/{local_file_name}'
    s3.download_file(bucket_name, input_image_key, local_input_image)
    # Open the image using PIL
    image = Image.open(local_input_image)
    draw = ImageDraw.Draw(image)
    width, height = image.size
    # Redact PII by drawing black boxes over the sensitive words
    for data in bounding_boxes:
        left = int(data['left'] * width) - 5
        top = int(data['top'] * height) - 10
        right = int((data['left'] + data['width']) * width) + 5
        bottom = int((data['top'] + data['height']) * height) + 10
        draw.rectangle([left, top , right , bottom ], fill="black")
    # Save the redacted image
    local_output_image = f'/tmp/output_{local_file_name}'
    image.save(local_output_image)
    # Upload the redacted image back to S3
    s3.upload_file(local_output_image, redacted_bucket, output_image_key)

def process_success_message(message,profile_arn):
    try:
        case_id = message.get('case_id')
        bucket_name = message.get('bucket_name')
        base_path = message.get('base_path')
        attachments_path = base_path + '/attachments'

        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=attachments_path)
        if 'Contents' in response:
            # Check if file name already exists
            existing_files = []
            for obj in response['Contents']:
                attachment_key = obj['Key']
                file_name = attachment_key.split('/')[-1]
                date = attachment_key.split('/')[1]
                file_type = file_name.split('.')[-1].lower()
                file_name_no_extension = ".".join(file_name.split('.')[:-1])
                for name in existing_files:
                    if file_name_no_extension == name:
                        print (f"Duplicate file name found: {file_name_no_extension}")
                        raise ValueError(f"Duplicate file name found: {file_name_no_extension}")
            
                existing_files.append(file_name_no_extension)
            #continue processing if no duplicate file names found
            for obj in response['Contents']:
                attachment_key = obj['Key']
                file_name = attachment_key.split('/')[-1]
                date = attachment_key.split('/')[1]
                file_type = file_name.split('.')[-1].lower()
                file_name_no_extension = ".".join(file_name.split('.')[:-1])
                print(f"Processing {file_name}")
                if file_type == 'pdf':
                    # Handle PDF
                    pii_entities = extract_pii_entities_from_pdf(bucket_name, attachment_key, profile_arn)
                    output_pdf_key = f"redacted/{date}/{case_id}/attachments/{file_name}"
                    redact_pdf(bucket_name, redacted_bucket, attachment_key, output_pdf_key, pii_entities)

                elif file_type in ['jpg', 'jpeg', 'png']:
                    # Handle image formats directly
                    bounding_boxes = extract_pii_entities_from_images(bucket_name, attachment_key, profile_arn)
                    output_image_key = f"redacted/{date}/{case_id}/attachments/{file_name}"
                    redact_image(bucket_name, redacted_bucket, attachment_key, output_image_key, bounding_boxes, response)
                else:
                    # unsupported format
                    return {
                        'statusCode': 500,
                        'body': f'Error processing attachment for case {case_id}. Unsupported format'
                    }

    except Exception as e:
        print(f"Error processing success notification: {str(e)}")
        raise
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
        print(f"Failed to send success notification for case_id {case_id}: {str(e)} in topic {topic_arn}")
        raise

def publish_failure_notification(case_id, error_message):
    """
    Publish a failure message to an SNS topic if any step fails.
    """
    try:
        message = {
            'case_id': case_id,
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
    region = context.invoked_function_arn.split(":")[3]
    account_id = str(context.invoked_function_arn.split(":")[4])
    profile_arn = "arn:aws:bedrock:" + region + ":" + account_id + ":data-automation-profile/us.data-automation-v1"
    for record in event['Records']:
        message = {}
        sns_message = record['Sns']['Message']
        message = json.loads(sns_message)
        case_id = message.get('case_id')
        if project_arn == "":
            return {
                    'statusCode': 500,
                    'body': f'Error processing SNS notification for case {case_id}. Cannot find project arn for project {project_name}'
                    }
        try:
            process_success_message(message,profile_arn)
            update_dynamodb(case_id,'Processed')
            response = table.get_item(Key={'CaseID': int(case_id)})
            item = response.get('Item')
            processed_file_path = item.get('ProcessedFilePath')
            push_message = "Email is ready for CRM processing"
            publish_success_notification(case_id, redacted_bucket, processed_file_path, push_message, CRM_TOPIC_ARN)
        except Exception as e:
            update_dynamodb(case_id,'Failed')
            error_message = f"Failed redacting attachments for case id: {case_id}. Check for details in dynamodb table for this case id"
            publish_failure_notification(case_id,error_message)
            print(f"Error in processing SNS event: {str(e)}")
            return {
                'statusCode': 500,
                'body': f'Error processing SNS notification for case {case_id}'
            }
    return {
            'statusCode': 200,
            'body': 'Success SNS notification processed successfully'
        }