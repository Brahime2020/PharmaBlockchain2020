from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import Actor

class LoginForm(FlaskForm):
    actor_name = StringField('Nom', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Se connecter')

class RegistrationForm(FlaskForm):
    # Actor
    actor_name = StringField('Nom',  validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Numero Telephone', validators=[])
    manufacturer = BooleanField('Fabricateur')
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    password2 = PasswordField('Répeter le mot de passe', validators=[DataRequired(), EqualTo('password')])

    # Adress
    street = StringField('Rue', validators=[DataRequired()])
    city = StringField('Cité', validators=[DataRequired()])
    state = StringField('Wilaya')
    zip_code = StringField('Code Postale', validators=[DataRequired()])
    country = StringField('Pays', validators=[DataRequired()])

    submit = SubmitField('S\'inscrire')

    def validate_name(self, name):
        actor = Actor.query.filter_by(actor_name=actor_name.data).first()
        if actor is not None:
            raise ValidationError('Veuillez utiliser un nom d-utilisateur différent.')

    def validate_email(self, email):
        actor = Actor.query.filter_by(email=email.data).first()
        if actor is not None:
            raise ValidationError('Veuillez utiliser une autre adresse e-mail.')

class MedicineForm(FlaskForm):
    medicine_name = StringField('Nom', validators=[DataRequired()])
    gtin = StringField('GTIN', validators=[DataRequired()]) # Global Trade Item Number
    submit = SubmitField('Ajouter un nouveau médicament')

class BatchForm(FlaskForm):
    quantity = IntegerField('Quantité', validators=[DataRequired()])
