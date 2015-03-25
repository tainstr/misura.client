Procedura traduzione runtime di Misura4:
	1. Attivare l'opzione linguist in client/parameters.py
	2. Utilizzare la porzione di programma che si desidera tradurre. Questo genererà un file runtime_timestamp contenente tutte le stringe traducibili.
	3. Eseguire lsync.py dando in argomento i file runtime_...
	4. Questo genererà i file QtLinguist per tutte le lingue, misura4_it.ts, misura4_de.ts, etc
	5. Aggiornare i file usando QtLinguist

	
Procedura per la traduzione delle stringhe statiche:
	1. Eseguire adder.sh per aggiornare misura4.pro (elenco di file sorgente ed interfaccia).
	2. Eseguire pylupdate4 su misura4.pro per creare il file ts con tutte le stringhe statiche.
	3. Tradurre il file
	4. Lanciare nuovamente sync.py, con o senza argomenti

Dopo ogni traduzione:
	1. Eseguire lrelease su tutti i file di lingua (misura4_*.ts)
	
	
In futuro queste procedure potrebbero essere automatizzate (eccetto ovviamente la traduzione)