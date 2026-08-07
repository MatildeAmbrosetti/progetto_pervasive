1. Questo progetto è stato portato avanti con micro pico. Per far runnare il codice dell'esp32 è necessario CAMBIARE nome al file config_EXAMPLE.json a config.json da caricare sull esp32 e cambiare i valori del json al suo interno. 
2. configurazioni di sistema del esp32 il pin per il led di stato è il 2 
dout è impostato al pin 13 
e il pdsck è impostato al pin 12, la cartella dog va caricata come progetto su esp32 
3. la google function è stata creata in python e con una variabile ambientale che verrà controllata con una variabile che il sensore invia nell'header della domanda http questo per far si che solo chi ha la password corretta possa scrivere sul firestore e per rendere più leggero al sensore l'invio http 