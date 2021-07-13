import pytest
from app import app, db


@pytest.fixture
def client_empty_db():
    app.config["TESTING"] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ivana:ivana1@localhost:5432/UsrRcp_test'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        db.create_all()
        db.session.commit()
        yield client
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def patch_jwt(mocker):
    return mocker.patch(
        "app.jwt.encode", return_value="321"
    )


def test_empty_register(client_empty_db):
    res = client_empty_db.post('/registration')

    assert res.status_code == 400
    assert res.get_json() == {'_schema': ['Invalid input type.']}


def test_registration(client_empty_db):
    data = {
        "first_name": "Ivana",
        "last_name": "Tepavac",
        "email": "ivana.tepavac@factoryww.com",
        "username": "ivancica",
        "password": "123"}

    url = '/registration'
    res = client_empty_db.post(url, json=data)

    assert res.status_code == 200
    assert res.get_json() == {"message": 'User Ivana has been created successfully.'}


def test_registration_with_same_user(client_empty_db):
    test_registration(client_empty_db)
    data = {
            "first_name": "Ivana",
            "last_name": "Tepavac",
            "email": "ivana.tepavac@factoryww.com",
            "username": "ivancica",
            "password": "123"}

    url = '/registration'
    res = client_empty_db.post(url, json=data)

    assert res.status_code == 400
    assert res.get_json() == {"message": 'User with that username already exists. Please Log in'}


def test_registration_without_required_data(client_empty_db):
    data = {
        "first_name": "Ivana",
        "last_name": "Tepavac",
        "email": "ivana.tepavac@factoryww.com"}

    url = '/registration'
    res = client_empty_db.post(url, json=data)

    assert res.status_code == 400
    assert res.get_json() == {'password': ['Missing data for required field.'],
                              'username': ['Missing data for required field.']}


def test_non_existent_user_login(client_empty_db):
    data = {
        "username": "ivanka",
        "password": "111"}

    url = '/login'
    res = client_empty_db.post(url, json=data)

    assert res.status_code == 401
    assert res.get_json() == {'message': 'User with that username does not exist'}


def test_user_with_invalid_password_login(client_empty_db):
    test_registration(client_empty_db)
    data = {
        "username": "ivancica",
        "password": "111"}

    url = '/login'
    res = client_empty_db.post(url, json=data)

    assert res.status_code == 401
    assert res.get_json() == {'message': 'Invalid password.'}


def test_login(client_empty_db, patch_jwt):
    test_registration(client_empty_db)
    data = {
        "username": "ivancica",
        "password": "123"}

    url = '/login'
    res = client_empty_db.post(url, json=data)

    assert res.status_code == 200
    assert res.get_json() == {'token': "321"}

