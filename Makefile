# Clear python cache
.PHONY: clear-cache
clear-cache:
	-rm -f *.pyc */*.pyc */*/*.pyc */*/*/*.pyc */*/*/*/*.pyc */*/*/*/*/*.pyc || true
	-rm -rf __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__ */*/*/*/__pycache__ */*/*/*/*/__pycache__ || true
	-rm -rf .ipynb_checkpoints */.ipynb_checkpoints */*/.ipynb_checkpoints */*/*/.ipynb_checkpoints */*/*/*/.ipynb_checkpoints */*/*/*/*/.ipynb_checkpoints || true
	-rm -rf .mypy_cache */.mypy_cache */*/.mypy_cache */*/*/.mypy_cache */*/*/*/.mypy_cache */*/*/*/*/.mypy_cache || true
