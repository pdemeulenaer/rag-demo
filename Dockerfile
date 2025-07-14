# ===========================
#  🚀 Stage 1: Builder
# ===========================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Enable bytecode compilation and Python optimization
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONOPTIMIZE=1
ENV UV_LINK_MODE=copy

# Set Python path to include the src directory for imports
# ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Copy only dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# # Install dependencies into .venv (cached)
# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv venv .venv && \
#     uv pip install --no-deps . && \
#     uv sync --frozen    

# Clean up unneeded stuff in .venv
RUN rm -rf /app/.venv/lib/python*/site-packages/tests && \
    find /app/.venv -name "*.pyc" -delete && \
    find /app/.venv -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app/.venv -name "*.egg-info" -type d -exec rm -rf {} +
    # find /app/.venv -name "*.egg-info" -type d -exec rm -rf {} + && # \
    # find /app/.venv -name "*.dist-info" -type d -exec rm -rf {} +

# ===========================
#  📦 Stage 2: Final Image
# ===========================
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# # Install only required system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation and Python optimization
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONOPTIMIZE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

# Set Python path to include the src directory for imports
# ENV PYTHONPATH="/app/src:$PYTHONPATH"
# ENV PYTHONPATH="/app/src:${PYTHONPATH}"

# Copy only the installed virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy the rest of the application code
# COPY . .
COPY src/ ./src/
COPY config.yaml ./config.yaml

# Pre-compile Python files to bytecode for startup performance
RUN python -m compileall ./src

# Create non-root user and set permissions
RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port for Streamlit
EXPOSE 8501

# Command to run the Streamlit app
# CMD ["poetry", "run", "streamlit", "run", "src/rag_demo/app.py", "--server.address=0.0.0.0"]
CMD ["/app/.venv/bin/streamlit", "run", "src/rag_demo/app.py", "--server.address=0.0.0.0"]
