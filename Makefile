include .env

$(eval @:)

clean: clean-eggs clean-build
	@sudo find . -iname '*.pyc' -delete
	@sudo find . -iname '*.pyo' -delete
	@sudo find . -iname '*~' -delete
	@sudo find . -iname '*.swp' -delete
	@sudo find . -iname '__pycache__' -delete
clean-eggs:
	@sudo find . -name '*.egg' -print0|xargs -0 rm -rf --
	@sudo rm -rf .eggs/
clean-build:
	@sudo rm -fr build/
	@sudo rm -fr dist/
	@sudo rm -fr src/*.egg-info
build: clean
	@echo "Building source..."
	python3 -m build
check:
	@echo "Check for errors pypi..."
	python3 -m twine check dist/*
test:
	@echo "Upload for testpypi..."
	python3 -m twine upload --repository testpypi dist/*
dry:
	python3 -m pip install --index-url https://test.pypi.org/simple/ --no-deps relock
upload:
	@echo "Release..."
	python3 -m twine upload dist/*
install:
	python3 -m pip install relock