RM=rm -rf

.PHONY: clean
clean:
	-$(RM) *.py[cod] *.bin *.parm *.tlog *.raw logs terrain __pycache__
	-$(RM) */*.py[cod] */__pycache__
