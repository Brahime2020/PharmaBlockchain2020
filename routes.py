import datetime
import json

from pystrich.datamatrix import DataMatrixEncoder
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from flask import render_template, redirect, request, flash, url_for
from app import app, db
from app.forms import LoginForm, RegistrationForm, MedicineForm, BatchForm
from flask_login import current_user, login_user, login_required, logout_user
from app.models import Actor, Medicine, Adress, Batch
from pylibdmtx.pylibdmtx import decode
from werkzeug.utils import secure_filename
from PIL import Image

from sqlalchemy.exc import IntegrityError

# Le noeud avec lequel notre application interagit, il peut y avoir plusieurs noeuds.
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000/"

errors =[]
manufacturer = True

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/update_connected_node_address/<address>')
def update_connected_node_address(address):
    """
    Route pour changer le noeud actuellement connecté
    """
    #TODO mettre à jour ces méthodes

    global CONNECTED_NODE_ADDRESS
    #CONNECTED_NODE_ADDRESS = "http://127.0.0.1:" + str(address) + "/"
    return "Succès"

@app.route('/')
def index():
    """
    Pour la: Construisez et obtenez l'index
    """
    #transactions = fetch_transactions()
    #for transaction in transactions:
    #medicine = Medicine.query.filter_by(medicine_id=Batch.query.filter_by(batch_id=transaction['batch_id']).first().medicine_id).first()
    #transaction.update( {'medicine_name': medicine.medicine_name, 'medicine_id': medicine.medicine_id} )

    return render_template('index.html',
                           title='Pharma Blockchain',
                           manufacturer=manufacturer,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string,
                           errors=errors)

@app.route('/actor/<actor_name>')
@login_required
def actor(actor_name):
    """
    Retourner la page d'acteur pour un acteur de la blockchain en utilisant le nom de l'acteur (a string)
    """
    actor = Actor.query.filter_by(actor_name=actor_name).first_or_404()
    adress = Adress.query.filter_by(id=actor.id).first()
    return render_template( 'actor.html',
                            title=actor.actor_name,
                            actor=actor,
                            manufacturer=manufacturer,
                            adress=adress)

@app.route('/actorID/<actor_id>')
def actorID(actor_id):
    """
    Retourner la page d'acteur pour un acteur de la blockchain en utilisant l'identifiant d'acteur (an int)
    """
    actor = Actor.query.filter_by(id=actor_id).first_or_404()
    adress = Adress.query.filter_by(id=actor_id).first()
    return render_template( 'actor.html',
                            title=actor.actor_name,
                            actor=actor,
                            manufacturer=manufacturer,
                            adress=adress)

@app.route('/batch/<batch_id>')
def batch(batch_id):
    """
    Retourner la page de lot pour un lot de la blockchain en utilisant l'ID de lot (an int)
    """
    datamatrix_data = generateDatamatrix(batch_id)
    transactions = fetch_batch_transactions(batch_id)
    batch = Batch.query.filter_by(batch_id=batch_id).first_or_404()

    # Obtenez tous les parents de ce lot
    while batch.parent_batch_id is not None:
        batch = Batch.query.filter_by(batch_id=batch.parent_batch_id).first_or_404()
        transactions.append(fetch_batch_transactions(batch.batch_id)[0])

    transactions = sorted(transactions, key=lambda k: k['timestamp'], reverse=True)

    for t in transactions:
        if int(t['batch_id']) != int(batch_id):
            t['status']='Fragmenter'

    medicine = Medicine.query.filter_by(medicine_id=batch.medicine_id).first()
    return render_template( 'batch.html',
                            title="Lot: " + str(batch.batch_id),
                            medicine=medicine,
                            batch=batch,
                            transactions=transactions,
                            manufacturer=manufacturer,
                            readable_time=timestamp_to_string,
                            datamatrix_data=datamatrix_data)

@app.route('/user_medicine')
@login_required
def user_medicine():
    """
    Liste de tous les médicaments de l'utilisateur actuellement connecté (son stock)
    """
    transactions = fetch_transactions_without_double()
    medicines = Medicine.query.filter_by(manufacturer_id=current_user.id).all()

    #blockchain
    user_id = current_user.id
    transactions_user = []
    for transaction in transactions:
        medicine_send_forward = False
        if transaction["recipient_id"] == user_id and transaction["status"] == "accepted":
            for t in transactions:
                if t["sender_id"] == user_id and transaction["batch_id"] == t["batch_id"] and t["status"] == "accepted" and t["sender_id"] != t["recipient_id"]:
                    medicine_send_forward = True
            if medicine_send_forward is False:
                transactions_user.append(transaction)

    return render_template('user_medicine.html',
                           title='Stocke des médicaments d\'un utilisateur',
                           transactions=transactions_user,
                           medicines=medicines,
                           manufacturer=manufacturer,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string,
                           user_id=user_id,
                           errors=errors)

