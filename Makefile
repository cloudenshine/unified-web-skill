.PHONY: install test smoke lint

install:
	pip install -r requirements.txt

test:
	pytest -q tests/

smoke:
	python -c "from app.research_pipeline import ResearchPipeline; print('OK')"

lint:
	ruff check app/ tests/
