# Azure AI Services Setup Guide

This guide provides step-by-step instructions for setting up the required Azure services for the Executive Orders RAG chatbot.

## Cost-Effective Azure Setup

We'll set up the minimum required Azure services with cost-optimization in mind:

1. **Azure AI Search** - For vector search and document retrieval
2. **Azure OpenAI Service** (optional for now) - For embeddings and text generation

## Step 1: Set Up Azure AI Search

### Create an Azure AI Search Service

1. Log in to the [Azure Portal](https://portal.azure.com)

2. Click on "Create a resource" and search for "Azure AI Search"

3. Click "Create" to start creating a new search service

4. Fill in the basic information:
   - **Subscription**: Select your subscription
   - **Resource Group**: Create new or use existing
   - **Service name**: Enter a unique name (e.g., `exec-orders-search`)
   - **Location**: Choose a region near you
   - **Pricing tier**: Select "Basic" for development (lowest cost option)
     - Basic tier pricing is approximately $0.269/hour (~$197/month)
     - For true cost efficiency during development, you can create/delete the resource as needed

5. Click "Review + create" and then "Create" to deploy the service

6. Once deployment is complete, go to the resource

7. In the left menu, go to "Keys" to find:
   - **URL**: This is your `AZURE_SEARCH_ENDPOINT`
   - **Primary Admin Key**: This is your `AZURE_SEARCH_API_KEY`

8. Copy these values to your `.env` file:
   ```
   AZURE_SEARCH_ENDPOINT=https://<your-service-name>.search.windows.net
   AZURE_SEARCH_API_KEY=<your-primary-admin-key>
   AZURE_SEARCH_INDEX_NAME=executive-orders-index
   ```

## Step 2: Upload Your Documents to Azure AI Search

Now that you have Azure AI Search set up, you can upload your processed and embedded documents:

1. First make sure you have processed your documents and generated embeddings:
   ```bash
   python scripts/ingest.py --input test_docs --output data/processed_chunks.json
   python scripts/embed.py --input data/processed_chunks.json --output data/embedded_chunks.json
   ```

2. Upload your embedded documents to Azure AI Search:
   ```bash
   python scripts/upload_to_azure.py --input data/embedded_chunks.json
   ```

3. This script will:
   - Create a new index in Azure AI Search
   - Upload your document chunks with embeddings
   - Configure vector search settings

## Step 3: Test Your Azure AI Search Integration

Now you can test your Azure AI Search integration:

1. Run a test query:
   ```bash
   python scripts/test_azure_search.py --query "What is the policy on climate change?"
   ```

2. Or use the interactive CLI with Azure AI Search:
   ```bash
   python scripts/rag_cli.py --azure
   ```

## Cost Management Tips

### Azure AI Search

- **Basic tier** ($0.269/hour) is the least expensive option for development
- For maximum cost savings during development:
  - Create the resource only when you need it for testing
  - Delete the resource when not in use
  - Basic tier allows up to 2 GB of storage (sufficient for testing)

### Data Transfer

- All the queries run locally first to generate embeddings, then only send the embeddings to Azure
- This minimizes data transfer costs

### Shutting Down Resources

When not actively developing or testing:

1. Go to your Resource Group in the Azure Portal
2. Select the Azure AI Search resource
3. Click "Delete" to completely remove it (recommended for maximum cost savings)
   - OR -
4. If you need to preserve your index, consider migrating to Free tier by:
   - Exporting your index data
   - Creating a new Free tier resource (limited to 3 indexes, 50 MB total)
   - Reimporting essential data

## Next Steps

After you've verified that Azure AI Search is working correctly, you can:

1. Set up Azure OpenAI Service for embedding generation and response generation
2. Implement authentication and usage tracking
3. Prepare for production deployment

For additional cost savings, consider using:
- Tiered pricing based on usage patterns
- Reserved capacity for production workloads
- Azure Free tier services where possible