@app.route('/request_mine', methods=['GET'])
@login_required
def request_mine():
    """
    Demander au noeud connecté de miner pour l'utilisateur d'un noeud
    """
    mine_address = "{}mine".format(CONNECTED_NODE_ADDRESS)
    requests.get(mine_address)
    print('l153, la demande de minage sous l\'adresse suivant', mine_address)

    return redirect(url_for('user_transactions'))

def mine_blockchain():
    """
    Demander au noeud connecté de miner
    """
    mine_address = "{}mine".format(CONNECTED_NODE_ADDRESS)
    requests.get(mine_address)

@app.route('/fetch_medicine_for_user_id', methods=['POST'])
@login_required
def fetch_medicine_for_user_id():
    """
    Route pour obtenir tous les médicaments pour un user_id donné
    """
    user_id = current_user.id

    return redirect(url_for('user_medicine'))

@app.route('/new_medicine', methods=['GET', 'POST'])
@login_required
def new_medicine():
    """
    Route pour ajouter un nouveau médicament à la blockchain
    """

    if request.method == 'POST':
        if request.form['medicine_name']=='' or request.form['GTIN']=='':
            flash('Données manquantes ⚠️⚠️')
        else:
            try:
                medicine=Medicine(medicine_name=request.form['medicine_name'], GTIN=request.form['GTIN'], manufacturer_id=current_user.id)
                db.session.add(medicine)
                db.session.commit()
            except IntegrityError:
                flash('Ce médicament existe déjà dans la BDD BC.')

                return redirect(url_for('user_medicine'))

    return redirect(url_for('user_medicine'))

@app.route('/new_batch', methods=['POST'])
@login_required
def new_batch():
    """
    Route pour créer un nouveau lot
    """
    if request.method == 'POST':
        if request.form['exp_date']=='' or request.form['quantity']=='':
            flash('Données manquantes ⚠️⚠️')
        else:
            batch=Batch(exp_date=request.form['exp_date'], medicine_id=request.form['medicine_id'], quantity=request.form['quantity'])
            db.session.add(batch)
            db.session.flush()
            db.session.commit()

            json_object = {
                'batch_id': int(batch.batch_id),
                'sender_id': int(current_user.id),
                'quantity': int(request.form['quantity'])
            }

            new_batch_adress="{}register_batch".format(CONNECTED_NODE_ADDRESS)
            requests.post(new_batch_adress,
                          json=json_object,
                          headers={'Content-type': 'application/json'})

            return redirect(url_for('user_medicine'))

    return redirect(url_for('user_medicine'))

