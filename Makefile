.PHONY: docker-build run-test run-bash

# Build the Docker image
docker-build:
	@docker build -t podcast-creator .

# Run the test (automatically builds image if needed)
run-test: docker-build
	@docker \
	run \
	--rm \
	-v $(CURDIR)/tmp:/app/tmp \
	-e PYTHONPATH=/app \
	-e DEBUG=True \
	-e LOGLEVEL=DEBUG \
	podcast-creator \
	python tests/test_llm_client.py $(TOPICS)

# Access the docker container
run-bash: docker-build
	@docker \
	run \
	--rm \
	-it \
	-v $(CURDIR)/tmp:/app/tmp \
	-e PYTHONPATH=/app \
	-e DEBUG=True \
	-e LOGLEVEL=DEBUG \
	podcast-creator \
	bash