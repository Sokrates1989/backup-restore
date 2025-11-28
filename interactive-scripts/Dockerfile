# Interactive Scripts Environment Dockerfile
# This Dockerfile provides the environment to run interactive bash scripts
# It uses Alpine Linux with Docker CLI for scripts that need to interact with Docker

FROM docker:28-cli

# Install bash and dos2unix for running interactive scripts
# dos2unix helps handle Windows line ending issues
RUN apk add --no-cache bash dos2unix

# Set working directory
WORKDIR /workspace

# The scripts will be mounted and executed via docker-compose
# This is the base environment for running interactive scripts
