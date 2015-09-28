RM=rm -rf

.PHONY: clean
clean:
	-$(RM) *.py[cod] *.bin *.parm *.tlog *.raw logs terrain
	-$(RM) */*.py[cod]
