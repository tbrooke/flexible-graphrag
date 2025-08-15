#!/bin/bash

# OpenSearch Hybrid Search Pipeline Setup Script
# This script creates the required search pipeline for hybrid search functionality

# Default configuration
OPENSEARCH_URL="http://localhost:9201"
PIPELINE_NAME="hybrid-search-pipeline"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}OpenSearch Hybrid Search Pipeline Setup${NC}"
echo "========================================"

# Check if OpenSearch is running
echo -e "${YELLOW}Checking OpenSearch connectivity...${NC}"
if curl -s "${OPENSEARCH_URL}/_cluster/health" > /dev/null; then
    echo -e "${GREEN}✓ OpenSearch is accessible at ${OPENSEARCH_URL}${NC}"
else
    echo -e "${RED}✗ Cannot connect to OpenSearch at ${OPENSEARCH_URL}${NC}"
    echo "Please ensure OpenSearch is running and accessible."
    exit 1
fi

# Create the hybrid search pipeline
echo -e "${YELLOW}Creating hybrid search pipeline...${NC}"
RESPONSE=$(curl -s -w "%{http_code}" -X PUT "${OPENSEARCH_URL}/_search/pipeline/${PIPELINE_NAME}" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Post processor for hybrid search",
    "phase_results_processors": [
      {
        "normalization-processor": {
          "normalization": {
            "technique": "min_max"
          },
          "combination": {
            "technique": "harmonic_mean",
            "parameters": {
              "weights": [0.3, 0.7]
            }
          }
        }
      }
    ]
  }')

HTTP_CODE="${RESPONSE: -3}"
RESPONSE_BODY="${RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ Pipeline '${PIPELINE_NAME}' created successfully${NC}"
    echo "  - Normalization: min_max"
    echo "  - Combination: harmonic_mean"
    echo "  - Weights: [0.3, 0.7] (30% vector, 70% text)"
else
    echo -e "${RED}✗ Failed to create pipeline (HTTP ${HTTP_CODE})${NC}"
    echo "Response: ${RESPONSE_BODY}"
    exit 1
fi

# Verify pipeline creation
echo -e "${YELLOW}Verifying pipeline creation...${NC}"
if curl -s "${OPENSEARCH_URL}/_search/pipeline/${PIPELINE_NAME}" | grep -q "hybrid-search-pipeline"; then
    echo -e "${GREEN}✓ Pipeline verification successful${NC}"
else
    echo -e "${RED}✗ Pipeline verification failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 OpenSearch hybrid search pipeline setup complete!${NC}"
echo ""
echo "You can now use hybrid search with:"
echo "  VECTOR_DB=opensearch"
echo "  SEARCH_DB=opensearch"
echo ""
echo "To adjust weights, edit the weights in this script:"
echo "  [0.3, 0.7] = 30% vector, 70% text (keyword focus)"
echo "  [0.5, 0.5] = 50% vector, 50% text (balanced)"
echo "  [0.7, 0.3] = 70% vector, 30% text (semantic focus)"
echo ""
echo -e "${BLUE}Pipeline URL: ${OPENSEARCH_URL}/_search/pipeline/${PIPELINE_NAME}${NC}"
