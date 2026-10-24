  # 1. Build the image with build arguments
  docker build \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg BUILD_COMMIT=$(git rev-parse --short HEAD) \
    -t spiderfoot:latest \
    .

  # 2. Tag for GCloud Artifact Registry
  # Replace with your actual values:
  #   REGION: e.g., us-central1, us-east1, etc.
  #   PROJECT_ID: your GCP project ID
  #   REPOSITORY: your artifact registry repository name
  docker tag spiderfoot:latest \
    REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/spiderfoot:latest

  # Optional: Also tag with version/commit
  docker tag spiderfoot:latest \
    REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/spiderfoot:$(git rev-parse --short HEAD)

  # 3. Configure Docker authentication for GCloud (if not already done)
  gcloud auth configure-docker REGION-docker.pkg.dev

  # 4. Push to Artifact Registry
  docker push REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/spiderfoot:latest
  docker push REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/spiderfoot:$(git rev-parse --short HEAD)

  Example with actual values:
  # If your setup is:
  # Region: us-central1
  # Project: my-project-123
  # Repository: spiderfoot-repo
BUILD_DATE=$(date -u +'%Y%m%dt%H%M%S') \
&& \
BUILD_COMMIT=$(git rev-parse --short HEAD) \
&& \
BUILD_VERS=v$BUILD_DATE---$BUILD_COMMIT \
&& \        docker build \
    --build-arg ${BUILD_DATE}\
    --build-arg ${BUILD_COMMIT}\
    -t blkc-spiderfoot:${BUILD_VERS} \
    . \
    && \          docker tag blkc-spiderfoot:${BUILD_VERS} \
    us-central1-docker.pkg.dev/intranet-of-tools/blkc-foot-enterprise/blkc-spiderfoot:${BUILD_VERS}\
    && \
    docker push us-central1-docker.pkg.dev/intranet-of-tools/blkc-foot-enterprise/blkc-spiderfoot:${BUILD_VERS}  
  gcloud auth configure-docker us-central1-docker.pkg.dev  
  
  docker tag blkc-spiderfoot:LATEST \
    us-central1-docker.pkg.dev/my-project-123/spiderfoot-repo/blkc-spiderfoot:LATEST

  gcloud auth configure-docker us-central1-docker.pkg.dev

  docker push us-central1-docker.pkg.dev/my-project-123/spiderfoot-repo/blkc-spiderfoot:LATEST

  The build includes metadata injection via BUILD_DATE and BUILD_COMMIT arguments, which gets written to
  /home/spiderfoot/BUILD_INFO in the image.
