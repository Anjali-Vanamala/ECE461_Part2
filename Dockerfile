# syntax=docker/dockerfile:1
# TODO: Consider migrating to FastAPI + ECS if Lambda becomes limiting
# TODO: Add health check endpoint for container orchestration
# TODO: Optimize image size with multi-stage build if needed
# TODO: Add OpenAPI specification for API documentation
FROM public.ecr.aws/lambda/python:3.11

WORKDIR /var/task

# Copy source first so handler and code are available to Lambda
COPY . .

# Install runtime deps
RUN pip install --no-cache-dir -r dependencies.txt

# Default logging env for Lambda (overridable via Lambda config)
ENV LOG_LEVEL=1
ENV LOG_FILE=/tmp/error_logs.log

# Set the handler (module.function)
CMD ["lambda_handler.handler"]


