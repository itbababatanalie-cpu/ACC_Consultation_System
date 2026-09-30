# Abuyog Community College - Health Services System (ACC Health Hub)

A scalable, secure, Flask-powered web application built with Role-Based Access Control (RBAC) supporting **Super Admin**, **Medical Expert**, and **Student** roles.

---

## 📁 Project Folder Structure

```
abuyog_cc_health_system/
│
├── app.py                   # Main Flask application & SQLAlchemy database models
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation & run setup guide
│
├── static/
│   └── css/
│       └── style.css        # Custom Deep Purple & Slate styling system
│
└── templates/
    ├── base.html            # Core layout with RBAC-driven dynamic navbar
    ├── index.html           # Public Landing Page & Health Advisories
    ├── login.html           # Authentication portal with demo logins
    ├── dashboard.html       # Role-specific dashboard layouts
    ├── admin_users.html     # Super Admin user management panel
    ├── admin_logs.html      # Audit trail & system logging viewer
    ├── medical_records.html # Clinical history & diagnosis registry
    ├── medical_requests.html# Student appointment & certificate triage
    ├── student_request.html # Student health request submission form
    └── profile.html         # User account settings
```

---

## ⚙️ Setup and Installation

### 1. Create a Virtual Environment
```bash
python -m venv venv
```

Activate the virtual environment:
- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database & Run App
```bash
python app.py
```
*Note: Running `python app.py` will automatically create the SQLite database (`acc_health.db`) and seed demo accounts.*

Access the app in your browser at: `http://127.0.0.1:5000`

---

## 🔑 Demo Account Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Super Admin** | `admin@acc.edu.ph` | `Admin123!` |
| **Medical Expert** | `doctor@acc.edu.ph` | `Doctor123!` |
| **Student** | `student@acc.edu.ph` | `Student123!` |

---

## 🔒 How RBAC Logic Works & Adding New Roles

1. **Role Definition**: Roles are defined on the `User` SQLAlchemy model via string constants or an Enum (`Role.SUPER_ADMIN`, `Role.MEDICAL_EXPERT`, `Role.STUDENT`).
2. **Custom RBAC Decorator**: The `@roles_required(*roles)` decorator inspects `current_user.role`. If the authenticated user does not possess one of the allowed roles, access is rejected with a `403` error/flash message redirect.
3. **Template Context Control**: Jinja templates check `current_user.has_role('RoleName')` to dynamically render accessible menu items, action buttons, and navigation sections.

### How to Add a New Role in the Future:
1. Open `app.py` and add the constant to the `Role` class:
   ```python
   class Role:
       SUPER_ADMIN = 'Super Admin'
       MEDICAL_EXPERT = 'Medical Expert'
       STUDENT = 'Student'
       NURSE = 'Nurse' # New Role
   ```
2. Decorate new endpoints with the new role name:
   ```python
   @app.route('/nurse/triage')
   @login_required
   @roles_required(Role.NURSE, Role.MEDICAL_EXPERT)
   def nurse_triage():
       return render_template('nurse_triage.html')
   ```
3. Update Jinja navigation conditionals in `templates/base.html` to display UI features for the new role.
