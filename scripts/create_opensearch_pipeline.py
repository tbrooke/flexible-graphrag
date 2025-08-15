#!/usr/bin/env python3
"""
OpenSearch Hybrid Search Pipeline Management Script
Creates and updates OpenSearch search pipelines for hybrid search functionality.
Uses direct REST API calls instead of specialized client libraries.
"""

import sys
import json
import argparse
import requests
from requests.exceptions import RequestException

def create_opensearch_client(host='localhost', port=9201, username=None, password=None, use_ssl=False):
    """Create OpenSearch client configuration for REST API calls."""
    protocol = 'https' if use_ssl else 'http'
    base_url = f"{protocol}://{host}:{port}"
    
    session = requests.Session()
    if username and password:
        session.auth = (username, password)
    
    # Configure session for OpenSearch
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    # Disable SSL warnings for self-signed certificates
    if use_ssl:
        session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    return session, base_url

def create_pipeline_config(vector_weight=0.5, text_weight=0.5, description=None):
    """Create pipeline configuration with specified weights."""
    if description is None:
        description = f"Hybrid search pipeline with weights [{vector_weight}, {text_weight}]"
    
    return {
        "description": description,
        "phase_results_processors": [
            {
                "normalization-processor": {
                    "normalization": {
                        "technique": "min_max"
                    },
                    "combination": {
                        "technique": "harmonic_mean",
                        "parameters": {
                            "weights": [vector_weight, text_weight]
                        }
                    }
                }
            }
        ]
    }

def manage_pipeline(session, base_url, pipeline_name, vector_weight=0.5, text_weight=0.5, force_update=False):
    """Create or update OpenSearch search pipeline."""
    
    pipeline_url = f"{base_url}/_search/pipeline/{pipeline_name}"
    
    # Check if pipeline exists
    pipeline_exists = False
    try:
        response = session.get(pipeline_url)
        if response.status_code == 200:
            pipeline_exists = True
            print(f"Pipeline '{pipeline_name}' already exists.")
            
            if not force_update:
                user_response = input("Update existing pipeline? (y/N): ")
                if user_response.lower() not in ['y', 'yes']:
                    print("Operation cancelled.")
                    return False
        elif response.status_code != 404:
            print(f"Error checking pipeline (HTTP {response.status_code}): {response.text}")
            return False
    except RequestException as e:
        print(f"Error checking pipeline: {e}")
        return False
    
    if not pipeline_exists:
        print(f"Pipeline '{pipeline_name}' does not exist. Creating new pipeline.")
    
    # Create pipeline configuration
    pipeline_config = create_pipeline_config(
        vector_weight=vector_weight,
        text_weight=text_weight,
        description=f"Hybrid search pipeline - {vector_weight*100:.0f}% vector, {text_weight*100:.0f}% text"
    )
    
    try:
        # Create or update pipeline
        response = session.put(pipeline_url, json=pipeline_config)
        
        if response.status_code in [200, 201]:
            action = "Updated" if pipeline_exists else "Created"
            print(f"✓ {action} pipeline '{pipeline_name}' successfully!")
            print(f"  Vector weight: {vector_weight} ({vector_weight*100:.0f}%)")
            print(f"  Text weight: {text_weight} ({text_weight*100:.0f}%)")
            print(f"  Normalization: min_max")
            print(f"  Combination: harmonic_mean")
            return True
        else:
            print(f"✗ Failed to manage pipeline (HTTP {response.status_code}): {response.text}")
            return False
        
    except RequestException as e:
        print(f"✗ Failed to manage pipeline: {e}")
        return False

def test_connection(session, base_url):
    """Test connection to OpenSearch cluster."""
    try:
        response = session.get(f"{base_url}/_cluster/health")
        if response.status_code == 200:
            health = response.json()
            return health.get('cluster_name', 'Unknown')
        else:
            raise RequestException(f"HTTP {response.status_code}: {response.text}")
    except RequestException as e:
        raise RequestException(f"Cannot connect to OpenSearch: {e}")

def main():
    parser = argparse.ArgumentParser(description='Manage OpenSearch hybrid search pipelines')
    parser.add_argument('--host', default='localhost', help='OpenSearch host (default: localhost)')
    parser.add_argument('--port', type=int, default=9201, help='OpenSearch port (default: 9201)')
    parser.add_argument('--username', help='OpenSearch username (optional)')
    parser.add_argument('--password', help='OpenSearch password (optional)')
    parser.add_argument('--pipeline-name', default='hybrid-search-pipeline', help='Pipeline name (default: hybrid-search-pipeline)')
    parser.add_argument('--vector-weight', type=float, default=0.5, help='Vector search weight (default: 0.5)')
    parser.add_argument('--text-weight', type=float, default=0.5, help='Text search weight (default: 0.5)')
    parser.add_argument('--force-update', action='store_true', help='Update without confirmation')
    parser.add_argument('--ssl', action='store_true', help='Use SSL connection')
    
    args = parser.parse_args()
    
    # Validate weights
    if abs(args.vector_weight + args.text_weight - 1.0) > 0.001:
        print("Error: Vector and text weights must sum to 1.0")
        sys.exit(1)
    
    try:
        # Create OpenSearch client
        print(f"Connecting to OpenSearch at {args.host}:{args.port}...")
        session, base_url = create_opensearch_client(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            use_ssl=args.ssl
        )
        
        # Test connection
        cluster_name = test_connection(session, base_url)
        print(f"✓ Connected to OpenSearch cluster: {cluster_name}")
        
        # Manage pipeline
        success = manage_pipeline(
            session=session,
            base_url=base_url,
            pipeline_name=args.pipeline_name,
            vector_weight=args.vector_weight,
            text_weight=args.text_weight,
            force_update=args.force_update
        )
        
        if success:
            print(f"\nPipeline URL: {base_url}/_search/pipeline/{args.pipeline_name}")
            print(f"Use in your application: search_pipeline='{args.pipeline_name}'")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()