from core.database import Pet, Session


session = Session()

pet = Pet(user_id=12345678, name="Oleg")

session.add(pet)
session.commit()
session.close()
