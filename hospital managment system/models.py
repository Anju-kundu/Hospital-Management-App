from app import db
from datetime import datetime
class User(db.Model):
    __tablename__ = 'users'
    # specialization_id = db.column(db.Integer,db.ForeignKey('departments.dep_id'),nullable = True)
    id = db.column(db.Integer,primary_key = True)
    username = db.column(db.String(150),unique=True,nullable = False)
    email = db.column(db.String(150),unique=True,nullable = False)
    password = db.column(db.String(150),nullable = False)
    role = db.column(db.String(150),nullable = False)
    created_at = db.column(db.DateTime,defult = datetime.utcnow)
    department_id = db.column(db.Integer,db.ForeignKey('Dep.dep_id'),nullable=False)

class Dep(db.Model):
    __tablename__ = 'departments'
    dep_id = db.column(db.Integer,primary_key = True)
    dep_name = db.column(db.String(80),unique=True,nullable = False)
    description = db.column(db.Text,nullable = True)


class Appointement(db.Model):
    __tablename__ = 'appointements'
    id = db.column(db.Integer,primary_key = True)
    date = db.column(db.String(20))
    time = db.column(db.String(20))
    status = db.column(db.String(20),defult = 'Booked') # pending,cenceld,booked
