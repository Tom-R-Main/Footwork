# Common commands; everything runs from jevdual/. Evals need TYPESAFE_API_KEY and MODEL_API_KEY.
J := jevdual

.PHONY: sync test test-browser lint upstream-tests eval-dev eval-heldout eval-live

sync:
	cd $(J) && uv sync

test:
	cd $(J) && uv run pytest -q -m "not browser"

test-browser:
	cd $(J) && JEVDUAL_BROWSER_TESTS=1 uv run pytest -q -m browser

lint:
	cd $(J) && uv run ruff check python evals tests scripts && cargo fmt --all --check && cargo clippy --workspace --all-targets --locked -- -D warnings

upstream-tests:
	cd $(J) && scripts/upstream_tests.sh

eval-dev:
	cd $(J) && uv run python -m evals.runner --split dev --arm stock --arm guarded --arm dual --llm meta --max-steps 20

eval-heldout:
	cd $(J) && uv run python -m evals.runner --split heldout --arm stock --arm guarded --arm dual --llm meta --max-steps 20

eval-live:
	cd $(J) && uv run python -m evals.runner --split live-dev --arm guarded --arm dual --llm meta --max-steps 25
