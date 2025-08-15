.PHONY: docker-build run-test

# Build the Docker image
docker-build:
	@docker build -t podcast-creator .

# Run the llm client test
run-test: docker-build
	@docker run -v $(CURDIR):/app podcast-creator python tests/test_llm_client.py $(topics)