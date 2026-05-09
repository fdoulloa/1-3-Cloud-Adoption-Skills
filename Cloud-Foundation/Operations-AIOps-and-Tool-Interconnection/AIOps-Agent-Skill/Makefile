.PHONY: demo test deploy install start stop status logs clean

# AIOps Agent Skill - Makefile

ECS_HOST ?= 101.44.184.244
SSH_KEY  ?= $(HOME)/.ssh/gov-rag-20260508055113
SSH      := ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no

demo: ## Run demo with all 6 alert scenarios
	DEMO_MODE=true python3 scripts/run_agent_demo.py 0

demo-all: ## Run demo for all 6 scenarios
	@for i in 0 1 2 3 4 5; do \
		echo "--- Scenario $$i ---"; \
		DEMO_MODE=true python3 scripts/run_agent_demo.py $$i 2>&1 | grep -E "^Alert:|^Expected|Matched|L[0-3]:"; \
		echo; \
	done

test: ## Run unit tests
	DEMO_MODE=true python3 -m pytest tests/ -v --tb=short

test-quick: ## Run unit tests (quiet)
	DEMO_MODE=true python3 -m pytest tests/ -q

deploy: ## Deploy to ECS
	bash scripts/deploy_to_ecs.sh $(ECS_HOST) $(SSH_KEY)

install: ## Install on local ECS (run on ECS)
	bash scripts/install_agent.sh

start: ## Start agent service on ECS
	$(SSH) root@$(ECS_HOST) "systemctl start aiops-agent && systemctl status aiops-agent --no-pager"

stop: ## Stop agent service on ECS
	$(SSH) root@$(ECS_HOST) "systemctl stop aiops-agent"

status: ## Check agent status on ECS
	$(SSH) root@$(ECS_HOST) "systemctl status aiops-agent --no-pager; echo '---'; tail -5 /opt/aiops-agent/aiops_loop.log 2>/dev/null || true"

logs: ## Tail agent logs on ECS
	$(SSH) root@$(ECS_HOST) "tail -20 /opt/aiops-agent/aiops_loop.log 2>/dev/null || journalctl -u aiops-agent -n 20 --no-pager"

css-count: ## Check CSS incident count
	$(SSH) root@$(ECS_HOST) "curl -s -u admin:Andrea1980\$$ 'http://192.168.0.23:9200/ops_incidents-*/_count' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"count\",0), \"incidents\")'"

css-health: ## Check CSS cluster health
	$(SSH) root@$(ECS_HOST) "curl -s -u admin:Andrea1980\$$ 'http://192.168.0.23:9200/_cluster/health?pretty' | head -8"

css-indices: ## List all CSS indices
	$(SSH) root@$(ECS_HOST) "curl -s -u admin:Andrea1980\$$ 'http://192.168.0.23:9200/_cat/indices?v&h=index,docs.count,store.size'"

generate-demo: ## Generate demo alert data
	python3 scripts/generate_demo_alerts.py

ingest-lts: ## Ingest LTS logs to CSS
	python3 scripts/ingest_lts_to_css.py --es-url $${CSS_ENDPOINT:-http://192.168.0.23:9200} --username $${CSS_USERNAME:-admin} --password $${CSS_PASSWORD:-} --insecure

ingest-cts: ## Ingest CTS events to CSS
	python3 scripts/ingest_cts_to_css.py --es-url $${CSS_ENDPOINT:-http://192.168.0.23:9200} --username $${CSS_USERNAME:-admin} --password $${CSS_PASSWORD:-} --insecure

clean: ## Remove checkpoints and logs
	rm -f aiops_checkpoints.db aiops_loop.log
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
