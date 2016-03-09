#/bin/bash
python2 -m unittest discover -s tests -p "*.py" -t ..
RESULT=$?
rm -f logs/*.log
exit $RESULT