@app.route('/send_batch', methods=['POST'])
@login_required
def send_batch():
    """
    Route pour envoyer un lot entre 2 ID utilisateurs de blockchains
    """
    transactions = fetch_current_actor_transactions()
    if request.method == 'POST':
        if request.form['batch_id']=='' or request.form['recipient_id']=='' or request.form['quantity']=='':
            flash('Données manquantes ⚠️⚠️')
        else:
            user_owner_batch = False
            batch_quantity = 0
            # Vérifiez que l'utilisateur est le propriétaire du lot qu'il essaie d'envoyer
            # L'utilisateur est le propriétaire de le lot qui est dans la liste des transactions
            # association à son identifiant.
            for t in transactions:
                if int(request.form['batch_id']) == int(t['batch_id']):
                    user_owner_batch = True
                    batch_origin = Batch.query.filter_by(batch_id=request.form['batch_id']).first_or_404()
                    print('l246R, on à envoyons le: ', batch_origin)

            if user_owner_batch:
                if int(batch_origin.quantity) == int(request.form['quantity']): #Envoyer tout le lot
                    json_object = {
                        'batch_id': int(request.form['batch_id']),
                        'sender_id': int(current_user.id),
                        'recipient_id': int(request.form['recipient_id']),
                        'quantity': int(batch_origin.quantity)
                    }
                    new_transaction_address = "{}new_transaction".format(CONNECTED_NODE_ADDRESS)
                    response = requests.post(   new_transaction_address,
                                                json=json_object,
                                                headers={'Content-type': 'application/json'})

                elif int(batch_origin.quantity) > int(request.form['quantity']): # Divisez le lot en 2
                    print("Breaking the batch in 2")
                    size_batch_1 = int(batch_origin.quantity) - int(request.form['quantity'])
                    size_batch_2 = int(request.form['quantity'])

                    # Ajouter de nouveaux lots 
                    # lot 1 garder le même propriétaire 
                    # lot 2 est envoyé au nouveau propriétaire
                    batch1=Batch(exp_date=batch_origin.exp_date, medicine_id=batch_origin.medicine_id, quantity=size_batch_1, parent_batch_id=batch_origin.batch_id)
                    batch2=Batch(exp_date=batch_origin.exp_date, medicine_id=batch_origin.medicine_id, quantity=size_batch_2, parent_batch_id=batch_origin.batch_id)
                    db.session.add(batch1)
                    db.session.add(batch2)
                    db.session.flush()
                    db.session.commit()

                    json_object1 = {
                        'batch_id': int(batch1.batch_id),
                        'sender_id': int(current_user.id),
                        'quantity': int(batch1.quantity)
                    }

                    json_object2 = {
                        'batch_id': int(batch2.batch_id),
                        'sender_id': int(current_user.id),
                        'quantity': int(batch2.quantity)
                    }
                    new_batch_adress="{}register_batch".format(CONNECTED_NODE_ADDRESS)
                    requests.post(new_batch_adress,
                                  json=json_object1,
                                  headers={'Content-type': 'application/json'})
                    requests.post(new_batch_adress,
                                  json=json_object2,
                                  headers={'Content-type': 'application/json'})

                    mine_blockchain() #Ajouter un nouveau lot à la blockchain

                    json_object = {
                        'batch_id': int(batch2.batch_id),
                        'sender_id': int(current_user.id),
                        'recipient_id': int(request.form['recipient_id']),
                        'quantity': int(batch2.quantity)
                    }
                    new_transaction_address = "{}new_transaction".format(CONNECTED_NODE_ADDRESS)
                    response = requests.post(   new_transaction_address,
                                                json=json_object,
                                                headers={'Content-type': 'application/json'})
                    print('l307R', new_transaction_address)


                elif batch_origin.quantity < request.form['quantity']: # Ne fait rien
                    flash('Vous n\'avez pas cette quantité de médicament.')

            else:
                flash('Vous n\'êtes pas propriétaire du lot')
            return redirect(url_for('user_transactions'))


@app.route('/user_transactions')
@login_required
def user_transactions():
    """
    Liste des transactions de l'acteur actuellement connecté
    """
    transactions = fetch_current_actor_transactions()

    user_transactions = []
    for transaction in transactions:

        medicine = Medicine.query.filter_by(medicine_id=Batch.query.filter_by(batch_id=transaction['batch_id']).first().medicine_id).first()
        transaction.update( {'medicine_name': medicine.medicine_name, 'medicine_id': medicine.medicine_id} )

        user_transactions.append(transaction)

    return render_template('user_transactions.html',
                           title='Gérez vos transactions',
                           transactions=user_transactions,
                           manufacturer=manufacturer,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string,
                           user_id=current_user.id,
                           errors=errors)

@app.route('/submit_accept_transaction', methods=['POST'])
@login_required
def submit_accept_transaction():
    """
    Le Point final pour la confirmation d'une transaction dans la blockchain
    """
    if request.method == 'POST':
        json_object = {
            'batch_id': int(request.form['batch_id']),
            'sender_id': int(request.form['sender_id']),
            'recipient_id': int(current_user.id),
            'quantity': int(request.form['quantity']),
            'status': request.form['statusTransaction']
        }


        submit_accept_transaction = "{}response_transaction".format(CONNECTED_NODE_ADDRESS)

        requests.post(submit_accept_transaction,
                      json=json_object,
                      headers={'Content-type': 'application/json'})

        mine_blockchain()

        return redirect(url_for('user_transactions'))




'''
--------------------
 ROUTES DE CONNEXION
--------------------
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Route pour se connecter
    """
    form = LoginForm()
    if form.validate_on_submit():
        actor = Actor.query.filter_by(actor_name=form.actor_name.data).first()
        if actor is None or not actor.check_password(form.password.data):
            flash('Nom ou mot de passe d\'acteur non valide')
            return redirect(url_for('login'))

        global manufacturer
        if actor.manufacturer != 1:
            manufacturer = False
        else:
            manufacturer = True

        login_user(actor, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Se connecter', form=form)

@app.route('/logout')
def logout():
    """
    Route pour la déconnexion
    """
    global manufacturer
    manufacturer = False

    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Route pour enregistrer un nouvel utilisateur
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        actor = Actor(actor_name=form.actor_name.data, email=form.email.data, phone=form.phone.data, manufacturer=form.manufacturer.data)
        actor.set_password(form.password.data)
        db.session.add(actor)
        db.session.flush() # pour obtenir l'identifiant de l'acteur qui vient d'être ajouté

        adress = Adress(street=form.street.data, city=form.city.data, state=form.state.data, zip_code=form.zip_code.data, country=form.country.data, id=actor.id)
        db.session.add(adress)
        db.session.commit()
        flash('Félicitations, vous êtes maintenant inscrit ✅')

        global manufacturer
        if actor.manufacturer != 1:
            manufacturer = False
        else:
            manufacturer = True

        login_user(actor, remember=True)

        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)

'''
--------------------
 SUPPORT DE FONCTIONS
