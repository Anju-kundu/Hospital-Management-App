from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask import render_template,request,redirect,url_for,session


app = Flask(__name__)
app.secret_key = "143"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
db = SQLAlchemy(app)


# ----------------------------------------models------------------------------
from datetime import datetime
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer,primary_key = True)
    username = db.Column(db.String(150),unique=True,nullable = False)
    email = db.Column(db.String(150),unique=True,nullable = False)
    password = db.Column(db.String(150),nullable = False)
    role = db.Column(db.String(150),nullable = False)
    created_at = db.Column(db.DateTime, default = datetime.utcnow)

    department_id = db.Column(db.Integer,db.ForeignKey('departments.dep_id'),nullable=False)



    # reverse realtionship
    department = db.relationship("Department",back_populates="doctors")




class Department(db.Model):
    __tablename__ = 'departments'

    dep_id = db.Column(db.Integer,primary_key = True)
    dep_name = db.Column(db.String(80),unique=True,nullable = False)
    description = db.Column(db.Text,nullable = True)
    doctors = db.relationship("User",back_populates="department")


class Appointement(db.Model):
    __tablename__ = 'appointements'

    id = db.Column(db.Integer,primary_key = True)
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    status = db.Column(db.String(20),default = 'Booked') # pending,cenceld,booked

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    treatment_id = db.Column(db.Integer,db.ForeignKey('treatment.id'))


class Treatment(db.Model):
    __tablename__ = 'treatment'
    id = db.Column(db.Integer,primary_key = True)
    treatment_name = db.Column(db.String(150))
    description = db.Column(db.Text,nullable = True)



@app.route('/')
def base():
    return render_template('index.html')

@app.route('/login')
def index():
    return render_template('login.html')






if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        existing_admin = User.query.filter_by(username ="admin").first()
        if not existing_admin:
            admin_db = User(
                username = "admin",
                password = "admin",
                email = "143@gmail.com",
                role = "admin",
                department_id="unknown"
            )
            # dep = Department(name="Administration")
            db.session.add(admin_db)
            db.session.commit()
    app.run(debug=True)