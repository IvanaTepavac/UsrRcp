from marshmallow import Schema, fields
from marshmallow.validate import Range, Length


class UserRegistration(Schema):
    first_name = fields.Str(required=True, validate=Length(max=15))
    last_name = fields.Str(required=True, validate=Length(max=20))
    email = fields.Str(required=True, validate=Length(max=30))
    username = fields.Str(required=True, validate=Length(max=15))
    password = fields.Str(required=True, validate=Length(max=100))


class RecipeCreation(Schema):
    name = fields.Str(required=True, validate=Length(max=30))
    r_ingredients = fields.Str(required=True, validate=Length(max=300))
    text = fields.Str(required=True, validate=Length(max=500))


class RecipeRating(Schema):
    rcp_id = fields.Int(required=True)
    rating = fields.Int(required=True, validate=Range(min=1, max=5))


user_registration_schema = UserRegistration()
recipe_creation_schema = RecipeCreation()
recipe_rating_schema = RecipeRating()

