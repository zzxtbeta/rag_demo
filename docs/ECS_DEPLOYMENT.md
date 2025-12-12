# ECS Deployment Guide for Gravaity Agent

This guide explains how to package and deploy your LangGraph agent to AWS ECS.

## Prerequisites

- Docker installed locally
- AWS CLI configured with appropriate credentials
- AWS ECR repository created
- ECS cluster and task definition setup
- PostgreSQL and Redis instances (managed or self-hosted)

## Step 1: Build Docker Image Locally

### Basic Build
```bash
langgraph build -t gravaity-agent:latest
```

### Build for Specific Platform (Recommended for ECS)
```bash
langgraph build --platform linux/amd64 -t gravaity-agent:v1.0.0
```

### Build with Custom Config
```bash
langgraph build -t gravaity-agent:v1.0.0 -c langgraph.json --platform linux/amd64
```

## Step 2: Test Locally with Docker Compose

Before deploying to ECS, test your image locally:

```bash
# Build the image first
langgraph build -t gravaity-agent:latest

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f langgraph-api

# Test the API
curl http://localhost:8000/docs

# Cleanup
docker-compose down
```

## Step 3: Push to AWS ECR

### 1. Create ECR Repository (if not exists)
```bash
aws ecr create-repository \
  --repository-name gravaity-agent \
  --region us-east-1
```

### 2. Login to ECR
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### 3. Tag Image for ECR
```bash
docker tag gravaity-agent:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/gravaity-agent:latest

docker tag gravaity-agent:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/gravaity-agent:v1.0.0
```

### 4. Push to ECR
```bash
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/gravaity-agent:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/gravaity-agent:v1.0.0
```

## Step 4: Configure ECS Task Definition

Create or update your ECS task definition with:

### Container Image
```json
{
  "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/gravaity-agent:v1.0.0",
  "portMappings": [
    {
      "containerPort": 8000,
      "hostPort": 8000,
      "protocol": "tcp"
    }
  ]
}
```

### Required Environment Variables

**LangGraph Runtime (Required):**
- `REDIS_URL` - Redis connection URI
  - Format: `redis://:password@host:6379/2`
  - Use AWS ElastiCache or self-hosted Redis
  
- `DATABASE_URI` - PostgreSQL connection URI
  - Format: `postgresql://user:password@host:5432/database?sslmode=disable`
  - Use AWS RDS or self-hosted PostgreSQL

- `LANGSMITH_API_KEY` - Your LangSmith API key (optional but recommended)

**Application Configuration:**
- `CHAT_MODEL` - Default: `qwen-plus-latest`
- `DASHSCOPE_API_KEY` - Alibaba DashScope API key
- `DASHSCOPE_BASE_URL` - Default: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `OPENAI_EMBEDDINGS_API_KEY` - OpenAI embeddings API key
- `EMBEDDINGS_MODEL` - Default: `text-embedding-v4`

**Vector Store Configuration:**
- `POSTGRES_CONNECTION_STRING` - Same as `DATABASE_URI` or separate PostgreSQL instance
- `VECTOR_COLLECTION` - Default: `bp_pdf`
- `CHUNK_SIZE` - Default: `1000`
- `CHUNK_OVERLAP` - Default: `200`
- `RETRIEVER_TOP_K` - Default: `4`

**Project Search (if enabled):**
- `PROJECT_SEARCH_ENABLED` - Set to `true` to enable
- `PROJECT_SEARCH_API_URL` - Your project search API URL
- `PROJECT_SEARCH_API_USERNAME` - API username
- `PROJECT_SEARCH_API_PASSWORD` - API password

**Optional Features:**
- `RERANK_ENABLED` - Default: `false`
- `RERANK_MODEL` - Default: `qwen3-rerank`
- `RERANK_TOP_N` - Default: `3`
- `REDIS_STREAM_ENABLED` - Default: `false`
- `STREAM_TTL_SECONDS` - Default: `3600`
- `STREAM_MAX_LENGTH` - Default: `1000`
- `WORKFLOW_TIMEOUT_SECONDS` - Default: `300`

### Use AWS Secrets Manager (Recommended)

For sensitive variables, use AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name gravaity-agent-secrets \
  --secret-string '{
    "DASHSCOPE_API_KEY": "your-key",
    "OPENAI_EMBEDDINGS_API_KEY": "your-key",
    "LANGSMITH_API_KEY": "your-key"
  }'
```

Then reference in task definition:
```json
{
  "secrets": [
    {
      "name": "DASHSCOPE_API_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:gravaity-agent-secrets:DASHSCOPE_API_KEY::"
    }
  ]
}
```

## Step 5: Deploy to ECS

### Using AWS Console
1. Go to ECS → Clusters → Your Cluster
2. Create new Task Definition
3. Set container image to your ECR image URL
4. Configure environment variables
5. Create/Update Service
6. Deploy

### Using AWS CLI
```bash
aws ecs update-service \
  --cluster your-cluster-name \
  --service your-service-name \
  --force-new-deployment \
  --region us-east-1
```

## Step 6: Verify Deployment

### Check Service Health
```bash
aws ecs describe-services \
  --cluster your-cluster-name \
  --services your-service-name \
  --region us-east-1
```

### View Logs
```bash
# Get task ID
TASK_ID=$(aws ecs list-tasks \
  --cluster your-cluster-name \
  --service-name your-service-name \
  --region us-east-1 \
  --query 'taskArns[0]' \
  --output text)

# View logs
aws logs tail /ecs/gravaity-agent --follow
```

### Test API Endpoint
```bash
curl http://your-ecs-instance:8000/docs
```

## Troubleshooting

### Container Won't Start
- Check CloudWatch logs for error messages
- Verify all required environment variables are set
- Ensure database and Redis are accessible from ECS

### Database Connection Issues
- Verify security groups allow traffic from ECS to RDS/PostgreSQL
- Check connection string format
- Ensure database exists and user has permissions

### Out of Memory
- Increase task memory in ECS task definition
- Check for memory leaks in logs
- Monitor with CloudWatch

### Performance Issues
- Increase task CPU allocation
- Scale horizontally with multiple tasks
- Use load balancer for distribution

## Monitoring

### CloudWatch Metrics
Monitor these key metrics:
- CPU utilization
- Memory utilization
- Network in/out
- Task count

### LangSmith Integration
Set `LANGSMITH_API_KEY` to automatically trace all requests in LangSmith for debugging and monitoring.

## Scaling

### Horizontal Scaling
Use ECS Service Auto Scaling:
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/your-cluster/your-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10
```

### Vertical Scaling
Update task definition with more CPU/memory and force new deployment.

## Security Best Practices

1. **Use AWS Secrets Manager** for sensitive data
2. **Enable VPC** for network isolation
3. **Use IAM roles** for task execution
4. **Enable logging** to CloudWatch
5. **Use HTTPS** for external communication
6. **Regularly update** base images and dependencies
7. **Scan images** for vulnerabilities with ECR image scanning

## Rollback

If deployment fails:
```bash
aws ecs update-service \
  --cluster your-cluster-name \
  --service your-service-name \
  --task-definition your-service:PREVIOUS_VERSION \
  --region us-east-1
```

## Additional Resources

- [LangGraph CLI Documentation](https://docs.langchain.com/langsmith/cli)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS ECR Documentation](https://docs.aws.amazon.com/ecr/)