--------------------
'''

def timestamp_to_string(epoch_time):
    """
    pour Convertir l'horodatage en une chaine lisible
    """
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%d/%m/%Y - %H:%M:%S')

def generateDatamatrix(batch_id):
    """
    Générer la datamatrix d'un lot à l'aide de l'ID de lot
    """
    batch = Batch.query.filter_by(batch_id=batch_id).first_or_404()
    medicine = Medicine.query.filter_by(medicine_id=batch.medicine_id).first()

    balise01 = "ASCII232"
    balise02 = "ASCII29"

    gtin = medicine.GTIN
    exp_date = batch.exp_date
    lot = batch.batch_id
    free_data = ""

    data = str(balise01) + "01" + str(gtin) + "17" + str(exp_date) + "10" + str(lot) + str(balise02) + "91" + str(free_data)

    datamatrix_data = DataMatrixEncoder(data)

    return data

def fetch_transactions():
    """
    Fonction pour récupérer la chaîne à partir d'un noeud de chaîne de blocs, analyser la
    données et les stocker localement.
    """
    get_chain_address = "{}chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        chain_content = []
        chain = json.loads(response.content)
        for block in chain["chain"]:
            for transaction in block["transactions"]:
                transaction["index"] = block["index"]
                transaction["hash"] = block["previous_hash"]
                chain_content.append(transaction)

        return sorted(chain_content, key=lambda k: k['timestamp'], reverse=True)

def fetch_transactions_without_double():
    """
    Fonction pour récupérer la chaine à partir d'un noeud de Blockchain, analyser les données,
    vérifiez que chaque transaction n'apparaît qu'une seule fois et stockez-la localement.
    """
    get_chain_address = "{}chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        chain_content = []
        chain = json.loads(response.content)
        for block in chain["chain"]:
            for transaction in block["transactions"]:
                transaction["index"] = block["index"]
                transaction["hash"] = block["previous_hash"]
                chain_content.append(transaction)

        chain_content_cp = []
        for transaction in chain_content:
            transaction_confirmed_or_rejected = False
            for t in chain_content:
                if t["batch_id"] == transaction["batch_id"] and t["sender_id"] == transaction["sender_id"] and t["recipient_id"] == transaction["recipient_id"] and t["timestamp"] != transaction["timestamp"]:
                    transaction_confirmed_or_rejected = True
            if transaction_confirmed_or_rejected is False or transaction["status"] != "waiting" :
                chain_content_cp.append(transaction)

        return sorted(chain_content_cp, key=lambda k: k['timestamp'], reverse=True)

def fetch_current_actor_transactions():
    """
    Récupérer les transactions de l'acteur actuellement connecté
    """
    get_chain_address = "{}chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        transactions_actor=[]
        data_transactions=[]
        chain = json.loads(response.content)
        for element in chain["chain"]:
            for transaction_elem in element["transactions"]:
                data_transactions.append(transaction_elem)

        current_transactions = sorted(data_transactions, key=lambda k: k['timestamp'], reverse=True)

        batch_with_owner = []

        for t in current_transactions:
            batch_have_owner = False
            for b in batch_with_owner:
                if b['batch_id'] == t['batch_id']:
                    batch_have_owner = True

            if not batch_have_owner:
                if t['status'] == "accepted" or t['status'] == "waiting":
                    if t['recipient_id'] == current_user.id:
                        transactions_actor.append(t)
                if t['status'] == "refused":
                    if t['sender_id'] == current_user.id:
                        transactions_actor.append(t)
                batch_with_owner.append(t)
                print('l555R', transactions_actor)

        return sorted(transactions_actor, key=lambda k: k['timestamp'], reverse=True)

def fetch_batch_transactions(batch_id):
    """
    Récupérer les transactions d'un lot en utilisant son identifiant
    """
    get_chain_address = "{}chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        transactions_batch = []
        chain = json.loads(response.content)

        for element in chain["chain"]:
            for transaction in element["transactions"]:
                if int(transaction["batch_id"]) == int(batch_id):
                    transactions_batch.append(transaction)

        transactions_batch = sorted(transactions_batch, key=lambda k: k['timestamp'], reverse=True)
        print('l574R', transactions_batch)

        return transactions_batch
