import datetime
from functools import wraps

import jwt
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from sqlalchemy.sql.functions import count
from werkzeug.security import generate_password_hash, check_password_hash

from my_clearbit import get_user_and_company_data
from my_hunter import email_verification
from schema import user_registration_schema, recipe_creation_schema, recipe_rating_schema

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nestotesko'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ivana:ivana1@localhost:5432/UsrRcp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(40))
    email = db.Column(db.String(50))
    username = db.Column(db.String(50))
    password = db.Column(db.String(100))
    recipes = db.relationship('Recipe', backref='user')


recipe_ingredients = db.Table('recipe_ingredients',
                              db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id')),
                              db.Column('ingredients_id', db.Integer, db.ForeignKey('ingredients.id')))


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))
    text = db.Column(db.String(300))
    r_sum = db.Column(db.Integer)
    r_count = db.Column(db.Integer)
    rating = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ingredients = db.relationship('Ingredients', secondary=recipe_ingredients, backref=db.backref('recipe'))


class Ingredients(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'access_token' in request.headers:
            token = request.headers['access_token']
        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['id']).first()
        except:
            return jsonify({'message': 'Token is invalid.'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@app.route('/registration', methods=['POST'])
def registration():
    try:
        data = user_registration_schema.load(request.get_json())
    except ValidationError as err:
        return err.messages, 400

    user = User.query.filter_by(username=data['username']).first()
    if user:
        return jsonify({"message": 'User with that username already exists.'}), 400
    hashed_password = generate_password_hash(data['password'], method='sha256')

    #  hunter for verifying email
    email = data['email']
    if not email_verification(email):
        return jsonify({'message': 'Invalid email'}), 400

    #  clearbit for getting additional user or company data
    get_user_and_company_data(email)

    new_user = User(first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=data['email'],
                    username=data['username'],
                    password=hashed_password)

    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": f'User {new_user.first_name} has been created successfully.'}), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'message': 'User with that username does not exist'}), 401
    if not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid password.'}), 401

    token = jwt.encode(
        {'id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
        app.config['SECRET_KEY'], algorithm='HS256')
    return jsonify({"token": token}), 200


@app.route('/creation', methods=['POST'])
@token_required
def creation(current_user):
    try:
        data = recipe_creation_schema.load(request.get_json())
    except ValidationError as err:
        return err.messages, 400

    name = data['name']
    text = data['text']
    ingredients = [x.strip() for x in data['r_ingredients'].split(',')]

    old_recipe = Recipe.query.filter_by(name=name).first()
    if old_recipe:
        return jsonify({"message": f'Recipe {name} already exists.'}), 200

    new_recipe = Recipe(name=name,
                        text=text,
                        user_id=current_user.id,
                        r_sum=0,
                        r_count=0,
                        rating=0)

    db.session.add(new_recipe)
    db.session.commit()

    db_ingredients = Ingredients.query.with_entities(Ingredients.name).all()
    db_ingredients_list = [r for (r,) in db_ingredients]

    for ingredient in ingredients:
        if ingredient not in db_ingredients_list:
            new_ingredient = Ingredients(name=ingredient)
            db.session.add(new_ingredient)
            db.session.commit()

    db_ing_all = Ingredients.query.all()
    for i in db_ing_all:
        if i.name in ingredients:
            i.recipe.append(new_recipe)

    db.session.commit()

    return jsonify({"message": f'Recipe {new_recipe.name} has been created successfully.'}), 200


@app.route('/rating', methods=['POST'])
@token_required
def rating(current_user):
    try:
        data = recipe_rating_schema.load(request.get_json())
    except ValidationError as err:
        return err.messages, 400

    r_rating = data['rating']
    rcp_id = data['rcp_id']

    recipe = Recipe.query.filter_by(id=rcp_id).first()
    if not recipe:
        return jsonify({"message": f'Recipe {rcp_id} does not exist.'}), 400
    if recipe.user_id == current_user.id:
        return jsonify({"message": 'You can not rate your own recipe.'}), 200

    recipe.r_sum += r_rating
    recipe.r_count += 1
    recipe.rating = round(recipe.r_sum / recipe.r_count, 2)

    db.session.commit()

    return jsonify({"message": f'Recipe {recipe.name} has been rated successfully.'}), 200


def get_rcp(rcp):
    everything = []
    for a in rcp:
        recipe = {
            "id": a.id,
            "name": a.name,
            "ingredients": [ingredient.name for ingredient in a.ingredients],
            "text": a.text,
            "rating": a.rating,
            "user_id": a.user_id
        }

        everything.append(recipe)

    return everything


@app.route('/all_recipes')
def all_recipes():
    all_rcp = Recipe.query.order_by(Recipe.id).all()
    all_r = get_rcp(all_rcp)

    return jsonify({"message": all_r}), 200


@app.route('/my_recipes')
@token_required
def my_recipes(current_user):
    my_rcp = Recipe.query.filter_by(user_id=current_user.id).all()
    my_r = get_rcp(my_rcp)

    return jsonify({"message": my_r}), 200


@app.route('/top_ing')
def top_ing():
    top = db.session.query(Ingredients) \
        .select_from(Recipe) \
        .join(Ingredients.recipe) \
        .group_by(Ingredients.id) \
        .order_by(count(Recipe.id).desc()).limit(5)

    list1 = []
    for t in top:
        list1.append({t.name: len(t.recipe)})

    return jsonify({"Most used ingredients are": list1}), 200


@app.route('/rcp_by_name/<name>')
def rcp_by_name(name):
    r = Recipe.query.filter_by(name=name).all()
    recipe = get_rcp(r)
    return jsonify({"The required recipe is": recipe}), 200


@app.route('/rcp_by_ing/<ing>')
def rcp_by_ing(ing):
    r = Recipe.query.filter_by(r_ingredients=ing).all()
    recipe = get_rcp(r)
    return jsonify({"The required recipe is": recipe}), 200


@app.route('/rcp_by_text/<text>')
def rcp_by_text(text):
    r = Recipe.query.filter_by(text=text).all()
    recipe = get_rcp(r)
    return jsonify({"The required recipe is": recipe}), 200


#  recipe by name, ingredients, text in one function
@app.route('/search')
def search():
    name = request.args.get('name')
    ingredient = request.args.get('ingredient')
    text = request.args.get('text')
    recipes_by_name = Recipe.query.filter_by(name=name)
    recipes_by_ingredient = db.session.query(Recipe) \
        .select_from(Ingredients) \
        .join(Ingredients.recipe) \
        .filter(Ingredients.name == ingredient)
    recipes_by_text = Recipe.query.filter(Recipe.text.like(f'%{text}%'))
    r = recipes_by_name.union(recipes_by_ingredient).union(recipes_by_text).all()

    all_recipes = get_rcp(r)
    return {'Recipes': all_recipes}


@app.route('/max_ing')
def max_ing():
    r = db.session.query(Recipe) \
        .select_from(Ingredients) \
        .join(Ingredients.recipe) \
        .group_by(Recipe.id) \
        .order_by(count(Ingredients.id).desc()).limit(1)
    recipe = get_rcp(r)
    return jsonify({"Recipe with maximum number of ingredients is": recipe}), 200


@app.route('/min_ing')
def min_ing():
    r = db.session.query(Recipe) \
        .select_from(Ingredients) \
        .join(Ingredients.recipe) \
        .group_by(Recipe.id) \
        .order_by(count(Ingredients.id).asc()).limit(1)
    recipe = get_rcp(r)
    return jsonify({"Recipe with minimum number of ingredients is": recipe}), 200


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
