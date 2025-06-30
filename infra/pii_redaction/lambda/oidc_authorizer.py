import json
import jwt
import jwt.algorithms
import requests
import os
import re
import boto3

from datetime import datetime, timezone
from http import HTTPStatus
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_lambda_powertools.utilities.data_classes.api_gateway_authorizer_event import (
    DENY_ALL_RESPONSE,
    APIGatewayAuthorizerRequestEvent,
    APIGatewayAuthorizerResponse,
    HttpVerb,
)
from aws_lambda_powertools.event_handler import (
    Response,
    content_types
)
from botocore.exceptions import ClientError

logger = Logger(
    log_record_order=["message", "operation", "service", "namespace"],
    log_uncaught_exceptions=True,
    serialize_stacktrace=False,
    level="DEBUG" if os.environ['ENVIRONMENT'] in ['local', 'development'] else "INFO"
)
logger.append_keys(namespace="PII-Redaction-APIAuthorizer")

dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])

def check_token_replay(jti, exp):
    # Store used JTIs in DynamoDB with TTL set to token expiration
    # Reject if JTI already exists
    pass

def sanitize_user_id(user_id):
    if not re.match("^[a-zA-Z0-9_-|]+$", user_id):
        logger.error("Invalid user ID format")
        return DENY_ALL_RESPONSE
    return user_id

@event_source(data_class=APIGatewayAuthorizerRequestEvent)
def lambda_handler(event: APIGatewayAuthorizerRequestEvent, context):
    """
    Lambda function to handle OIDC authorization for API Gateway
    """

    logger.debug(f"Received event")
    logger.debug(event)

    # Get the authorization header from the event
    auth_header = event.authorization_token

    # Add additional validation checks before processing the token
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.error("Invalid authorization header format")
        return DENY_ALL_RESPONSE
    

    token = auth_header.split(' ')[1]  # Extract token from header
    logger.debug(f"Token: {token}")

    try:
        # Fetch the public key from the OIDC provider
        jwks_uri = os.environ['JWKS_URI']
        jwks_response = requests.get(jwks_uri, timeout=(5, 5))
        jwks_response.raise_for_status()
        jwks = jwks_response.json()

        # Find the appropriate key based on the 'kid' in the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header['kid']
        
        for key in jwks['keys']:
            if key['kid'] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break

        # Verify the token using the public key
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=[os.environ['OIDC_ALGO']],  # Adjust algorithm based on your OIDC provider
            audience=os.environ['OIDC_AUDIENCE'],  # Specify the audience claim
            issuer=os.environ['OIDC_ISSUER'],  # Specify the issuer claim
            options={
                'verify_exp': True,
                'verify_aud': True,
                'verify_iss': True,
                'require': ['exp', 'iss', 'aud', 'sub']
            }
        )

        logger.debug("Token verified successfully")

         # Validate token age
        now = datetime.now(timezone.utc)
        iat = datetime.fromtimestamp(decoded_token['iat'], tz=timezone.utc)
        if (now - iat).total_seconds() > 1800:  # Token age > 30 min
            logger.error("Token too old")
            return DENY_ALL_RESPONSE

        # Token verification successful
        logger.debug("Token verified successfully")

        user_id = decoded_token['sub']

        users_table = dynamodb.Table(os.environ['USERS_TABLE_NAME'])
        result = users_table.get_item(
            Key={'ID': user_id}, 
            ConsistentRead=True
        )

        if 'Item' not in result:
            logger.error({
                "security_event": "authentication",
                "user_id": user_id,
                "details": "User not found",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return DENY_ALL_RESPONSE
    
        logger.debug(result['Item'])

        # parse the `methodArn` as an `APIGatewayRouteArn`
        arn = event.parsed_arn

        # If authentication succeeds, return a policy allowing the user to access the resource
        policy = APIGatewayAuthorizerResponse(
            principal_id=user_id,
            context={'username': user_id},
            region=arn.region,
            aws_account_id=arn.aws_account_id,
            api_id=arn.api_id,
            stage=arn.stage,
        )
    except Exception as e:
        logger.exception(e)
        return DENY_ALL_RESPONSE
    
    policy.allow_all_routes()
    return policy.asdict()

    # Return the decoded token or other data
    # return {"statusCode": 200, "body": json.dumps({"message": "Token verified"}) }