.PHONY: demo demo-live test

demo:
	env OPENAI_API_KEY= python3 -m src.main

demo-live:
	python3 -m src.main

test:
	python3 -m unittest discover -s tests
