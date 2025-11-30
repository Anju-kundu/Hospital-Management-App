from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os

app = Flask(__name__)

# ============================================ Configuration ============================================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "hospital_secret_key_secure_2025"

db = SQLAlchemy(app)


# ============================================ Models ============================================

class Department(db.Model):
    __tablename__ = 'departments'

    dep_id = db.Column(db.Integer, primary_key=True)
    dep_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctors = db.relationship("User", back_populates="department", foreign_keys="User.department_id")

    def __repr__(self):
        return f"<Department {self.dep_name}>"


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(50), nullable=False)  # admin, doctor, patient
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # For doctors: department they work in
    department_id = db.Column(db.Integer, db.ForeignKey('departments.dep_id'), nullable=True)
    department = db.relationship("Department", back_populates="doctors", foreign_keys=[department_id])

    # For doctors: specialization
    specialization = db.Column(db.String(150), nullable=True)

    # Relationships
    appointments_as_doctor = db.relationship("Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id")
    appointments_as_patient = db.relationship("Appointment", back_populates="patient", foreign_keys="Appointment.patient_id")
    availabilities = db.relationship("Availability", back_populates="doctor", cascade="all, delete-orphan")
    treatments = db.relationship("Treatment", back_populates="doctor")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(50), default='Booked', nullable=False)  # Booked, Completed, Cancelled
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship("User", back_populates="appointments_as_patient", foreign_keys=[patient_id])
    doctor = db.relationship("User", back_populates="appointments_as_doctor", foreign_keys=[doctor_id])
    treatment = db.relationship("Treatment", back_populates="appointment", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appointment {self.patient.full_name} -> {self.doctor.full_name}>"


class Treatment(db.Model):
    __tablename__ = 'treatment'

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    appointment = db.relationship("Appointment", back_populates="treatment")
    doctor = db.relationship("User", back_populates="treatments")

    def __repr__(self):
        return f"<Treatment for Appointment {self.appointment_id}>"


class Availability(db.Model):
    __tablename__ = 'availability'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    available_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship("User", back_populates="availabilities")

    def __repr__(self):
        return f"<Availability {self.doctor.full_name} on {self.available_date}>"


# ============================================ Authentication Helper ============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            flash('You do not have admin access.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.role != 'doctor':
            flash('You do not have doctor access.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.role != 'patient':
            flash('You do not have patient access.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================ Public Routes ============================================

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            session['user_id'] = user.id
            session['role'] = user.role
            flash(f'Welcome back, {user.full_name}!', 'success')

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials or account is inactive.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')

        # Validation
        if not all([username, email, password, confirm_password, full_name]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('register'))

        # Create patient user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            phone=phone,
            role='patient'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ============================================ Admin Routes ============================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_doctors = User.query.filter_by(role='doctor', is_active=True).count()
    total_patients = User.query.filter_by(role='patient', is_active=True).count()
    total_appointments = Appointment.query.count()
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status != 'Cancelled'
    ).count()

    return render_template('admin_dashboard.html',
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         upcoming_appointments=upcoming_appointments)


@app.route('/admin/doctors', methods=['GET', 'POST'])
@admin_required
def admin_doctors():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            username = request.form.get('username')
            specialization = request.form.get('specialization')
            department_id = request.form.get('department_id')
            phone = request.form.get('phone')

            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
            else:
                doctor = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    phone=phone,
                    role='doctor',
                    department_id=int(department_id) if department_id else None,
                    specialization=specialization
                )
                doctor.set_password('default123')  # Default password
                db.session.add(doctor)
                db.session.commit()
                flash('Doctor added successfully!', 'success')

        elif action == 'update':
            doctor_id = request.form.get('doctor_id')
            doctor = User.query.get(doctor_id)
            if doctor:
                doctor.full_name = request.form.get('full_name')
                doctor.email = request.form.get('email')
                doctor.specialization = request.form.get('specialization')
                doctor.department_id = int(request.form.get('department_id')) if request.form.get('department_id') else None
                doctor.phone = request.form.get('phone')
                db.session.commit()
                flash('Doctor updated successfully!', 'success')

        elif action == 'delete':
            doctor_id = request.form.get('doctor_id')
            doctor = User.query.get(doctor_id)
            if doctor:
                doctor.is_active = False
                db.session.commit()
                flash('Doctor removed from system.', 'success')

        return redirect(url_for('admin_doctors'))

    departments = Department.query.all()
    doctors = User.query.filter_by(role='doctor', is_active=True).all()

    return render_template('admin_doctors.html', doctors=doctors, departments=departments)


@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    appointments = Appointment.query.all()
    return render_template('admin_appointments.html', appointments=appointments)


@app.route('/admin/appointments/<int:appointment_id>/status', methods=['POST'])
@admin_required
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    new_status = request.form.get('status')

    if appointment:
        appointment.status = new_status
        db.session.commit()
        flash('Appointment status updated.', 'success')

    return redirect(url_for('admin_appointments'))


@app.route('/admin/search', methods=['GET', 'POST'])
@admin_required
def admin_search():
    results = []
    search_type = None
    search_query = None

    if request.method == 'POST':
        search_type = request.form.get('search_type')  # doctor or patient
        search_query = request.form.get('search_query')

        if search_type == 'doctor':
            results = User.query.filter(
                User.role == 'doctor',
                User.is_active == True,
                (User.full_name.ilike(f'%{search_query}%') | User.specialization.ilike(f'%{search_query}%'))
            ).all()
        elif search_type == 'patient':
            results = User.query.filter(
                User.role == 'patient',
                User.is_active == True,
                (User.full_name.ilike(f'%{search_query}%') | User.email.ilike(f'%{search_query}%'))
            ).all()

    return render_template('admin_search.html', results=results, search_type=search_type, search_query=search_query)


# ============================================ Doctor Routes ============================================

@app.route('/doctor/dashboard')
@doctor_required
def doctor_dashboard():
    doctor_id = session['user_id']
    doctor = User.query.get(doctor_id)

    today = datetime.now().date()
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date >= today,
        Appointment.status != 'Cancelled'
    ).all()

    total_patients = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == doctor_id
    ).distinct().count()

    completed_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == 'Completed'
    ).count()

    return render_template('doctor_dashboard.html',
                         doctor=doctor,
                         upcoming_appointments=upcoming_appointments,
                         total_patients=total_patients,
                         completed_appointments=completed_appointments)


