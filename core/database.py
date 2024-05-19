import sqlalchemy as db
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from datetime import datetime


base = declarative_base()
engine = create_engine("sqlite:///bot.db")
Session = sessionmaker(bind=engine)


class User(base):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)


class Pet(base):
    __tablename__ = "pet"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    satiety = db.Column(db.Integer, default=100)
    happiness = db.Column(db.Integer, default=100)
    health = db.Column(db.Integer, default=100)
    sleep = db.Column(db.Integer, default=100)
    born = db.Column(db.String, default=datetime.now())
    death = db.Column(db.String, nullable=True)
    data = db.Column(db.String, nullable=True)
    state = db.Column(db.String, default='nothing')
    status = db.Column(db.Integer, default='live')


class Stats(base):
    __tablename__ = "stats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    type = db.Column(db.String)



async def get_data(id):
    session = Session()
    pet = session.query(Pet).filter(Pet.id == id).first()
    session.close()
    return pet.data