from hashlib import sha256
import json

import time
from uuid import uuid4

import requests
from flask import Flask, jsonify, request, url_for

'''
les composants d'un Bloc de blockchain
 - Un index 
 - la liste des transactions
 - un horodatage : temps de validation entre deux blocs successifs. 
 - le hachage de bloc précédent 
 - un nonce : valeur aléatoire généré par le hachage.
'''
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        """
        Calculation de l'hachage avec l'algorithme de SHA-256
        :param block: <dict> Block
        :return: <str>
        """
        #Triez le dictionnaire par index, pour obtenir un hachage cohérent
        block_string = json.dumps(self.__dict__, sort_keys=True)
        print('l34, la structure de bloc est: ', block_string)
        return sha256(block_string.encode()).hexdigest()

class Blockchain:

    #Difféculté de la preuve de travail (PoW)
    difficulty = 2

    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []

    def create_genesis_block(self):
        """
        Fonction pour générer le premier bloc et le premier hachage
        """
        genesis_block = Block(0, [], time.time(), "00")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)
        print('l54, le Hachage de Bloc est:', genesis_block.hash)

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, block):
        """
       Fonction de preuve de travail qui vérifie que le début de notre hachage est un nombre de zéros.
        """
        block.nonce = 0
        computed_hash = block.compute_hash()
        while computed_hash.startswith('0' * self.difficulty) is False:
            block.nonce += 1
            print('l67, le nonce est:', block.nonce)
            computed_hash = block.compute_hash()
            print('l69, le haching est:', computed_hash)

        return computed_hash

    def add_block(self, block, proof):
        """
        Fonction pour ajouter un bloc à la Blockchain
        """
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Vérifier si block_hash est un hachage valide de bloc avec la difficulté
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    @classmethod
    def check_chain_validity(cls, chain):
        """
        Vérifiez que le hachage est correct ou non ?
        """
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block.hash) or previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        """
        Fonction qui ajoute toutes les transactions non confirmées à un bloc et
        obtenir ensuite la preuve de travail
        """
        #Si il y'a pas des transactions
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []
        announce_new_block(new_block)
        return new_block.index

# Création de l'API Blockchain
app = Flask(__name__)

# Générez une adresse unique globale pour ce noeud
node_identifier = str(uuid4()).replace('-', '')

#Cette copie de noeud de la Blockchain
blockchain = Blockchain()
blockchain.create_genesis_block()

# Une liste d'adresses de tous les autres membres du réseau blockchain
peers = set()

@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required_fields = ["batch_id", "sender_id", "recipient_id", "quantity"]

    if not all(k in values for k in required_fields):
        return 'Données manquantes ⚠️⚠️', 400

    batch_exist = False
    for block in blockchain.chain:
        for transaction in block.transactions:
            if int(transaction['batch_id']) == int(values['batch_id']):
                batch_exist = True

    if batch_exist is False:
        print("Le médicament n'existe pas dans la blockchain.")
        return 'Le médicament n existe pas dans la blockchain', 400

    values["timestamp"] = time.time()
    values["status"] = "waiting"
    blockchain.add_new_transaction(values)
    print('l177', values)

    response = {'message': 'La transaction sera ajoutée'}
    return jsonify(response), 201

@app.route('/response_transaction', methods=['POST'])
def response_transaction():
    values = request.get_json()
    required_fields = ["batch_id", "sender_id", "quantity", "recipient_id", "status"]

    if not all(k in values for k in required_fields):
        return 'Données manquantes ⚠️⚠️', 400

    med_exist = False
    transaction_exist = False
    for block in blockchain.chain:
        for transaction in block.transactions:
            if transaction['batch_id'] == values['batch_id']:
                med_exist = True
            if transaction['batch_id'] == values['batch_id'] and transaction['sender_id'] == values['sender_id'] and transaction['recipient_id'] == values['recipient_id'] and transaction['status']:
                transaction_exist = True

    if med_exist is False:
        return 'Le médicament n existe pas dans la blockchain', 400

    if transaction_exist is False:
        return 'La transaction n existe pas dans la blockchain', 400

    values["timestamp"] = time.time()
    blockchain.add_new_transaction(values)

    response = {'message': 'La réponse de transaction a été ajoutée à la blockchain'}
    return jsonify(response), 201



