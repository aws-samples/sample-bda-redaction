from aws_cdk import (
    aws_apigateway as apigateway
)
from aws_cdk.aws_lambda import CfnPermission

class LambdaIntegrationNoPermission(apigateway.LambdaIntegration):
    def __init__(self, handler, **kwargs):
        super().__init__(handler, **kwargs)
    
    def bind(self, method: apigateway.Method):
        integration_config = super().bind(method)
        permissions = filter(lambda x: isinstance(x, CfnPermission), method.node.children)
        
        # Removing permissions policy for each integration
        for p in permissions:
            method.node.try_remove_child(p.node.id)
        return integration_config