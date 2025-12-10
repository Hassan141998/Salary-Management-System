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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rass-cuisine-secret-key-change-this-in-production')

# Database Configuration - PostgreSQL for Production, SQLite for Local
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Production: Use PostgreSQL (Neon)
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
    salary_payment_date = db.Column(db.Date, nullable=True)
    total_withdrawn = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # CASCADE DELETE - THIS IS THE FIX!
    transactions = db.relationship('Transaction', backref='employee', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='employee_rel', lazy=True, cascade='all, delete-orphan')


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    check_in_time = db.Column(db.Time)
    check_out_time = db.Column(db.Time)
    notes = db.Column(db.String(500))
    marked_by = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_employee_date'),)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Timezone Helper Functions (Pakistan Standard Time = UTC+5)
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


# ============================================
# PDF GENERATION FUNCTIONS
# ============================================

def generate_withdrawal_slip_pdf(transaction, employee):
    """Generate a withdrawal slip PDF for a single transaction"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

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

    title = Paragraph("RASS CUISINE RESTAURANT", title_style)
    elements.append(title)

    subtitle = Paragraph("Salary Withdrawal Slip", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.3 * inch))

    time_str = 'N/A'
    if transaction.time:
        time_str = transaction.time.strftime('%I:%M %p')

    slip_data = [
        ['Slip No:', f"WS-{transaction.id:06d}"],
        ['Date & Time:', f"{transaction.date.strftime('%d %B %Y')} at {time_str}"],
        ['Generated On:', get_pakistan_time().strftime('%d %B %Y, %I:%M %p')],
    ]

    slip_table = Table(slip_data, colWidths=[2 * inch, 4 * inch])
    slip_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(slip_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Employee Information", heading_style))

    emp_data = [
        ['Employee Name:', employee.name],
        ['Designation:', employee.designation],
        ['Employee ID:', f"EMP-{employee.id:04d}"],
        ['Join Date:', employee.join_date.strftime('%d %B %Y')],
    ]

    emp_table = Table(emp_data, colWidths=[2 * inch, 4 * inch])
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
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Salary Details", heading_style))

    salary_data = [
        ['Description', 'Amount (Rs)'],
        ['Monthly Salary', f"{employee.salary:,.2f}"],
        ['Previous Withdrawals', f"{employee.total_withdrawn - transaction.amount:,.2f}"],
        ['Current Withdrawal', f"{transaction.amount:,.2f}"],
        ['Remaining Balance', f"{employee.salary - employee.total_withdrawn:,.2f}"],
    ]

    salary_table = Table(salary_data, colWidths=[3 * inch, 2 * inch])
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
    elements.append(Spacer(1, 0.3 * inch))

    if transaction.notes:
        elements.append(Paragraph(f"<b>Notes:</b> {transaction.notes}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

    elements.append(Spacer(1, 0.5 * inch))

    sig_data = [
        ['_____________________', '_____________________'],
        ['Employee Signature', 'Authorized Signature'],
    ]

    sig_table = Table(sig_data, colWidths=[3 * inch, 3 * inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 5),
    ]))
    elements.append(sig_table)

    elements.append(Spacer(1, 0.5 * inch))
    footer_text = "This is a computer-generated document. No signature required."
    footer = Paragraph(f"<i>{footer_text}</i>", styles['Normal'])
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_employee_history_pdf(employee):
    """Generate complete salary history PDF for an employee"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

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
    elements.append(Spacer(1, 0.2 * inch))

    emp_info = f"""
    <b>Employee Name:</b> {employee.name}<br/>
    <b>Designation:</b> {employee.designation}<br/>
    <b>Employee ID:</b> EMP-{employee.id:04d}<br/>
    <b>Join Date:</b> {employee.join_date.strftime('%d %B %Y')}<br/>
    <b>Monthly Salary:</b> Rs {employee.salary:,.2f}<br/>
    <b>Report Generated:</b> {get_pakistan_time().strftime('%d %B %Y, %I:%M %p')}
    """
    elements.append(Paragraph(emp_info, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    summary_data = [
        ['Total Salary', f"Rs {employee.salary:,.2f}"],
        ['Total Withdrawn', f"Rs {employee.total_withdrawn:,.2f}"],
        ['Remaining Balance', f"Rs {employee.salary - employee.total_withdrawn:,.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
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
    elements.append(Spacer(1, 0.3 * inch))

    if employee.transactions:
        elements.append(Paragraph("<b>Withdrawal History</b>", styles['Heading3']))
        elements.append(Spacer(1, 0.1 * inch))

        trans_data = [['Date', 'Time', 'Amount (Rs)', 'Notes']]
        for trans in sorted(employee.transactions, key=lambda x: x.date, reverse=True):
            trans_data.append([
                trans.date.strftime('%d %b %Y'),
                trans.time.strftime('%I:%M %p') if trans.time else 'N/A',
                f"{trans.amount:,.2f}",
                trans.notes[:30] + '...' if trans.notes and len(trans.notes) > 30 else (trans.notes or '-')
            ])

        trans_table = Table(trans_data, colWidths=[1.5 * inch, 1.2 * inch, 1.5 * inch, 2.3 * inch])
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


def generate_all_employees_pdf():
    """Generate comprehensive PDF report for ALL employees with complete information"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#f97316'),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    # Main Title
    title = Paragraph("RASS CUISINE RESTAURANT", title_style)
    elements.append(title)

    subtitle = Paragraph("Complete Employee Information Report", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.1 * inch))

    report_info = f"<b>Report Generated:</b> {get_pakistan_time().strftime('%d %B %Y, %I:%M %p')}"
    elements.append(Paragraph(report_info, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # Get all employees
    employees = Employee.query.all()

    # Summary Statistics
    total_salaries = sum(emp.salary for emp in employees)
    total_withdrawn = sum(emp.total_withdrawn for emp in employees)
    total_remaining = total_salaries - total_withdrawn

    summary_data = [
        ['Metric', 'Value'],
        ['Total Employees', str(len(employees))],
        ['Total Monthly Salaries', f"Rs {total_salaries:,.2f}"],
        ['Total Withdrawn', f"Rs {total_withdrawn:,.2f}"],
        ['Total Remaining', f"Rs {total_remaining:,.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 2.5 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f97316')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fef3c7'), colors.white]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.4 * inch))

    # Individual Employee Details
    for idx, emp in enumerate(employees, 1):
        # Page break after every 2 employees (except first)
        if idx > 1 and (idx - 1) % 2 == 0:
            elements.append(PageBreak())

        # Employee Header
        emp_header = f"<b>Employee #{idx}: {emp.name}</b>"
        elements.append(Paragraph(emp_header, styles['Heading3']))
        elements.append(Spacer(1, 0.1 * inch))

        # Employee Basic Info
        emp_data = [
            ['Employee ID', f"EMP-{emp.id:04d}"],
            ['Name', emp.name],
            ['Designation', emp.designation],
            ['Join Date', emp.join_date.strftime('%d %B %Y')],
            ['Salary Payment Date',
             emp.salary_payment_date.strftime('%d %B %Y') if emp.salary_payment_date else 'Not Set'],
        ]

        emp_table = Table(emp_data, colWidths=[2 * inch, 3.5 * inch])
        emp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(emp_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Financial Summary
        fin_data = [
            ['Monthly Salary', f"Rs {emp.salary:,.2f}"],
            ['Total Withdrawn', f"Rs {emp.total_withdrawn:,.2f}"],
            ['Remaining Balance', f"Rs {emp.salary - emp.total_withdrawn:,.2f}"],
            ['Withdrawal Percentage', f"{(emp.total_withdrawn / emp.salary * 100):.1f}%" if emp.salary > 0 else '0%'],
        ]

        fin_table = Table(fin_data, colWidths=[2 * inch, 3.5 * inch])
        fin_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(fin_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Recent Transactions (Last 5)
        recent_trans = sorted(emp.transactions, key=lambda x: x.date, reverse=True)[:5]
        if recent_trans:
            elements.append(Paragraph("<b>Recent Withdrawals (Last 5):</b>", styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))

            trans_data = [['Date', 'Amount (Rs)', 'Notes']]
            for trans in recent_trans:
                trans_data.append([
                    trans.date.strftime('%d %b %Y'),
                    f"{trans.amount:,.2f}",
                    (trans.notes[:25] + '...') if trans.notes and len(trans.notes) > 25 else (trans.notes or '-')
                ])

            trans_table = Table(trans_data, colWidths=[1.5 * inch, 1.5 * inch, 2.5 * inch])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#60a5fa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eff6ff')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(trans_table)
        else:
            elements.append(Paragraph("<i>No withdrawal history</i>", styles['Normal']))

        # Attendance Summary (Last 30 days)
        today = get_pakistan_date()
        start_date = today - timedelta(days=30)
        attendance_records = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_date,
            Attendance.date <= today
        ).all()

        if attendance_records:
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph("<b>Attendance (Last 30 Days):</b>", styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))

            present = sum(1 for r in attendance_records if r.status == 'Present')
            absent = sum(1 for r in attendance_records if r.status == 'Absent')
            leave = sum(1 for r in attendance_records if r.status == 'Leave')
            half_day = sum(1 for r in attendance_records if r.status == 'Half-Day')
            total = len(attendance_records)
            percentage = (present / total * 100) if total > 0 else 0

            att_data = [
                ['Status', 'Days'],
                ['Present', str(present)],
                ['Absent', str(absent)],
                ['Leave', str(leave)],
                ['Half-Day', str(half_day)],
                ['Total Marked', str(total)],
                ['Attendance %', f"{percentage:.1f}%"],
            ]

            att_table = Table(att_data, colWidths=[2 * inch, 1.5 * inch])
            att_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#d1fae5')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(att_table)

        elements.append(Spacer(1, 0.3 * inch))

        # Separator line
        if idx < len(employees):
            elements.append(Paragraph("_" * 80, styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

    # Footer
    elements.append(Spacer(1, 0.3 * inch))
    footer = Paragraph(
        "<i>End of Report - RASS CUISINE Restaurant - Confidential</i>",
        styles['Normal']
    )
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_monthly_report_pdf(month, year):
    """Generate monthly salary report for all employees"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

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
    elements.append(Spacer(1, 0.2 * inch))

    report_info = f"<b>Report Generated:</b> {get_pakistan_time().strftime('%d %B %Y, %I:%M %p')}"
    elements.append(Paragraph(report_info, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

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
        total_withdrawn = sum(t.amount for t in transactions)
        elements.append(
            Paragraph(f"<b>Total Withdrawals This Month:</b> Rs {total_withdrawn:,.2f}", styles['Heading3']))
        elements.append(Paragraph(f"<b>Total Transactions:</b> {len(transactions)}", styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))

        trans_data = [['Date', 'Employee', 'Designation', 'Amount (Rs)', 'Notes']]
        for trans in transactions:
            trans_data.append([
                trans.date.strftime('%d %b'),
                trans.employee.name,
                trans.employee.designation,
                f"{trans.amount:,.2f}",
                trans.notes[:20] + '...' if trans.notes and len(trans.notes) > 20 else (trans.notes or '-')
            ])

        trans_table = Table(trans_data, colWidths=[1 * inch, 1.8 * inch, 1.5 * inch, 1.2 * inch, 1.5 * inch])
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


# ============================================
# INITIALIZATION AND ROUTES
# ============================================

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
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
    employees = Employee.query.order_by(Employee.id).all()  # ✅ Sort by ID
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()

    stats = {
        'total_employees': len(employees),
        'total_salaries': sum(emp.salary for emp in employees),
        'total_withdrawn': sum(emp.total_withdrawn for emp in employees),
        'total_remaining': sum(emp.salary - emp.total_withdrawn for emp in employees)
    }

    return render_template('dashboard.html', stats=stats, transactions=transactions, employees=employees)


@app.route('/employees')
@login_required
def employees():
    search = request.args.get('search', '')
    if search:
        employees = Employee.query.filter(
            (Employee.name.contains(search)) | (Employee.designation.contains(search))
        ).order_by(Employee.id).all()  # ✅ Sort by ID
    else:
        employees = Employee.query.order_by(Employee.id).all()  # ✅ Sort by ID

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

        pakistan_time = get_pakistan_time()

        transaction = Transaction(
            employee_id=employee_id,
            amount=amount,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            time=pakistan_time.time(),
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


@app.route('/download-all-employees-pdf')
@login_required
def download_all_employees_pdf():
    """Download complete PDF report for ALL employees with all information"""
    pdf_buffer = generate_all_employees_pdf()

    filename = f"All_Employees_Complete_Report_{get_pakistan_time().strftime('%Y%m%d_%H%M%S')}.pdf"

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


# ============================================
# ATTENDANCE ROUTES
# ============================================

@app.route('/attendance')
@login_required
def attendance():
    """Show attendance marking page"""
    today = get_pakistan_date()

    selected_date_str = request.args.get('date', today.strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except:
        selected_date = today

    employees = Employee.query.order_by(Employee.name).all()

    attendance_records = {}
    records = Attendance.query.filter_by(date=selected_date).all()
    for record in records:
        attendance_records[record.employee_id] = record

    return render_template('attendance.html',
                           employees=employees,
                           selected_date=selected_date,
                           today=today,
                           attendance_records=attendance_records,
                           timedelta=timedelta)


@app.route('/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
    """Mark attendance for employees"""
    try:
        date_str = request.form.get('date')
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        pakistan_time = get_pakistan_time()

        employees = Employee.query.all()
        marked_count = 0

        for employee in employees:
            status = request.form.get(f'status_{employee.id}')

            if status:
                existing = Attendance.query.filter_by(
                    employee_id=employee.id,
                    date=attendance_date
                ).first()

                check_in = request.form.get(f'check_in_{employee.id}')
                check_out = request.form.get(f'check_out_{employee.id}')
                notes = request.form.get(f'notes_{employee.id}', '')

                if existing:
                    existing.status = status
                    existing.check_in_time = datetime.strptime(check_in, '%H:%M').time() if check_in else None
                    existing.check_out_time = datetime.strptime(check_out, '%H:%M').time() if check_out else None
                    existing.notes = notes
                    existing.marked_by = current_user.username
                else:
                    attendance = Attendance(
                        employee_id=employee.id,
                        date=attendance_date,
                        status=status,
                        check_in_time=datetime.strptime(check_in, '%H:%M').time() if check_in else None,
                        check_out_time=datetime.strptime(check_out, '%H:%M').time() if check_out else None,
                        notes=notes,
                        marked_by=current_user.username
                    )
                    db.session.add(attendance)

                marked_count += 1

        db.session.commit()
        flash(f'Attendance marked successfully for {marked_count} employees!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error marking attendance: {str(e)}', 'error')

    return redirect(url_for('attendance', date=date_str))


@app.route('/attendance/report')
@login_required
def attendance_report():
    """Show attendance report page"""
    pakistan_now = get_pakistan_datetime()
    month = int(request.args.get('month', pakistan_now.month))
    year = int(request.args.get('year', pakistan_now.year))

    employees = Employee.query.order_by(Employee.name).all()

    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, days_in_month)

    attendance_data = {}
    for employee in employees:
        records = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()

        present_count = sum(1 for r in records if r.status == 'Present')
        absent_count = sum(1 for r in records if r.status == 'Absent')
        leave_count = sum(1 for r in records if r.status == 'Leave')
        half_day_count = sum(1 for r in records if r.status == 'Half-Day')

        daily_records = {r.date.day: r for r in records}

        attendance_data[employee.id] = {
            'employee': employee,
            'records': daily_records,
            'present': present_count,
            'absent': absent_count,
            'leave': leave_count,
            'half_day': half_day_count,
            'total_marked': len(records)
        }

    return render_template('attendance_report.html',
                           attendance_data=attendance_data,
                           month=month,
                           year=year,
                           days_in_month=days_in_month,
                           employees=employees,
                           date=date)


@app.route('/attendance/employee/<int:employee_id>')
@login_required
def employee_attendance_history(employee_id):
    """Show individual employee attendance history"""
    employee = db.session.get(Employee, employee_id)
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))

    today = get_pakistan_date()
    start_date = today - timedelta(days=30)

    records = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date <= today
    ).order_by(Attendance.date.desc()).all()

    total_days = len(records)
    present_count = sum(1 for r in records if r.status == 'Present')
    absent_count = sum(1 for r in records if r.status == 'Absent')
    leave_count = sum(1 for r in records if r.status == 'Leave')
    half_day_count = sum(1 for r in records if r.status == 'Half-Day')

    stats = {
        'total': total_days,
        'present': present_count,
        'absent': absent_count,
        'leave': leave_count,
        'half_day': half_day_count,
        'attendance_percentage': (present_count / total_days * 100) if total_days > 0 else 0
    }

    return render_template('employee_attendance.html',
                           employee=employee,
                           records=records,
                           stats=stats,
                           start_date=start_date,
                           end_date=today)


@app.route('/attendance/download/<int:month>/<int:year>')
@login_required
def download_attendance_report(month, year):
    """Download monthly attendance report as CSV"""
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, days_in_month)

    employees = Employee.query.order_by(Employee.name).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([f'RASS CUISINE - Attendance Report - {start_date.strftime("%B %Y")}'])
    writer.writerow([])
    writer.writerow(['Employee', 'Present', 'Absent', 'Leave', 'Half-Day', 'Total Days', 'Attendance %'])

    for employee in employees:
        records = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()

        present = sum(1 for r in records if r.status == 'Present')
        absent = sum(1 for r in records if r.status == 'Absent')
        leave = sum(1 for r in records if r.status == 'Leave')
        half_day = sum(1 for r in records if r.status == 'Half-Day')
        total = len(records)
        percentage = (present / total * 100) if total > 0 else 0

        writer.writerow([
            employee.name,
            present,
            absent,
            leave,
            half_day,
            total,
            f"{percentage:.1f}%"
        ])

    output.seek(0)
    month_name = date(year, month, 1).strftime('%B_%Y')

    return send_file(
        BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'Attendance_Report_{month_name}.csv'
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)