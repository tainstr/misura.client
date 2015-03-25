#!/bin/bash
"""Aggiunta automatica di tutti i file interfaccia per pylupdate4"""

pro='./misura4.pro'
echo '' > $pro
for f in `ls /opt/misura4/client/*.py`
	do echo "SOURCES += $f" >> $pro
	echo "SOURCES += $f"
	done
	
echo "TRANSLATIONS += static_it.ts" >> $pro
echo "TRANSLATIONS += static_de.ts" >> $pro
echo "TRANSLATIONS += static_es.ts" >> $pro
echo "TRANSLATIONS += static_fr.ts" >> $pro