@app.route('/doctor/appointments')
@doctor_required
def doctor_appointments():
    doctor_id = session['user_id']
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
    return render_template('doctor_appointments.html', appointments=appointments)


@app.route('/doctor/appointments/<int:appointment_id>/update', methods=['POST'])
@doctor_required
def doctor_update_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)

    if appointment and appointment.doctor_id == session['user_id']:
        new_status = request.form.get('status')
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')

        appointment.status = new_status

        # Create/update treatment record if appointment is completed
        if new_status == 'Completed':
            treatment = Treatment.query.filter_by(appointment_id=appointment_id).first()
            if not treatment:
                treatment = Treatment(appointment_id=appointment_id, doctor_id=session['user_id'])
            treatment.diagnosis = diagnosis
            treatment.prescription = prescription
            treatment.notes = notes
            db.session.add(treatment)

        db.session.commit()
        flash('Appointment updated successfully!', 'success')

    return redirect(url_for('doctor_appointments'))


@app.route('/doctor/availability', methods=['GET', 'POST'])
@doctor_required
def doctor_availability():
    doctor_id = session['user_id']

    if request.method == 'POST':
        available_date = request.form.get('available_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        # Convert to Python types
        date_obj = datetime.strptime(available_date, '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()

        availability = Availability(
            doctor_id=doctor_id,
            available_date=date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj
        )
        db.session.add(availability)
        db.session.commit()
        flash('Availability added successfully!', 'success')

    availabilities = Availability.query.filter_by(doctor_id=doctor_id).all()
    return render_template('doctor_availability.html', availabilities=availabilities)


@app.route('/doctor/patient-history/<int:patient_id>')
@doctor_required
def doctor_patient_history(patient_id):
    doctor_id = session['user_id']

    # Verify doctor has treated this patient
    appointment = Appointment.query.filter_by(doctor_id=doctor_id, patient_id=patient_id).first()
    if not appointment:
        flash('You do not have access to this patient.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    patient = User.query.get(patient_id)
    treatments = Treatment.query.filter(
        Treatment.doctor_id == doctor_id,
        Appointment.patient_id == patient_id
    ).join(Appointment).all()

    return render_template('doctor_patient_history.html', patient=patient, treatments=treatments)


# ============================================ Patient Routes ============================================

@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    patient_id = session['user_id']
    patient = User.query.get(patient_id)

    today = datetime.now().date()
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.appointment_date >= today,
        Appointment.status != 'Cancelled'
    ).all()

    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.appointment_date < today
    ).all()

    departments = Department.query.all()

    return render_template('patient_dashboard.html',
                         patient=patient,
                         upcoming_appointments=upcoming_appointments,
                         past_appointments=past_appointments,
                         departments=departments)


@app.route('/patient/book-appointment', methods=['GET', 'POST'])
@patient_required
def patient_book_appointment():
    patient_id = session['user_id']

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        reason = request.form.get('reason')

        # Check for conflicts
        date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        time_obj = datetime.strptime(appointment_time, '%H:%M').time()

        conflict = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == date_obj,
            Appointment.appointment_time == time_obj,
            Appointment.status != 'Cancelled'
        ).first()

        if conflict:
            flash('This time slot is already booked. Please choose another.', 'warning')
        else:
            appointment = Appointment(
                patient_id=patient_id,
                doctor_id=int(doctor_id),
                appointment_date=date_obj,
                appointment_time=time_obj,
                reason=reason,
                status='Booked'
            )
            db.session.add(appointment)
            db.session.commit()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient_appointments'))

    departments = Department.query.all()
    return render_template('patient_book_appointment.html', departments=departments)


