# Docker Multi-Architecture Deployment with GitHub Actions

This document explains how to set up automated Docker image builds for both x86_64 and ARM64 architectures using GitHub Actions and DockerHub.

> **📋 For CapRover Deployment**: See [CAPROVER_DEPLOYMENT.md](./CAPROVER_DEPLOYMENT.md) for specific instructions on deploying to CapRover with separate Redis instances.

## Prerequisites

1. A DockerHub account
2. A GitHub repository with this project
3. Admin access to the GitHub repository to configure secrets

## Setup Instructions

### 1. Create DockerHub Access Token

1. Log in to [DockerHub](https://hub.docker.com/)
2. Go to **Account Settings** → **Security**
3. Click **New Access Token**
4. Give it a descriptive name (e.g., "GitHub Actions")
5. Select **Read, Write, Delete** permissions
6. Copy the generated token (you won't see it again)

### 2. Configure GitHub Repository Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add the following secrets:

   - **Name**: `DOCKERHUB_USERNAME`
     **Value**: Your DockerHub username

   - **Name**: `DOCKERHUB_TOKEN`
     **Value**: The access token you created in step 1

### 3. Update the Workflow Configuration

Edit the `.github/workflows/docker-build.yml` file and update the `IMAGE_NAME` environment variable:

```yaml
env:
  REGISTRY: docker.io
  IMAGE_NAME: your-dockerhub-username/registration-retrieval  # Replace with your actual DockerHub username
```

Replace `your-dockerhub-username` with your actual DockerHub username.

## How It Works

### Workflow Triggers

The workflow runs automatically on:
- **Push to main/master branch**: Builds and pushes images with `latest` tag
- **Push tags starting with 'v'**: Builds and pushes images with version tags (e.g., `v1.0.0`)
- **Pull requests**: Builds images but doesn't push them (for testing)

### Multi-Architecture Support

The workflow builds images for:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)

### Image Tags

The workflow automatically creates the following tags:
- `latest` (for main/master branch)
- Branch name (for feature branches)
- Version tags (for git tags like `v1.0.0`, `v1.0`, `v1`)
- PR number (for pull requests)

## Usage Examples

### Triggering a Build

1. **Latest build**: Push to main/master branch
   ```bash
   git push origin main
   ```

2. **Version release**: Create and push a version tag
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **Feature testing**: Create a pull request (builds but doesn't push)

### Using the Images

Once built, you can pull and use the images:

```bash
# Pull latest version
docker pull your-dockerhub-username/registration-retrieval:latest

# Pull specific version
docker pull your-dockerhub-username/registration-retrieval:v1.0.0

# Run the container
docker run -p 8000:8000 your-dockerhub-username/registration-retrieval:latest
```

### Multi-Architecture Usage

The images support both architectures automatically:

```bash
# On x86_64 systems
docker pull your-dockerhub-username/registration-retrieval:latest

# On ARM64 systems (Apple Silicon, ARM servers)
docker pull your-dockerhub-username/registration-retrieval:latest
```

Docker will automatically pull the correct architecture for your system.

## Workflow Features

### Caching
- Uses GitHub Actions cache to speed up builds
- Caches Docker layers between builds

### Security
- Only pushes images on main branch and tags (not on PRs)
- Uses secure token authentication
- Generates build attestations for supply chain security

### Optimization
- Uses Docker Buildx for advanced build features
- Builds both architectures in parallel
- Optimized layer caching

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are set correctly
   - Ensure the DockerHub token has write permissions

2. **Image Name Conflicts**
   - Make sure the `IMAGE_NAME` in the workflow matches your DockerHub repository
   - Repository names must be lowercase

3. **Build Failures**
   - Check the Actions tab in your GitHub repository for detailed logs
   - Ensure your Dockerfile works with both x86_64 and ARM64 architectures

4. **Attestation Errors**
   - If you see "Failed to get ID token" errors, the workflow will continue without attestations
   - This is normal for some repository configurations and doesn't affect the Docker build
   - Attestations provide additional security metadata but are optional

5. **Permission Errors**
   - Ensure your repository has the necessary permissions enabled
   - Go to Settings → Actions → General → Workflow permissions
   - Select "Read and write permissions" if builds fail with permission errors

### Viewing Build Status

1. Go to your GitHub repository
2. Click the **Actions** tab
3. Select the **Build and Push Multi-Architecture Docker Images** workflow
4. View individual build runs and their logs

## Advanced Configuration

### Custom Build Arguments

To pass build arguments to your Docker build, modify the workflow:

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: ${{ github.event_name != 'pull_request' }}
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    build-args: |
      BUILD_VERSION=${{ github.sha }}
      BUILD_DATE=${{ github.event.head_commit.timestamp }}
```

### Additional Platforms

To support more architectures, update the platforms list:

```yaml
platforms: linux/amd64,linux/arm64,linux/arm/v7
```

Note: Additional platforms may increase build time significantly.

## Environment Variable Configuration

Your application uses these key environment variables for Redis connection:

```bash
# Redis Configuration (required)
REDIS_URL=redis://localhost:6379/0

# Alternative formats:
REDIS_URL=redis://username:password@host:port/database
REDIS_URL=redis://srv-captain--redis-app:6379  # CapRover internal DNS
```

### Platform-Specific Redis URLs

| Platform | Redis URL Format | Example |
|----------|------------------|---------|
| **Docker Compose** | `redis://service-name:6379` | `redis://redis:6379` |
| **CapRover** | `redis://srv-captain--app-name:6379` | `redis://srv-captain--registration-redis:6379` |
| **Kubernetes** | `redis://service-name.namespace:6379` | `redis://redis.default:6379` |
| **Local Development** | `redis://localhost:6379` | `redis://localhost:6379/0` |
| **Redis Cloud** | `redis://user:pass@host:port` | `redis://user:pass@redis-12345.cloud.redislabs.com:12345` |

## Security Best Practices

1. **Use Access Tokens**: Never use your DockerHub password in GitHub secrets
2. **Limit Token Scope**: Create tokens with minimal required permissions
3. **Regular Rotation**: Rotate access tokens periodically
4. **Monitor Usage**: Check DockerHub for unexpected image pulls/pushes

## Cost Considerations

- GitHub Actions provides free minutes for public repositories
- Private repositories have limited free minutes
- DockerHub has rate limits for anonymous pulls
- Consider using GitHub Container Registry (ghcr.io) as an alternative