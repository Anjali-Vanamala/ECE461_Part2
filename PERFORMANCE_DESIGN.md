# Performance Design Choices

## Component Selection

We selected **ECS/Fargate over Lambda** for the backend to support long-running processes, consistent performance for artifact processing, and better resource control. For storage, **S3 was chosen over RDS** to efficiently handle large binary artifact files (models, datasets) with versioning and lifecycle management. The frontend uses **AWS Amplify instead of basic S3 static hosting** to leverage built-in CDN distribution, automatic caching, and optimized build pipelines that cache `node_modules` and Next.js build artifacts.

## Performance Optimizations & Configuration

In-memory caching is implemented for expensive metric calculations (size scores, license scores) to avoid redundant API calls to HuggingFace and GitHub. ECS autoscaling is configured via the AWS Console (ECS → Service → Auto Scaling) with CPU utilization thresholds (scale at 70%, scale-in at 30% for 5 minutes) and task limits (1-5 tasks). API Gateway throttling can be configured in the API Gateway console (Throttle settings: 100 requests/second default rate, 200 burst capacity). Amplify build caching is automatically configured via `amplify.yml` to cache `node_modules` and `.next/cache` directories, reducing build times on subsequent deployments. Task resource allocation (512 CPU units, 1024 MB memory) is configured in the ECS task definition JSON file.