@app.route('/register_batch', methods=['POST'])
def register_batch():
    """
   Cas où un producteur de médicaments souhaite enregistrer un nouveau lot
    """
    values = request.get_json()
    required_fields = ["batch_id", "sender_id", "quantity"]

    if not all(k in values for k in required_fields):
        return 'Données manquantes ⚠️⚠️', 400

    values['recipient_id']=values['sender_id']
    values["timestamp"] = time.time()
    values["status"] = "accepted"
    blockchain.add_new_transaction(values)
    print('l231', values)

    response = {'message': 'Des médicaments ajoutés à la blockchain'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def get_chain():
    consensus()
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    response = {
        "length": len(chain_data),
        "chain": chain_data,
        "peers": list(peers)
    }
    print('l247', chain_data)

    return jsonify(response), 200

@app.route('/mine', methods=['GET'])
def mine_transactions():
    result = blockchain.mine()
    if not result:
        response = {'message': 'Aucune transaction à miner'}
        print('l253', response)
    else:
        response = {'message': "Block #{} est miner.".format(result)}
        print('l256', response)
    return jsonify(response), 200

@app.route('/unconfirmed_transactions', methods=['GET'])
def unconfirmed_transactions():
    return jsonify(blockchain.unconfirmed_transactions), 200

'''
-----
DECENTRALISATION
-----
'''

'''
@app.route('/add_nodes', methods=['POST'])
def register_new_peers():
    nodes = request.get_json()
    if not nodes:
        return "Données invalide", 400
    for node in nodes:
        peers.add(node)

    return "Succés", 201
'''

@app.route('/register_node', methods=['POST'])
def register_new_node():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Données Invalide", 400

    # Ajouter un noeud à la liste des paires
    peers.add(node_address)

    # Retourner la blockchain consensus au noeud nouvellement enregistré
    # pour synchroniser
    return get_chain()

@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Enregistrer ce noeud actuel sur un autre noeud
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Données Invalide", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Faire une demande d'enregistrement avec un noeud distant et obtenir des informations
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        # mis à jour de la chaine et les paires
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Inscription réussi ✅", 200
    else:
        # en cas de problème, transmettez-le à la réponse de l'API
        return response.content, response.status_code

def create_chain_from_dump(chain_dump):
    blockchain = Blockchain()
    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        if idx > 0:
            added = blockchain.add_block(block, proof)
            if not added:
                raise Exception("la chaine à été vider !!")
        else:  # le bloc est un bloc de genèse, aucune vérification nécessaire
            block.hash = block_data['hash']
            blockchain.chain.append(block)
    return blockchain


@app.route('/add_block', methods=['POST'])
def verify_and_add_block():        
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "Le bloc a été rejeté par le noeud", 400

    return "Bloc ajouté à la chaine", 201


def consensus():
    """
    Un algorithme de consensus simple pour vérifier la validation
    la plus longue chaine.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        print('l370', response)
        length = response.json()['length']
        print('l372', length)
        chain = response.json()['chain']
        print('l374', chain)
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain
            print('l378', current_len)
            print('l379', longest_chain)

    if longest_chain:
        blockchain = longest_chain
        print('l383', blockchain)
        return True

    return False


def announce_new_block(block):
    """
    Fonction pour annoncer un nouveau bloc aux autres noeuds
    """
    headers = {'Content-Type': "application/json"}
    for peer in peers:
        url = "{}add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True), headers=headers)
        print('l391', url)
        print('l392', headers)
