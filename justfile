all:
    uv run python -m pytest 
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy .
    uv run python -m db.generate_db_image
    echo "Everything looks good!"

test:
    uv run python -m pytest 

lint:
    uv run ruff format .
    uv run ruff check --fix .

typing:
    uv run mypy .
