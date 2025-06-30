def stackPrefix(resource_prefix: str, resource_name: str) -> str:
    if not resource_prefix:
        raise ValueError("Resource prefix cannot be empty")
    
    if not resource_name:
        raise ValueError("Resource name cannot be empty")
    
    return f"{resource_prefix}-{resource_name}"