#/bin/bash
python2 -m unittest discover -s tests -p "*.py" -t ..
rm -f logs/*.log
