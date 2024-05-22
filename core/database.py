import sqlalchemy as db
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import ast

from core import messages


base = declarative_base()
engine = create_engine("sqlite:///bot.db")
Session = sessionmaker(bind=engine)


class Pet(base):
    __tablename__ = "pet"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=True)
    satiety = db.Column(db.Integer, default=100)
    happiness = db.Column(db.Integer, default=100)
    health = db.Column(db.Integer, default=100)
    sleep = db.Column(db.Integer, default=100)
    born = db.Column(db.String, default=datetime.now())
    death = db.Column(db.String, nullable=True)
    data = db.Column(db.String, default="{}")
    state = db.Column(db.String, default="nothing")
    status = db.Column(db.Integer, default="live")


class States(base):
    __tablename__ = "states"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String, nullable=True)


class Stats(base):
    __tablename__ = "stats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    type = db.Column(db.String)


async def get_data(id):
    session = Session()
    pet = session.query(Pet).filter(Pet.id == id).first()
    session.close()
    return ast.literal_eval(pet.data)


async def new_user(user_id):
    session = Session()
    user = session.query(States).filter(States.user_id == user_id).first()
    if not user:
        user = States(user_id=user_id)
        session.add(user)
        session.commit()
        session.close()
        return True, ""
    else:
        session.close()
        return False, messages["errors"]["already_reg"]


async def set_state(id, state):
    session = Session()
    user = session.query(States).filter(States.user_id == id).first()
    if user is not None:
        user.state = state
        session.commit()
    session.close()
