.PHONY: install test smoke lint source-matrix-regression source-matrix-watch

install:
	pip install -r requirements.txt

test:
	pytest -q tests/

smoke:
	python -c "from app.pipeline.research import ResearchPipeline; print('OK')"

lint:
	ruff check app/ tests/

source-matrix-regression:
	python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified
	python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified
	python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified

source-matrix-watch:
	python verify_source_matrix.py --regression-profile boundary-watch
	python verify_source_matrix.py --regression-profile special-watch
	python verify_source_matrix.py --regression-profile rate-limited-watch
