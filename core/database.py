import sqlalchemy as db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import ast
import ast

from core import messages


Base = declarative_base()
engine_db = create_async_engine("sqlite+aiosqlite:///bot.db", echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine_db, class_=AsyncSession, expire_on_commit=False
)


class Pet(Base):
    __tablename__ = "pet"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=True)
    health = db.Column(db.Float, default=100)
    satiety = db.Column(db.Float, default=100)
    happiness = db.Column(db.Float, default=100)
    sleep = db.Column(db.Float, default=100)
    born = db.Column(db.String, nullable=True)
    death = db.Column(db.String, nullable=True)
    data = db.Column(db.String, default="{}")
    inventory = db.Column(db.String, default="{}")
    level = db.Column(db.Integer, default=1)
    experience = db.Column(db.Integer, default=0)
    state = db.Column(db.String, default="nothing")
    status = db.Column(db.Integer, default="hatching")


class States(Base):
    __tablename__ = "states"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String, nullable=True)
    current_page = db.Column(db.Integer, default=1)
    current_category = db.Column(db.String, nullable=True)
    msg_for_delete = db.Column(db.Integer, nullable=True)


class Stats(Base):
    __tablename__ = "stats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    type = db.Column(db.String)


async def get_data(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()
        if pet:
            return ast.literal_eval(pet.data)
        return {}


async def get_inventory(id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(Pet).filter(Pet.id == id))
        pet = result.scalar_one_or_none()
        if pet:
            return ast.literal_eval(pet.inventory)
        return {}


async def new_user(user_id):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            db.select(States).filter(States.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        result = await session.execute(db.select(Pet).filter(Pet.user_id == user_id))
        pet = result.scalar_one_or_none()
        if not pet:
            if not user:
                user = States(user_id=user_id)
                session.add(user)
                await session.commit()
            return True, ""
        return False, messages["errors"]["already_reg"]


async def set_state(id, state):
    async with AsyncSessionLocal() as session:
        result = await session.execute(db.select(States).filter(States.user_id == id))
        user = result.scalar_one_or_none()
        if user:
            user.state = state
            await session.commit()
