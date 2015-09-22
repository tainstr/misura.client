1. Execute language_sync.py
2. Update misura_*.ts files with new translations with Qt Linguist.
3. Execute lrelease on every misura_*.ts file




CHECK:

	
Procedura per la traduzione delle stringhe statiche (con .tr()):
	1. Eseguire adder.sh per aggiornare misura4.pro (elenco di file sorgente ed interfaccia).
	2. Eseguire pylupdate4 su misura4.pro per creare il file ts con tutte le stringhe statiche.
	3. Tradurre il file
	4. Lanciare nuovamente language_sync.py, con o senza argomenti

Dopo ogni traduzione:
	1. Eseguire lrelease su tutti i file di lingua (misura4_*.ts)
