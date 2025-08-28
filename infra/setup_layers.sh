#!/usr/bin/env bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run commands with error handling
run_command() {
    local cmd="$1"
    local description="$2"
    
    print_status "Running: $description"
    if eval "$cmd"; then
        print_status "✓ $description completed successfully"
        return 0
    else
        print_error "✗ $description failed"
        return 1
    fi
}

# Function to build lambda layer
build_lambda_layer() {
    local layer_path="$1"
    local layer_name="$2"
    
    print_status "Building $layer_name lambda layer..."
    
    if [[ ! -d "$layer_path" ]]; then
        print_error "Directory $layer_path does not exist"
        return 1
    fi
    
    if [[ ! -f "$layer_path/build_layer.sh" ]]; then
        print_error "build_layer.sh not found in $layer_path"
        return 1
    fi
    
    # Change to the layer directory
    if ! cd "$layer_path"; then
        print_error "Failed to change to directory $layer_path"
        return 1
    fi
    
    # Make script executable and run it
    if run_command "chmod +x build_layer.sh" "Making build_layer.sh executable for $layer_name"; then
        if run_command "./build_layer.sh" "Building $layer_name layer"; then
            print_status "✓ $layer_name layer built successfully"
            return 0
        else
            print_error "✗ Failed to build $layer_name layer"
            return 1
        fi
    else
        print_error "✗ Failed to make build_layer.sh executable for $layer_name"
        return 1
    fi
}

# Main execution
main() {
    print_status "Starting lambda layer build process..."
    
    # Store original directory
    ORIGINAL_DIR=$(pwd)
    
    # Check if we're in the right directory
    if [[ ! -d "pii_redaction/lambda" ]]; then
        print_error "pii_redaction/lambda directory not found. Please run this script from the infra directory."
        exit 1
    fi
    
    # Change to lambda directory
    if ! cd pii_redaction/lambda; then
        print_error "Failed to change to pii_redaction/lambda directory"
        exit 1
    fi
    
    # Build each lambda layer
    local failed=0
    
    # Build main lambda layer
    if ! build_lambda_layer "lambda-layer" "main"; then
        failed=1
    fi
    
    # Return to lambda directory for next layer
    cd "$ORIGINAL_DIR/pii_redaction/lambda" || exit 1
    
    # Build attachment processing layer
    if ! build_lambda_layer "attachmentProcessing/lambda-layer" "attachment processing"; then
        failed=1
    fi
    
    # Return to lambda directory for next layer
    cd "$ORIGINAL_DIR/pii_redaction/lambda" || exit 1
    
    # Build email processing layer
    if ! build_lambda_layer "emailProcessing/lambda-layer" "email processing"; then
        failed=1
    fi
    
    # Return to original directory
    cd "$ORIGINAL_DIR" || exit 1
    
    if [[ $failed -eq 0 ]]; then
        print_status "🎉 All lambda layers built successfully!"
        exit 0
    else
        print_error "❌ Some lambda layers failed to build. Check the output above for details."
        exit 1
    fi
}

# Run main function
main "$@"
