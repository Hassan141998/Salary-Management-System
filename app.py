from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta, timezone
import csv
from io import StringIO, BytesIO
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rass-cuisine-secret-key-change-this-in-production')

# Database Configuration - PostgreSQL for Production, SQLite for Local
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Production: Use PostgreSQL (Neon)
    # Fix for SQLAlchemy 1.4+ compatibility with postgres:// URLs
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local Development: Use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rass_salary.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.Float, nullable=False)
    join_date = db.Column(db.Date, nullable=False)
    salary_payment_date = db.Column(db.Date, nullable=True)  # Made optional
    total_withdrawn = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)  # Made optional
    
    transactions = db.relationship('Transaction', backref='employee', lazy=True, cascade='all, delete-orphan')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)  # Will be set manually with Pakistan time
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Timezone Helper Function (Using Built-in timezone - No pytz needed!)
# Pakistan Standard Time is UTC+5 (no daylight saving)
PKT = timezone(timedelta(hours=5))

def get_pakistan_time():
    """Get current time in Pakistan timezone (PKT = UTC+5)"""
    utc_now = datetime.now(timezone.utc)
    pakistan_time = utc_now.astimezone(PKT)
    return pakistan_time

def get_pakistan_datetime():
    """Get current datetime in Pakistan timezone"""
    return get_pakistan_time()

def get_pakistan_date():
    """Get current date in Pakistan timezone"""
    return get_pakistan_time().date()

def get_pakistan_time_only():
    """Get current time only in Pakistan timezone"""
    return get_pakistan_time().time()

