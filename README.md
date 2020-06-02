# PharmaBlockchain2020
Notre application web blockchain pour l'amélioration de la traçabilité des médicaments. Ce projet a été réalisé en collaboration avec M. Mami Med Amine et M. Mehdi Rouen Serik à l'Université Oran 1 Ahmed Ben Bella. Le back-end de la blockchain utilise principalement Pythonen particulier le microframework FLASK. et en frontend HTML CSS.



# Utilisation de l'application 
Pour lancer la blockchain à partir d'un terminal, et la blockchain s'exécutera sur le port 8000:



   cd  PharmaBlockchain2020
   export FLASK_APP = blockchain.py 
   flask run -p 8000
   
   
   
   
Depuis un autre terminal, vous devez maintenant lancer le client de la blockchain:
   
   
   
   
   cd PharmaBlockchain2020
   export FLASK_APP=blockchain.py
   python3 run_app.py -p 5000
   
   
   
Alternativement, le client peut s'exécuter sur n'importe quel port avec (ici pour l'exécuter sur le port 5001):




   python3 run_app.py -p 5001
   python3 run_app.py -p 5002
   python3 run_app.py -p 5003
  
   
    
