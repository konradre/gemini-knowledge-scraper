# Stage 1: Node.js for Claude Code
FROM node:20 AS node-base

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code@latest

# Stage 2: Python runtime
FROM python:3.11-slim

# Copy Claude Code binary from stage 1
COPY --from=node-base /usr/local/bin/claude /usr/local/bin/claude
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy actor code (including .claude/ directory)
COPY . ./

# Run actor via proper entry point
CMD ["python", "__main__.py"]
