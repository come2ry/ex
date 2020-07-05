#!make

lkill:
	- lsof -i @localhost:10001 | grep python | awk 'NR!=1 {print $$2}' | xargs kill
	- ps -fA | grep python | awk 'NR!=1 {print $$2}' | xargs kill

srun:
	$(MAKE) lkill
	pipenv run python server.py

crun:
	pipenv run python client.py