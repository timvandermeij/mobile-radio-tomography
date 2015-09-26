FILES=$(patsubst %.tex,%,$(wildcard *.tex))
RM=rm -f

.PHONY: all
all: $(FILES)

.PHONY: $(FILES)
.SECONDEXPANSION:
$(FILES): $$@.pdf

%.pdf: %.tex %.bib
	pdflatex $<
	bibtex $(patsubst %.tex,%.aux,$<)
	pdflatex $<
	pdflatex $<

%.pdf: %.tex
	pdflatex $<
	pdflatex $<

.PHONY: clean
clean:
	-$(RM) *.aux *.bbl *.blg *.dvi *.log *.out *.pdf *.ps
