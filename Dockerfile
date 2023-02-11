# syntax=docker/dockerfile:1
FROM python:3.10-slim
WORKDIR /usr/src/wh00t_server

# Update apt-get
RUN apt-get update -y

# Install poetry
ENV POETRY_VERSION=1.2.0
RUN apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | POETRY_VERSION=${POETRY_VERSION} python3 -
ENV PATH="/root/.local/bin:$PATH"

# Install project dependencies via poetry
COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install

# Set environmental variables for application
ENV SERVER_PORT=3001

# Copy application
COPY . .

# Run application
EXPOSE 3001
CMD ["poetry", "run", "python", "wh00t_server/wh00t_server.py"]