# PDF Generation Helper Functions
def generate_withdrawal_slip_pdf(transaction, employee):
    """Generate a withdrawal slip PDF for a single transaction"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#f97316'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12
    )
    
    # Header
    title = Paragraph("RASS CUISINE RESTAURANT", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Salary Withdrawal Slip", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.3*inch))
    
    # Slip Details
    # Format time properly
    time_str = 'N/A'
    if transaction.time:
        time_str = transaction.time.strftime('%I:%M %p')
    
    slip_data = [
        ['Slip No:', f"WS-{transaction.id:06d}"],
        ['Date & Time:', f"{transaction.date.strftime('%d %B %Y')} at {time_str}"],
        ['Generated On:', get_pakistan_time().strftime('%d %B %Y, %I:%M %p')],
    ]
    
    slip_table = Table(slip_data, colWidths=[2*inch, 4*inch])
    slip_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(slip_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Employee Details
    elements.append(Paragraph("Employee Information", heading_style))
    
    emp_data = [
        ['Employee Name:', employee.name],
        ['Designation:', employee.designation],
        ['Employee ID:', f"EMP-{employee.id:04d}"],
        ['Join Date:', employee.join_date.strftime('%d %B %Y')],
    ]
    
    emp_table = Table(emp_data, colWidths=[2*inch, 4*inch])
    emp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4b5563')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Salary Details
    elements.append(Paragraph("Salary Details", heading_style))
    
    salary_data = [
        ['Description', 'Amount (Rs)'],
        ['Monthly Salary', f"{employee.salary:,.2f}"],
        ['Previous Withdrawals', f"{employee.total_withdrawn - transaction.amount:,.2f}"],
        ['Current Withdrawal', f"{transaction.amount:,.2f}"],
        ['Remaining Balance', f"{employee.salary - employee.total_withdrawn:,.2f}"],
    ]
    
    salary_table = Table(salary_data, colWidths=[3*inch, 2*inch])
    salary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f97316')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(salary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Notes
    if transaction.notes:
        elements.append(Paragraph(f"<b>Notes:</b> {transaction.notes}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
    
    # Signature Section
    elements.append(Spacer(1, 0.5*inch))
    
    sig_data = [
        ['_____________________', '_____________________'],
        ['Employee Signature', 'Authorized Signature'],
    ]
    
    sig_table = Table(sig_data, colWidths=[3*inch, 3*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 5),
    ]))
    elements.append(sig_table)
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = "This is a computer-generated document. No signature required."
    footer = Paragraph(f"<i>{footer_text}</i>", styles['Normal'])
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_employee_history_pdf(employee):
    """Generate complete salary history PDF for an employee"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#f97316'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    title = Paragraph("RASS CUISINE RESTAURANT", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Employee Salary History Report", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.2*inch))
    
    # Employee Info
    emp_info = f"""
    <b>Employee Name:</b> {employee.name}<br/>
    <b>Designation:</b> {employee.designation}<br/>
    <b>Employee ID:</b> EMP-{employee.id:04d}<br/>
    <b>Join Date:</b> {employee.join_date.strftime('%d %B %Y')}<br/>
    <b>Monthly Salary:</b> Rs {employee.salary:,.2f}<br/>
    <b>Report Generated:</b> {datetime.now().strftime('%d %B %Y, %I:%M %p')}
    """
    elements.append(Paragraph(emp_info, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary
    summary_data = [
        ['Total Salary', f"Rs {employee.salary:,.2f}"],
        ['Total Withdrawn', f"Rs {employee.total_withdrawn:,.2f}"],
        ['Remaining Balance', f"Rs {employee.salary - employee.total_withdrawn:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Transaction History
    if employee.transactions:
        elements.append(Paragraph("<b>Withdrawal History</b>", styles['Heading3']))
        elements.append(Spacer(1, 0.1*inch))
        
        trans_data = [['Date', 'Time', 'Amount (Rs)', 'Notes']]
        for trans in sorted(employee.transactions, key=lambda x: x.date, reverse=True):
            trans_data.append([
                trans.date.strftime('%d %b %Y'),
                trans.time.strftime('%I:%M %p') if trans.time else 'N/A',
                f"{trans.amount:,.2f}",
                trans.notes[:30] + '...' if trans.notes and len(trans.notes) > 30 else (trans.notes or '-')
            ])
        
        trans_table = Table(trans_data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 2.3*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f97316')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(trans_table)
    else:
        elements.append(Paragraph("No withdrawal history available.", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_monthly_report_pdf(month, year):
    """Generate monthly salary report for all employees"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#f97316'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    month_name = datetime(year, month, 1).strftime('%B %Y')
    
    title = Paragraph("RASS CUISINE RESTAURANT", title_style)
    elements.append(title)
    
    subtitle = Paragraph(f"Monthly Salary Report - {month_name}", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.2*inch))
    
    # Report info
    report_info = f"<b>Report Generated:</b> {datetime.now().strftime('%d %B %Y, %I:%M %p')}"
    elements.append(Paragraph(report_info, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Get all transactions for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    transactions = Transaction.query.filter(
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).order_by(Transaction.date.desc()).all()
    
    if transactions:
        # Summary
        total_withdrawn = sum(t.amount for t in transactions)
        elements.append(Paragraph(f"<b>Total Withdrawals This Month:</b> Rs {total_withdrawn:,.2f}", styles['Heading3']))
        elements.append(Paragraph(f"<b>Total Transactions:</b> {len(transactions)}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Transaction table
        trans_data = [['Date', 'Employee', 'Designation', 'Amount (Rs)', 'Notes']]
        for trans in transactions:
            trans_data.append([
                trans.date.strftime('%d %b'),
                trans.employee.name,
                trans.employee.designation,
                f"{trans.amount:,.2f}",
                trans.notes[:20] + '...' if trans.notes and len(trans.notes) > 20 else (trans.notes or '-')
            ])
        
        trans_table = Table(trans_data, colWidths=[1*inch, 1.8*inch, 1.5*inch, 1.2*inch, 1.5*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f97316')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(trans_table)
    else:
        elements.append(Paragraph("No transactions found for this month.", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('rass2024')
            db.session.add(admin)
            db.session.commit()
            print("✅ Database initialized! Default admin user created.")
            print("   Username: admin")
            print("   Password: rass2024")

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    employees = Employee.query.all()
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    
    stats = {
        'total_employees': len(employees),
        'total_salaries': sum(emp.salary for emp in employees),
        'total_withdrawn': sum(emp.total_withdrawn for emp in employees),
        'total_remaining': sum(emp.salary - emp.total_withdrawn for emp in employees)
    }
    
    return render_template('dashboard.html', stats=stats, transactions=transactions)

@app.route('/employees')
@login_required
def employees():
    search = request.args.get('search', '')
    if search:
        employees = Employee.query.filter(
            (Employee.name.contains(search)) | (Employee.designation.contains(search))
        ).all()
    else:
        employees = Employee.query.all()
    
    return render_template('employees.html', employees=employees, search=search)

@app.route('/employee/add', methods=['POST'])
@login_required
def add_employee():
    try:
        employee = Employee(
            name=request.form['name'],
            designation=request.form['designation'],
            salary=float(request.form['salary']),
            join_date=datetime.strptime(request.form['join_date'], '%Y-%m-%d').date()
        )
        db.session.add(employee)
        db.session.commit()
        flash('Employee added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding employee: {str(e)}', 'error')
    
    return redirect(url_for('employees'))

@app.route('/employee/edit/<int:id>', methods=['POST'])
@login_required
def edit_employee(id):
    employee = db.session.get(Employee, id)
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))
    try:
        employee.name = request.form['name']
        employee.designation = request.form['designation']
        employee.salary = float(request.form['salary'])
        employee.join_date = datetime.strptime(request.form['join_date'], '%Y-%m-%d').date()
        db.session.commit()
        flash('Employee updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating employee: {str(e)}', 'error')
    
    return redirect(url_for('employees'))

@app.route('/employee/delete/<int:id>')
@login_required
def delete_employee(id):
    employee = db.session.get(Employee, id)
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))
    try:
        db.session.delete(employee)
        db.session.commit()
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting employee: {str(e)}', 'error')
    
    return redirect(url_for('employees'))

@app.route('/employee/<int:id>/data')
@login_required
def get_employee_data(id):
    employee = db.session.get(Employee, id)
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404
    return jsonify({
        'id': employee.id,
        'name': employee.name,
        'designation': employee.designation,
        'salary': employee.salary,
        'join_date': employee.join_date.strftime('%Y-%m-%d')
    })

@app.route('/withdrawal/add', methods=['POST'])
@login_required
def add_withdrawal():
    employee_id = int(request.form['employee_id'])
    employee = db.session.get(Employee, employee_id)
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))
    
    try:
        amount = float(request.form['amount'])
        remaining = employee.salary - employee.total_withdrawn
        
        if amount > remaining:
            flash('Withdrawal amount exceeds remaining salary!', 'error')
            return redirect(url_for('employees'))
        
        # Get Pakistan time
        pakistan_time = get_pakistan_time()
        
        transaction = Transaction(
            employee_id=employee_id,
            amount=amount,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            time=pakistan_time.time(),  # Set Pakistan time
            notes=request.form.get('notes', '')
        )
        
        employee.total_withdrawn += amount
        db.session.add(transaction)
        db.session.commit()
        flash('Withdrawal recorded successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording withdrawal: {str(e)}', 'error')
    
    return redirect(url_for('employees'))

@app.route('/export/csv')
@login_required
def export_csv():
    employees = Employee.query.all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Designation', 'Join Date', 'Total Salary', 'Withdrawn', 'Remaining'])
    
    for emp in employees:
        writer.writerow([
            emp.name,
            emp.designation,
            emp.join_date.strftime('%Y-%m-%d'),
            emp.salary,
            emp.total_withdrawn,
            emp.salary - emp.total_withdrawn
        ])
    
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'RASS_Salary_Report_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(old_password):
            flash('Current password is incorrect', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'error')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

# PDF Download Routes
@app.route('/withdrawal/<int:transaction_id>/download-slip')
@login_required
def download_withdrawal_slip(transaction_id):
    """Download PDF slip for a specific withdrawal"""
    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        flash('Transaction not found', 'error')
        return redirect(url_for('employees'))
    
    employee = transaction.employee
    pdf_buffer = generate_withdrawal_slip_pdf(transaction, employee)
    
    filename = f"Withdrawal_Slip_{employee.name.replace(' ', '_')}_{transaction.date.strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/employee/<int:employee_id>/download-history')
@login_required
def download_employee_history(employee_id):
    """Download complete salary history PDF for an employee"""
    employee = db.session.get(Employee, employee_id)
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))
    
    pdf_buffer = generate_employee_history_pdf(employee)
    
    filename = f"Salary_History_{employee.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/reports/monthly')
@login_required
def monthly_reports():
    """Show monthly report selection page"""
    pakistan_now = get_pakistan_datetime()
    return render_template('monthly_reports.html', now=pakistan_now, timedelta=timedelta)

@app.route('/reports/monthly/download')
@login_required
def download_monthly_report():
    """Download monthly salary report PDF"""
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    pdf_buffer = generate_monthly_report_pdf(month, year)
    
    month_name = datetime(year, month, 1).strftime('%B_%Y')
    filename = f"Monthly_Salary_Report_{month_name}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/employee/update-salary-date/<int:employee_id>', methods=['POST'])
@login_required
def update_salary_date(employee_id):
    """Update salary payment date for an employee"""
    employee = db.session.get(Employee, employee_id)
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))
    
    try:
        salary_date = request.form.get('salary_payment_date')
        if salary_date:
            employee.salary_payment_date = datetime.strptime(salary_date, '%Y-%m-%d').date()
            db.session.commit()
            flash('Salary payment date updated successfully!', 'success')
        else:
            flash('Please provide a valid date', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating date: {str(e)}', 'error')
    
    return redirect(url_for('employees'))

if __name__ == '__main__':
    init_db()
    # For production, use: app.run(host='0.0.0.0', port=5000, debug=False)
    app.run(debug=True)
