# Content Engine

AI-powered content generation and management system for the Autonomous Company OS. This engine handles content creation, SEO optimization, multi-platform distribution, and performance tracking.

## Features

- **AI Content Generation** - GPT-4 powered content creation
- **SEO Optimization** - Automated SEO analysis and optimization
- **Multi-Platform Distribution** - Publish to multiple platforms automatically
- **Content Calendar** - Plan and schedule content in advance
- **Performance Tracking** - Monitor content performance metrics
- **Content Repurposing** - Automatically repurpose content for different formats
- **A/B Testing** - Test content variants for optimization
- **Analytics Dashboard** - Content performance insights

## Architecture

```
┌─────────────┐    Topics    ┌──────────────┐
│   All       │ ────────────> │  Content     │
│  Sources    │               │  Ingestion   │
└─────────────┘               └──────┬───────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼──────┐ ┌────▼────┐ ┌────▼──────┐
            │   AI Content │ │  SEO    │ │ Calendar   │
            │   Generator   │ │ Engine  │ │  Manager   │
            └──────────────┘ └─────────┘ └───────────┘
                    │                │                │
                    └────────────────┼────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │      Distribution Manager       │
                    │  (Multi-platform publishing)   │
                    └─────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼──────┐ ┌────▼────┐ ┌────▼──────┐
            │   Repurpose  │ │ A/B     │ │ Analytics  │
            │   Engine     │ │ Testing  │ │  Engine    │
            └──────────────┘ └─────────┘ └───────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL (for content data)
- Redis (for caching and queues)
- OpenAI API key (for AI content generation)

### Local Development

```bash
# Clone repository
git clone https://github.com/autonomous-company/content-engine.git
cd content-engine

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the service
uvicorn app.main:app --reload --port 8040
```

### Docker Deployment

```bash
# Build and start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f content-engine

# Stop services
docker-compose down
```

## Configuration

Configuration is managed via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://localhost/content` | PostgreSQL connection URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `AI_MODEL` | `gpt-4` | AI model for content generation |

## API Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /` - Service information

### Content Generation
- `POST /content/generate` - Generate content
- `POST /content/repurpose` - Repurpose content
- `GET /content/{content_id}` - Get content details
- `GET /content` - List content

### SEO Optimization
- `POST /seo/optimize` - Optimize content for SEO
- `POST /seo/analyze` - Analyze content SEO
- `GET /seo/keywords/{content_id}` - Get content keywords

### Content Calendar
- `POST /calendar/create` - Create calendar entry
- `GET /calendar/{date}` - Get calendar entries
- `GET /calendar/upcoming` - Get upcoming content

### Distribution
- `POST /distribution/publish` - Publish content
- `POST /distribution/schedule` - Schedule distribution
- `GET /distribution/status/{content_id}` - Get distribution status

### Analytics
- `GET /analytics/performance` - Get content performance
- `GET /analytics/engagement` - Get engagement metrics
- `GET /analytics/trending` - Get trending content

## Usage Examples

### Generate Content

```python
import httpx

async def generate_content():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8040/content/generate",
            json={
                "content_type": "blog_post",
                "topic": "AI-powered content marketing",
                "target_audience": "marketers",
                "tone": "professional",
                "length": 1000
            }
        )
        return response.json()
```

### Optimize for SEO

```python
async def optimize_seo():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8040/seo/optimize",
            json={
                "content_id": "content_123",
                "target_keywords": ["AI marketing", "content automation"]
            }
        )
        return response.json()
```

### Publish Content

```python
async def publish_content():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8040/distribution/publish",
            json={
                "content_id": "content_123",
                "platforms": ["blog", "linkedin", "twitter"],
                "schedule_immediately": True
            }
        )
        return response.json()
```

## Content Types

- **Blog Posts** - Long-form articles and blog content
- **Social Media** - Short-form social content
- **Email Copy** - Email subject lines and body copy
- **Landing Pages** - Conversion-focused landing page copy
- **Video Scripts** - Video content scripts
- **Product Descriptions** - E-commerce product descriptions

## SEO Features

- **Keyword Analysis** - Identify and optimize for target keywords
- **Readability Score** - Assess content readability
- **Meta Tags** - Generate optimized meta titles and descriptions
- **Internal Linking** - Suggest internal linking opportunities
- **Content Structure** - Optimize heading structure and formatting

## Integration with Other Engines

### Marketing Automation
- Provides content for campaigns
- Tracks content performance in campaigns
- Optimizes content based on campaign results

### Analytics Engine
- Provides content performance data
- Tracks content engagement metrics
- Generates content insights

### Funnel Automation
- Provides content for funnel stages
- Optimizes content for conversion
- Tracks content impact on funnels

## Monitoring

### Metrics
- Content generation volume
- SEO scores and rankings
- Content engagement rates
- Distribution success rates
- Content conversion impact

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
