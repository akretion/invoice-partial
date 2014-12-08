
OPENERP_ADDONS=../../odoo-7/addons,.
COVERAGE?=coverage
COVERAGE_REPORT=$(COVERAGE) report -m
COVERAGE_PARSE_RATE=$(COVERAGE_REPORT) | tail -n 1 | sed "s/ \+/ /g" | cut -d" " -f4
OE=whereis oe | cut -d" " -f2

MODULE_NAME=sale_order_partial_invoice_percent
MODULE_PATH=$(MODULE_NAME)
DB_NAME=test_$(MODULE_NAME)

test:
	openerp-server -d $(DB_NAME) --addons $(OPENERP_ADDONS) --test-enable --stop-after-init --log-level test --init $(MODULE_NAME)

coverage:
	$(COVERAGE) run -p --omit=$(MODULE_PATH)/__openerp__.py --source=$(MODULE_PATH) `$(OE)` run-tests -d $(DB_NAME) --addons $(OPENERP_ADDONS) -m $(MODULE_NAME)
	$(COVERAGE) combine
	$(COVERAGE_REPORT)
	if [ "100%" != "`$(COVERAGE_PARSE_RATE)`" ] ; then exit 1 ; fi

init_testdb:
	createdb $(DB_NAME)
	openerp-server --addons=$(OPENERP_ADDONS) -i $(MODULE_NAME) --stop-after-init -d $(DB_NAME) --log-level=warn

drop_testdb:
	echo 'DROP DATABASE $(DB_NAME);' | psql

