.PHONY: lint format install-dev serve test coverage build-wheels install-wheels download-wheels-offline

install-dev:
	uv pip install -e ".[dev]" && uv pip install -e ".[test]"

format:
	uv run black --preview .

lint:
	uv run black --check .
	uv run ruff check .

serve:
	uv run server.py --reload

test:
	uv run pytest tests/

langgraph-dev:
	uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.12 langgraph dev --allow-blocking

coverage:
	uv run pytest --cov=src tests/ --cov-report=term-missing --cov-report=xml

build-wheels:
	python scripts/build_wheels_uv.py

install-wheels:
	python scripts/install_wheels_uv.py

download-wheels-offline:
	python scripts/download_volcengine_offline.py
