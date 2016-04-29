RM=rm -rf
SERVICE=mobile-radio-tomography.service

.PHONY: control_panel
control_panel:
	python2 control_panel.py

.PHONY: test
test:
	python2 test.py

# Service-related commands (may need to be superuser for them)
.PHONY: register
register: docs/raspberry-pi/$(SERVICE)
	cp docs/raspberry-pi/$(SERVICE) /etc/systemd/system
	systemctl enable $(SERVICE)

.PHONY: disable
disable:
	systemctl disable $(SERVICE)

.PHONY: start
start:
	systemctl start $(SERVICE)

.PHONY: stop
stop:
	systemctl stop $(SERVICE)

# Clean up directory
.PHONY: clean
clean:
	-$(RM) *~ *.py[cod] *.bin *.parm *.tlog *.raw terrain __pycache__
	-$(RM) */*.py[cod] */__pycache__
	-$(RM) logs/*.log
