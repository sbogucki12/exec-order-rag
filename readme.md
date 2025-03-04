# Executive Orders RAG Chatbot

A Retrieval Augmented Generation (RAG) system for accessing and querying information about executive orders and government guidance documents.

[![Day 5](https://img.youtube.com/vi/QjNIThQj2b8/0.jpg)](https://youtu.be/QjNIThQj2b8)

## Development Timeline 

### Day 5
- **Current functionality**: Integrated Stripe payment system, updated admin dashboard, and improved frontend user experience.
- **Accomplishments**:
  - Starting implementing Stripe payment processing for premium subscriptions
  - Added secure password protection to the admin dashboard
  - Created new React components for subscription management
  - Added chat history and account management pages
  - Implemented user experience improvements (clear chat, navigation)
  - Created subscription success and cancellation flows
  - Updated user schema to track subscription status
  - Added admin dashboard tab for subscription management
  - Made the admin dashboard independently accessible via direct URL
  - Ensured proper state persistence with localStorage
- **Next**:
  - Deploy to production environment
  - Set up webhook handling for Stripe events
  - Implement email notifications for subscription changes
  - Add more detailed analytics for premium users

### Day 4
- **Current functionality**: Separated API backend and React frontend, implemented authentication and subscription system.
- **Accomplishments**:
  - Created a Flask API backend separate from the Streamlit interface
  - Built a clean, minimal React frontend with user authentication
  - Implemented subscription tiers (free/premium)
  - Set up Docker configuration for seamless deployment
  - Created authentication endpoints (register, login)
  - Added usage limiting integration with the API
  - Established a foundation for the payment system

### Day 3
- **Current functionality**: Enhanced admin capabilities, fixed prompt limitations, added usage statistics.
- **Accomplishments**:
  - Created a dedicated admin dashboard separate from the main UI
  - Successfully implemented prompt limitations to control usage
  - Added privacy-focused user statistics with masked IP display
  - Added usage data visualization with charts
  - Fixed various bugs in the usage tracking system

### Day 2 
- **Current functionality**: Full chat functionality with executive orders
- **Currently missing**: Limit on number of prompts. 
- **Next**: 
  - Limit number of prompts. 
  - Move admin features to a separate protected admin console. 
  - Add authentication. 

### Day 1
- **Current functionality**: Runs locally, queries Executive Orders, provides relevant EO responsive to each prompt. 
- **Currently missing**: Chat functionality (isn't integrated with LLM).
- **Next**: 
  - Integrate LLM for chat functionality. 
  - Integrate with Azure AI. 
  - Add authentication. 


## Features

- **Document Processing**: Process executive orders and guidance documents in various formats (PDF, DOCX, TXT, HTML)
- **Vector Search**: Find relevant information using semantic similarity
- **Local Testing**: Develop and test locally before deploying to Azure
- **Command-line Interface**: Interactive CLI for testing the RAG system
- **Web Interface**: Modern React-based UI with Streamlit admin dashboard
- **Authentication System**: User registration and login functionality
- **Subscription Tiers**: Free tier with usage limits and premium tier with unlimited access
- **Payment Processing**: Stripe integration for subscription management
- **Admin Dashboard**: Password-protected admin panel for managing settings and viewing statistics
- **Usage Limits**: Control the number of prompts users can submit
- **Usage Analytics**: Track and visualize usage statistics with privacy protection
- **Docker Support**: Containerized deployment for both frontend and backend

## Project Structure

```
azure-rag-chatbot/
├── .env                     # Environment variables (API keys, etc.)
├── .env.template            # Template for environment variables
├── api.py                   # Flask API for the React frontend
├── api_chatbot.py           # API-compatible chatbot implementation
├── config.py                # Configuration settings
├── integration.py           # Integration between Streamlit and API
├── requirements.txt         # Dependencies
├── README.md                # Project documentation
├── testing_guide.md         # Guide for testing the application
├── azure_setup.md           # Azure setup documentation
├── .streamlit/              # Streamlit configuration
│   └── config.toml
├── docker/                  # Docker configuration
│   ├── backend/
│   │   └── DockerFile       # Backend Docker configuration
│   ├── frontend/
│   │   ├── DockerFile       # Frontend Docker configuration
│   │   └── nginx.conf       # Nginx configuration for React
│   └── docker-compose.yaml  # Docker Compose configuration
├── frontend/                # React frontend
│   ├── public/              # Public assets
│   │   ├── favicon.ico
│   │   ├── index.html
│   │   ├── logo192.png
│   │   ├── logo512.png
│   │   └── robots.txt
│   ├── src/                 # Source code
│   │   ├── components/      # React components
│   │   │   ├── ChatMessage.js
│   │   │   ├── LoginModal.js
│   │   │   ├── UserMenu.js
│   │   │   ├── PaymentForm.js
│   │   │   ├── SubscriptionStatus.js
│   │   │   ├── SubscriptionSuccess.js
│   │   │   └── SubscriptionCancel.js
│   │   ├── services/        # API services
│   │   │   └── api.js       # API integration
│   │   ├── app.css          # Application styles
│   │   ├── app.js           # Main application component
│   │   └── index.js         # Entry point
│   ├── .gitignore
│   └── README.md            # Frontend documentation
├── pages/                   # Previous Streamlit pages (backup)
│   └── 01_Admin_Dashboard.py.bak
├── scripts/                 # Utility scripts
│   ├── admin_auth.py        # Admin authentication module
│   ├── admin_dashboard.py   # Streamlit admin dashboard
│   ├── run_admin.py         # Script to run admin dashboard independently
│   ├── run_api.py           # Script to run the API server
│   ├── ingest.py            # Document ingestion script
│   ├── embed.py             # Embedding generation script
│   ├── create_index.py      # Index creation script
│   ├── search.py            # Vector search script
│   ├── rag_cli.py           # Command-line interface for RAG
│   └── ... 
├── src/                     # Core functionality modules
│   ├── payment_integration.py     # Stripe payment integration
│   ├── document_processor.py      # Document chunking and processing
│   ├── embeddings.py              # Embedding generation
│   ├── vector_store.py            # Vector search functionality
│   ├── rag.py                     # Core RAG functionality
│   ├── llm.py                     # LLM integration
│   ├── llm_factory.py             # Factory for creating LLM instances
│   ├── usage_config.py            # Configuration for usage limits
│   ├── usage_integration.py       # Integration of usage limiting with UI
│   ├── usage_limiter.py           # Core usage limiting functionality
│   └── admin_ips.txt              # List of admin IP addresses
└── test_docs/                     # Test documents for RAG system
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+
- Docker and Docker Compose (for containerized deployment)
- Azure Subscription (for production deployment)
- Stripe Account (for payment processing)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd azure-rag-chatbot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys and configuration
   ```

5. Set up the frontend:
   ```bash
   cd frontend
   npm install
   ```

### Running the Application Locally

1. Start the API server:
   ```bash
   python scripts/run_api.py
   ```

2. In a separate terminal, start the React frontend:
   ```bash
   cd frontend
   npm start
   ```

3. For the admin dashboard, run:
   ```bash
   python -m streamlit run scripts/run_admin.py
   ```

### Stripe Integration Setup

1. Create a Stripe account at [stripe.com](https://stripe.com)
2. Set up a subscription product and pricing plan in the Stripe dashboard
3. Add the following environment variables to your `.env` file:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLIC_KEY=pk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PREMIUM_PRICE_ID=price_...
   ```
4. Test the payment flow using Stripe test cards (e.g., 4242 4242 4242 4242)

### Running with Docker

```bash
docker-compose -f docker/docker-compose.yaml up
```

## Using the RAG System

Use the command-line interface for testing:

```bash
python scripts/rag_cli.py --index data/vector_store.json
```

Or access the web application:

1. API and frontend: http://localhost:3000
2. Admin dashboard: http://localhost:8501 (password protected)

### Authentication

The system supports two user tiers:
- **Free Tier**: Limited to a specific number of queries per day
- **Premium Tier**: Unlimited access via paid subscription

## Azure Integration

### Required Azure Resources

For a production deployment, the following Azure resources are needed:

- **Azure AI Search**: For vector storage and search
- **Azure OpenAI Service**: For embeddings and text generation
- **Azure AI Foundry**: For AI model hosting and management
- **Azure Storage Account**: For document storage
- **Azure App Service**: For hosting the web application

## Future Enhancements

- **Enhanced User Dashboard**: Add more detailed usage statistics for users
- **Advanced Search Features**: Filters, sorting, and faceted search
- **Document Management UI**: Interface for managing document sources
- **Email Notifications**: Send emails for subscription events and account activities
- **Mobile Optimization**: Enhance the UI for mobile devices

## Contact

[LinkedIn](https://www.linkedin.com/in/sbogucki12/)
