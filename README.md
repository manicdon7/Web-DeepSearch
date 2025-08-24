# Web-DeepSearch API

A powerful FastAPI-based web research agent that searches multiple web sources, scrapes content from relevant pages, and synthesizes comprehensive answers using AI. This tool eliminates the need to manually browse through multiple websites by providing synthesized answers from across the web.

## 🚀 Features

- **Multi-Source Research**: Searches and scrapes content from multiple web sources simultaneously
- **AI-Powered Synthesis**: Uses advanced AI to synthesize information from scraped sources into coherent answers
- **Unlimited Sources**: No artificial limits on the number of sites to search - scrapes as many relevant sources as possible
- **Smart Filtering**: Automatically filters out low-quality and blocked domains
- **FastAPI Backend**: High-performance REST API with automatic documentation
- **Health Monitoring**: Built-in `/ping` endpoint for health checks

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Web-DeepSearch
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

#### Local Development
```bash
# Run with uvicorn for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production with Vercel
This project is configured for Vercel deployment. Simply push to your GitHub repository connected to Vercel.

## 📡 API Endpoints

### 1. Query Endpoint
**POST** `/query/`

Submit a search query and receive a synthesized answer from multiple web sources.

**Request Body:**
```json
{
  "query": "What are the latest developments in quantum computing?"
}
```

**Response:**
```json
{
  "answer": "A comprehensive synthesized answer based on multiple web sources...",
  "sources_used": [
    "https://example.com/article1",
    "https://example.com/article2",
    "https://example.com/article3"
  ]
}
```

### 2. Health Check
**GET** `/ping`

Simple health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "pong"
}
```

### 3. Root Endpoint
**GET** `/`

Welcome message with API information.

**Response:**
```json
{
  "message": "Welcome to the Multi-Source Research Agent API!"
}
```

## 🧪 Testing the API

### Using curl
```bash
# Health check
curl http://localhost:8000/ping

# Query endpoint
curl -X POST "http://localhost:8000/query/" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is machine learning?"}'
```

### Using Python requests
```python
import requests

response = requests.post(
    "http://localhost:8000/query/",
    json={"query": "Latest AI breakthroughs 2024"}
)
print(response.json())
```

## 📁 Project Structure

```
Web-DeepSearch/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application and endpoints
│   ├── model.py         # Pydantic models for request/response
│   ├── search_client.py # Web search and scraping logic
│   ├── scraper.py       # Web scraping utilities
│   ├── agent.py         # AI synthesis logic
│   └── config.py        # Configuration settings
├── requirements.txt     # Python dependencies
├── vercel.json         # Vercel deployment configuration
├── .gitignore          # Git ignore rules (includes venv/)
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```bash
# Optional: Add your API keys here if needed
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Domain Filtering
The application automatically filters out certain domains (social media, video platforms, etc.) to ensure quality results. You can modify the `DOMAIN_BLOCKLIST` in `app/search_client.py` to customize this.

## 🚀 Deployment Options

### Vercel (Recommended)
1. Push your code to GitHub
2. Import the repository in Vercel
3. Deploy automatically with zero configuration

### Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Heroku
```bash
heroku create your-app-name
git push heroku main
```

## 📝 Usage Examples

### Research Assistant
Perfect for:
- Academic research across multiple sources
- Market analysis and competitive intelligence
- News aggregation and summary
- Technical documentation synthesis
- Fact-checking across multiple sources

### Integration Examples
```javascript
// Frontend integration
const researchQuery = async (query) => {
  const response = await fetch('/query/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  return response.json();
};
```

## ⚠️ Important Notes

- **Rate Limiting**: Be mindful of API rate limits when making frequent requests
- **Content Quality**: The AI synthesis quality depends on the scraped content quality
- **Network Dependency**: Requires active internet connection for web scraping
- **Blocked Domains**: Some websites may block scraping - these are automatically skipped

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with clear description

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🔗 Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vercel Deployment Guide](https://vercel.com/docs)
- [Project Repository](https://github.com/manicdon7/Web-DeepSearch)

---

For support or questions, please open an issue in the GitHub repository.