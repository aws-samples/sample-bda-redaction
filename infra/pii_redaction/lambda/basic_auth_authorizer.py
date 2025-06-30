import base64
import boto3
import os
import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_lambda_powertools.utilities.data_classes.api_gateway_authorizer_event import (
    DENY_ALL_RESPONSE,
    APIGatewayAuthorizerRequestEvent,
    APIGatewayAuthorizerResponse,
    HttpVerb,
)

logger = Logger(
    log_record_order=["message", "operation", "service", "namespace"],
    log_uncaught_exceptions=True,
    serialize_stacktrace=False
)
logger.append_keys(namespace="PII-Redaction-Authorizer")

secretsmanager = boto3.client('secretsmanager')

@event_source(data_class=APIGatewayAuthorizerRequestEvent)
def handler(event: APIGatewayAuthorizerRequestEvent, context):
    """
    Lambda function to handle basic authentication for API Gateway authorizer
    """

    logger.info(f"Received event: {event}")
    
    # Get the authorization header from the event
    auth_header = event.authorization_token
    
    # Check if the authorization header is present
    if not auth_header:
        raise DENY_ALL_RESPONSE
    
    # Check if the authorization header is in the correct format
    if not auth_header.startswith('Basic '):
        raise DENY_ALL_RESPONSE
    
    # Decode the authorization header
    encoded_credentials = auth_header.split(' ')[1]
    decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
    
    # Split the decoded credentials into username and password
    username, password = decoded_credentials.split(':')
    
    # Get AWS secrets manager secret
    secret_response = secretsmanager.get_secret_value(SecretId=os.environ['SECRET_ARN'])
    secret = json.loads(secret_response['SecretString'])

    # parse the `methodArn` as an `APIGatewayRouteArn`
    arn = event.parsed_arn
    
    # If authentication succeeds, return a policy allowing the user to access the resource
    policy = APIGatewayAuthorizerResponse(
        principal_id=username,
        context={'username': username},
        region=arn.region,
        aws_account_id=arn.aws_account_id,
        api_id=arn.api_id,
        stage=arn.stage,
    )

    if username == secret['username'] and password == secret['password']:
        policy.allow_all_routes()
    else:
        policy.deny_all_routes()

    return policy.asdict()