RM=rm -rf

.PHONY: clean
clean:
	-$(RM) *.py[cod] *.bin *.parm *.tlog *.raw terrain __pycache__
	-$(RM) */*.py[cod] */__pycache__
	-$(RM) logs/*.log
