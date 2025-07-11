# Docker Multi-Architecture Setup Checklist

Follow this checklist to set up automated Docker builds for x86_64 and ARM64 architectures.

## ✅ Pre-Setup Checklist

- [ ] DockerHub account created
- [ ] GitHub repository with admin access
- [ ] Project files committed to repository

## ✅ DockerHub Configuration

- [ ] Log in to [DockerHub](https://hub.docker.com/)
- [ ] Navigate to **Account Settings** → **Security**
- [ ] Create **New Access Token** with name "GitHub Actions"
- [ ] Select **Read, Write, Delete** permissions
- [ ] Copy the generated token (save it securely)

## ✅ GitHub Repository Setup

- [ ] Go to repository **Settings** → **Secrets and variables** → **Actions**
- [ ] Add secret: `DOCKERHUB_USERNAME` = your DockerHub username
- [ ] Add secret: `DOCKERHUB_TOKEN` = the access token from above

## ✅ Workflow Configuration

- [ ] Edit `.github/workflows/docker-build.yml`
- [ ] Update `IMAGE_NAME` environment variable:
  ```yaml
  IMAGE_NAME: your-dockerhub-username/registration-retrieval
  ```
- [ ] Replace `your-dockerhub-username` with your actual username

## ✅ Testing

- [ ] Run the validation workflow manually:
  1. Go to **Actions** tab in GitHub
  2. Select "Validate Docker Setup"
  3. Click "Run workflow"
- [ ] Check that validation passes
- [ ] Create a test commit to trigger the main workflow
- [ ] Verify images are built and pushed to DockerHub

## ✅ Verification

- [ ] Check DockerHub repository for new images
- [ ] Verify both `linux/amd64` and `linux/arm64` architectures are present
- [ ] Test pulling and running the image locally:
  ```bash
  docker pull your-dockerhub-username/registration-retrieval:latest
  docker run -p 8000:8000 your-dockerhub-username/registration-retrieval:latest
  ```

## 🚀 Usage

### Trigger Builds

- **Latest build**: Push to main/master branch
- **Version release**: Create and push version tag (e.g., `v1.0.0`)
- **Testing**: Create pull request (builds but doesn't push)

### Image Tags Available

- `latest` (main/master branch)
- `v1.0.0` (version tags)
- `main` or `master` (branch name)
- `pr-123` (pull request number)

## 🔧 Troubleshooting

If builds fail, check:

1. **Secrets are configured correctly**
   - DOCKERHUB_USERNAME matches your DockerHub username exactly
   - DOCKERHUB_TOKEN is valid and has write permissions

2. **Image name is correct**
   - Must be lowercase
   - Format: `username/repository-name`

3. **DockerHub repository exists**
   - Repository will be created automatically on first push
   - Or create it manually in DockerHub

4. **Dockerfile works with multi-arch**
   - Test locally with: `docker buildx build --platform linux/amd64,linux/arm64 .`

## 📚 Additional Resources

- [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) - Detailed documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/)
- [DockerHub Documentation](https://docs.docker.com/docker-hub/)