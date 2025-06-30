import boto3
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import smtplib
from email import encoders
import os

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
secrets_manager = boto3.client('secretsmanager')
my_session = boto3.session.Session()
my_region = my_session.region_name


table_name = os.environ['INVENTORY_TABLE_NAME']
auto_reply_from_email = os.environ['AUTO_REPLY_FROM_EMAIL']
secret_name = os.environ['SECRET_NAME']

table = dynamodb.Table(table_name)

def get_email_data_from_dynamodb(case_id):
    """
    Fetch the redacted email body and attachments path from DynamoDB using case_id.
    """
    
    # Retrieve the redacted email information from DynamoDB
    response = table.get_item(Key={'CaseID': int(case_id)})
    
    item = response.get('Item')
    if not item:
        raise ValueError(f"Case ID {case_id} not found in DynamoDB.")
    
    # Extract the S3 paths for the redacted body and attachments
    subject = item['EmailSubject']
    redacted_bucket = item['ProcessedBucketName']
    redacted_path = item['ProcessedFilePath']
    redacted_body_path = f'{redacted_path}/body'
    redacted_attachments_path = f'{redacted_path}/attachments'
    
    return subject, redacted_bucket, redacted_body_path, redacted_attachments_path

def download_redacted_body_from_s3(s3_bucket, body_path):
    """
    Download the redacted body content from S3 and return the content as text.
    """
    body_key = f'{body_path}/email_body.txt'
    
    # Fetch the redacted body content
    response = s3.get_object(Bucket=s3_bucket, Key=body_key)
    redacted_body = response['Body'].read().decode('utf-8')
    
    return redacted_body

def create_email(case_id):
    """
    Forwards the redacted email with attachments using AWS SES.
    """
    
    # Fetch S3 paths for redacted body and attachments from DynamoDB
    subject, redacted_bucket, redacted_body_path, redacted_attachments_path = get_email_data_from_dynamodb(case_id)
    
    # Download the redacted email body from S3
    redacted_body = download_redacted_body_from_s3(redacted_bucket,redacted_body_path)
    
    # Create the email message with the subject prefixed by "FW:"
    subject = f"FW: {subject}"
    body_text = f"Please find the forwarded email for Case ID {case_id}.\n\n{redacted_body}"
    body_html = f"<html><body><p>Please find the forwarded email for Case ID {case_id}.</p><hr>{redacted_body}</body></html>"

    # Build the email message
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = auto_reply_from_email

    # Attach the email body (both text and HTML)
    part1 = MIMEText(body_text, 'plain')
    part2 = MIMEText(body_html, 'html')
    msg.attach(part1)
    msg.attach(part2)

    # Get attachments from S3 folder
    attachment_objects = s3.list_objects_v2(Bucket=redacted_bucket, Prefix=redacted_attachments_path)

    # Loop through attachments and add them to the email
    for attachment in attachment_objects.get('Contents', []):
        attachment_key = attachment['Key']
        attachment_data = s3.get_object(Bucket=redacted_bucket, Key=attachment_key)['Body'].read()

        # Create a MIME part for each attachment
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attachment_key.split("/")[-1]}"')

        # Attach the part to the email
        msg.attach(part)
    return msg

def send_email(msg,forwarding_email):
    print("Forwarding email to", forwarding_email)
    msg['To'] = forwarding_email
    # Send the email using AWS SES
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            secret_string = response['SecretString']
            secret_dict = json.loads(secret_string)
            smtp_username = secret_dict['smtp_username']
            smtp_password = secret_dict['smtp_password']
        else:
            raise ValueError("Secret does not contain a SecretString")
        smtp_server = f'email-smtp.{my_region}.amazonaws.com'
        smtp_port = 587
        session = smtplib.SMTP(smtp_server, smtp_port)
        session.starttls()
        session.login(smtp_username, smtp_password)
        #for forward_to in forwarding_email:
        session.sendmail(auto_reply_from_email, forwarding_email, msg.as_string())
        session.quit()
        print(f"Email forwarded!")
    except Exception as e:
        print(f"Error forwarding email: {e}")


# Lambda handler
def lambda_handler(event, context):
    """
    Lambda function to forward a redacted email and its attachments.
    The event contains the case_id and forwarding email.
    """
    try:
        # Extract case_id and forwarding_email from the API Gateway event
        if 'case_id' in event:
            # API Gateway often sends the body as a JSON string, so parse it
            body = event
            case_id = body.get('case_id')
            forwarding_emails = body.get('forwarding_email')
        else:
            # If the event doesn't follow the expected structure
            raise ValueError("No 'body' field found in the event.")

        # Validate that we have the required parameters
        if not case_id or not forwarding_emails:
            raise ValueError("Missing 'case_id' or 'forwarding_email' in the request body.")
        
        # Forward the redacted email
        msg = create_email(case_id)
        for forwarding_email in forwarding_emails:
            send_email(msg, forwarding_email)
        
        return {
            'statusCode': 200,
            'body': json.dumps(f"Email for Case ID {case_id} forwarded to {forwarding_email}.")
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Failed to forward email for Case ID {case_id}. Error: {str(e)}")
            }