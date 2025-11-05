DOCKER_COMPOSE := docker compose

.PHONY: portal-up portal-down portal-shell tryton-shell build

portal-up:
	$(DOCKER_COMPOSE) up --build portal traefik

portal-down:
	$(DOCKER_COMPOSE) down

portal-shell:
	$(DOCKER_COMPOSE) exec portal bash

tryton-shell:
	$(DOCKER_COMPOSE) exec tryton bash

build:
	$(DOCKER_COMPOSE) build
