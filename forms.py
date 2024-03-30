from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField
from wtforms.validators import DataRequired
from wtforms import validators


# #WTForm
class AddBookForm(FlaskForm):
    submit = SubmitField("Add to bag")


class BagForm(FlaskForm):
    submit = SubmitField("proceed to checkout")


class RegisterForm(FlaskForm):
        email = EmailField(label='Email', validators=[DataRequired(), validators.Email()])
        password = PasswordField("Password", validators=[DataRequired()])
        name = StringField("Name", validators=[DataRequired()])
        submit = SubmitField(label="SING ME UP!")


class LoginForm(FlaskForm):
    email = EmailField(label='Email', validators=[DataRequired(), validators.Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField(label="LET ME IN!")