@app.route('/patient/doctors-by-department/<int:department_id>')
@patient_required
def get_doctors_by_department(department_id):
    doctors = User.query.filter_by(department_id=department_id, role='doctor', is_active=True).all()
    return jsonify([{'id': d.id, 'name': d.full_name, 'specialization': d.specialization} for d in doctors])


@app.route('/patient/appointments')
@patient_required
def patient_appointments():
    patient_id = session['user_id']
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    return render_template('patient_appointments.html', appointments=appointments)


@app.route('/patient/appointments/<int:appointment_id>/cancel', methods=['POST'])
@patient_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)

    if appointment and appointment.patient_id == session['user_id'] and appointment.status != 'Cancelled':
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')

    return redirect(url_for('patient_appointments'))


@app.route('/patient/treatment-history')
@patient_required
def patient_treatment_history():
    patient_id = session['user_id']

    appointments = Appointment.query.filter_by(patient_id=patient_id, status='Completed').all()
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()

    return render_template('patient_treatment_history.html', appointments=appointments, treatments=treatments)


@app.route('/patient/profile', methods=['GET', 'POST'])
@patient_required
def patient_profile():
    patient = User.query.get(session['user_id'])

    if request.method == 'POST':
        patient.full_name = request.form.get('full_name')
        patient.email = request.form.get('email')
        patient.phone = request.form.get('phone')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient_profile'))

    return render_template('patient_profile.html', patient=patient)


# ============================================ API Routes (Optional) ============================================

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    if request.method == 'GET':
        appointments = Appointment.query.all()
        return jsonify([{
            'id': a.id,
            'patient': a.patient.full_name,
            'doctor': a.doctor.full_name,
            'date': str(a.appointment_date),
            'time': str(a.appointment_time),
            'status': a.status
        } for a in appointments])

    elif request.method == 'POST':
        data = request.get_json()
        appointment = Appointment(
            patient_id=data['patient_id'],
            doctor_id=data['doctor_id'],
            appointment_date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            appointment_time=datetime.strptime(data['time'], '%H:%M').time(),
            status='Booked'
        )
        db.session.add(appointment)
        db.session.commit()
        return jsonify({'message': 'Appointment created', 'id': appointment.id}), 201


@app.route('/api/doctors', methods=['GET'])
def api_doctors():
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    return jsonify([{
        'id': d.id,
        'name': d.full_name,
        'specialization': d.specialization,
        'department': d.department.dep_name if d.department else 'N/A'
    } for d in doctors])


@app.route('/api/patients', methods=['GET'])
def api_patients():
    patients = User.query.filter_by(role='patient', is_active=True).all()
    return jsonify([{
        'id': p.id,
        'name': p.full_name,
        'email': p.email,
        'phone': p.phone
    } for p in patients])


# ============================================ Error Handlers ============================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    flash('An internal error occurred.', 'danger')
    return render_template('index.html', error='Internal server error'), 500


# ============================================ Entry Point ============================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Create default departments
        departments_data = [
            {'name': 'Cardiology', 'desc': 'Heart and circulatory system'},
            {'name': 'Neurology', 'desc': 'Brain and nervous system'},
            {'name': 'Dermatology', 'desc': 'Skin and hair'},
            {'name': 'Orthopedics', 'desc': 'Bones and joints'},
            {'name': 'Pediatrics', 'desc': 'Child health'},
        ]

        for dept_data in departments_data:
            if not Department.query.filter_by(dep_name=dept_data['name']).first():
                dept = Department(dep_name=dept_data['name'], description=dept_data['desc'])
                db.session.add(dept)
        db.session.commit()

        # Create admin user
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@hospital.com',
                full_name='Hospital Administrator',
                phone='9999999999',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
