import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abuyog-community-college-health-hub-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///acc_health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# --- MODELS ---

class Role:
    SUPER_ADMIN = 'Super Admin'
    MEDICAL_EXPERT = 'Medical Expert'
    STUDENT = 'Student'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=True) # E.g., ACC-2026-0001
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default=Role.STUDENT)
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    medical_records = db.relationship('MedicalRecord', backref='student', lazy=True, foreign_keys='MedicalRecord.student_id')
    health_requests = db.relationship('HealthRequest', backref='student', lazy=True, foreign_keys='HealthRequest.student_id')
    logs = db.relationship('SystemLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blood_type = db.Column(db.String(10), nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    pre_existing_conditions = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    recorded_by = db.relationship('User', foreign_keys=[recorded_by_id])


class HealthRequest(db.Model):
    __tablename__ = 'health_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_type = db.Column(db.String(100), nullable=False) # e.g., Medical Certificate, Consultation, Dental Checkup
    reason = db.Column(db.Text, nullable=False)
    preferred_date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default='Pending') # Pending, Approved, Rejected, Completed
    doctor_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(50), default='General Health')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User')


class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- RBAC DECORATOR ---

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if not current_user.has_role(*roles):
                flash('Access Denied: You do not have permission to view this resource.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_action(action_text):
    user_id = current_user.id if current_user.is_authenticated else None
    client_ip = request.remote_addr
    new_log = SystemLog(user_id=user_id, action=action_text, ip_address=client_ip)
    db.session.add(new_log)
    db.session.commit()


# --- ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()
    return render_template('index.html', announcements=announcements)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active_account:
                flash('Your account has been deactivated. Please contact the Super Admin.', 'danger')
                return redirect(url_for('login'))
            login_user(user)
            log_action(f"User logged in ({user.role})")
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    log_action(f"User logged out ({current_user.full_name})")
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    
    if current_user.role == Role.SUPER_ADMIN:
        total_users = User.query.count()
        total_students = User.query.filter_by(role=Role.STUDENT).count()
        total_experts = User.query.filter_by(role=Role.MEDICAL_EXPERT).count()
        total_records = MedicalRecord.query.count()
        logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(10).all()
        return render_template('dashboard.html', 
                               total_users=total_users, 
                               total_students=total_students, 
                               total_experts=total_experts,
                               total_records=total_records,
                               logs=logs,
                               announcements=announcements)
                               
    elif current_user.role == Role.MEDICAL_EXPERT:
        pending_requests = HealthRequest.query.filter_by(status='Pending').count()
        total_records = MedicalRecord.query.count()
        recent_requests = HealthRequest.query.order_by(HealthRequest.created_at.desc()).limit(5).all()
        return render_template('dashboard.html', 
                               pending_requests=pending_requests, 
                               total_records=total_records,
                               recent_requests=recent_requests,
                               announcements=announcements)
                               
    else: # Student
        my_records = MedicalRecord.query.filter_by(student_id=current_user.id).order_by(MedicalRecord.created_at.desc()).all()
        my_requests = HealthRequest.query.filter_by(student_id=current_user.id).order_by(HealthRequest.created_at.desc()).all()
        return render_template('dashboard.html', 
                               my_records=my_records, 
                               my_requests=my_requests,
                               announcements=announcements)


# --- SUPER ADMIN ROUTES ---

@app.route('/admin/users')
@login_required
@roles_required(Role.SUPER_ADMIN)
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/create', methods=['POST'])
@login_required
@roles_required(Role.SUPER_ADMIN)
def admin_create_user():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    student_id = request.form.get('student_id') or None
    role = request.form.get('role')
    password = request.form.get('password')
    
    if User.query.filter_by(email=email).first():
        flash('Email address is already registered!', 'danger')
        return redirect(url_for('admin_users'))
        
    new_user = User(
        full_name=full_name,
        email=email,
        student_id=student_id,
        role=role
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    log_action(f"Created new user: {email} with role {role}")
    flash(f'Account created successfully for {full_name}.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@roles_required(Role.SUPER_ADMIN)
def admin_toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own admin account.', 'warning')
        return redirect(url_for('admin_users'))
        
    user.is_active_account = not user.is_active_account
    db.session.commit()
    status_str = "activated" if user.is_active_account else "deactivated"
    log_action(f"User {user.email} was {status_str}")
    flash(f"User {user.full_name} has been {status_str}.", "info")
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@roles_required(Role.SUPER_ADMIN)
def admin_change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'warning')
        return redirect(url_for('admin_users'))
        
    old_role = user.role
    user.role = new_role
    db.session.commit()
    log_action(f"Changed role for {user.email} from {old_role} to {new_role}")
    flash(f"Role updated for {user.full_name} to {new_role}.", "success")
    return redirect(url_for('admin_users'))


@app.route('/admin/logs')
@login_required
@roles_required(Role.SUPER_ADMIN)
def admin_logs():
    logs = SystemLog.query.order_by(SystemLog.created_at.desc()).all()
    return render_template('admin_logs.html', logs=logs)


# --- MEDICAL EXPERT ROUTES ---

@app.route('/medical/records')
@login_required
@roles_required(Role.MEDICAL_EXPERT, Role.SUPER_ADMIN)
def medical_records():
    students = User.query.filter_by(role=Role.STUDENT).all()
    records = MedicalRecord.query.order_by(MedicalRecord.created_at.desc()).all()
    return render_template('medical_records.html', students=students, records=records)


@app.route('/medical/records/create', methods=['POST'])
@login_required
@roles_required(Role.MEDICAL_EXPERT)
def create_medical_record():
    student_id = request.form.get('student_id')
    blood_type = request.form.get('blood_type')
    height_cm = request.form.get('height_cm')
    weight_kg = request.form.get('weight_kg')
    allergies = request.form.get('allergies')
    pre_existing = request.form.get('pre_existing_conditions')
    diagnosis = request.form.get('diagnosis')
    treatment = request.form.get('treatment')
    remarks = request.form.get('remarks')
    
    rec = MedicalRecord(
        student_id=student_id,
        recorded_by_id=current_user.id,
        blood_type=blood_type,
        height_cm=float(height_cm) if height_cm else None,
        weight_kg=float(weight_kg) if weight_kg else None,
        allergies=allergies,
        pre_existing_conditions=pre_existing,
        diagnosis=diagnosis,
        treatment=treatment,
        remarks=remarks
    )
    db.session.add(rec)
    db.session.commit()
    log_action(f"Created medical record for Student ID {student_id}")
    flash('Medical record added successfully.', 'success')
    return redirect(url_for('medical_records'))


@app.route('/medical/requests')
@login_required
@roles_required(Role.MEDICAL_EXPERT, Role.SUPER_ADMIN)
def medical_requests():
    requests = HealthRequest.query.order_by(HealthRequest.created_at.desc()).all()
    return render_template('medical_requests.html', requests=requests)


@app.route('/medical/requests/<int:req_id>/update', methods=['POST'])
@login_required
@roles_required(Role.MEDICAL_EXPERT)
def update_health_request(req_id):
    h_req = HealthRequest.query.get_or_404(req_id)
    status = request.form.get('status')
    doctor_notes = request.form.get('doctor_notes')
    
    h_req.status = status
    h_req.doctor_notes = doctor_notes
    db.session.commit()
    log_action(f"Updated request #{req_id} status to {status}")
    flash(f"Health request status set to {status}.", "success")
    return redirect(url_for('medical_requests'))


# --- ANNOUNCEMENTS ---

@app.route('/announcements/create', methods=['POST'])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.MEDICAL_EXPERT)
def create_announcement():
    title = request.form.get('title')
    content = request.form.get('content')
    category = request.form.get('category', 'General Health')
    
    ann = Announcement(
        title=title,
        content=content,
        category=category,
        author_id=current_user.id
    )
    db.session.add(ann)
    db.session.commit()
    log_action(f"Created announcement: {title}")
    flash('Announcement posted successfully.', 'success')
    return redirect(url_for('dashboard'))


# --- STUDENT ROUTES ---

@app.route('/student/request', methods=['GET', 'POST'])
@login_required
@roles_required(Role.STUDENT)
def student_submit_request():
    if request.method == 'POST':
        request_type = request.form.get('request_type')
        reason = request.form.get('reason')
        preferred_date = request.form.get('preferred_date')
        
        req = HealthRequest(
            student_id=current_user.id,
            request_type=request_type,
            reason=reason,
            preferred_date=preferred_date
        )
        db.session.add(req)
        db.session.commit()
        log_action(f"Student submitted request: {request_type}")
        flash('Your health request/appointment has been submitted.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('student_request.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
        db.session.commit()
        log_action("User updated profile settings")
        flash("Profile updated successfully.", "success")
        return redirect(url_for('profile'))
        
    return render_template('profile.html')


# --- INITIALIZE DATABASE SEED DATA ---

def init_db():
    with app.app_context():
        db.create_all()
        
        # Check if users exist
        if User.query.count() == 0:
            # Seed Super Admin
            admin = User(
                full_name="Dr. Admin Abuyog",
                email="admin@acc.edu.ph",
                role=Role.SUPER_ADMIN
            )
            admin.set_password("Admin123!")
            
            # Seed Medical Expert
            doctor = User(
                full_name="Dr. Maria Clara, MD",
                email="doctor@acc.edu.ph",
                role=Role.MEDICAL_EXPERT
            )
            doctor.set_password("Doctor123!")
            
            # Seed Student
            student = User(
                student_id="ACC-2026-0001",
                full_name="Juan Cruz",
                email="student@acc.edu.ph",
                role=Role.STUDENT
            )
            student.set_password("Student123!")
            
            db.session.add_all([admin, doctor, student])
            db.session.commit()
            
            # Initial Announcement
            ann = Announcement(
                title="Annual Medical Examination & Blood Drive 2026",
                content="Welcome to the Abuyog Community College Health Hub! Annual physical examinations for all 1st year students will commence next Monday at the ACC Clinic.",
                category="Campus Advisory",
                author_id=admin.id
            )
            db.session.add(ann)
            
            # Initial Medical Record
            med = MedicalRecord(
                student_id=student.id,
                recorded_by_id=doctor.id,
                blood_type="O+",
                height_cm=170.0,
                weight_kg=65.5,
                allergies="Penicillin",
                pre_existing_conditions="Mild Asthma",
                diagnosis="Routine Health Clearance",
                treatment="Prescribed Multivitamins & Inhaler refill",
                remarks="Cleared for college athletics."
            )
            db.session.add(med)
            
            # Initial Health Request
            req = HealthRequest(
                student_id=student.id,
                request_type="Medical Certificate Request",
                reason="Required for ROTC / P.E. exemption due to mild asthma.",
                preferred_date="2026-10-05",
                status="Approved",
                doctor_notes="Granted PE modified activity clearance."
            )
            db.session.add(req)
            db.session.commit()
            print("Database initialized and seeded successfully!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
