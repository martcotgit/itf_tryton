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

# Staging commands
staging-up:
	$(DOCKER_COMPOSE) -f docker-compose-staging.yml up -d --remove-orphans

staging-down:
	$(DOCKER_COMPOSE) -f docker-compose-staging.yml down

staging-logs:
	$(DOCKER_COMPOSE) -f docker-compose-staging.yml logs -f

staging-update-db:
	$(DOCKER_COMPOSE) -f docker-compose-staging.yml exec tryton trytond-admin -c /etc/tryton/trytond.conf -d tryton --all

staging-shell:
	$(DOCKER_COMPOSE) -f docker-compose-staging.yml exec tryton bash
