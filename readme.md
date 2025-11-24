# 🍽️ RASS CUISINE RESTAURANT - Salary Management System

A comprehensive web-based salary management system built with Flask for tracking employee salaries, withdrawals, and generating reports.

## ✨ Features

- 🔐 **Secure Login System** - Protected admin access
- 👥 **Employee Management** - Add, edit, delete employees
- 💰 **Salary Tracking** - Track total salaries and withdrawals
- 📊 **Dashboard** - Real-time statistics and recent transactions
- 📅 **Date Tracking** - Record salary payment and withdrawal dates
- 📁 **Export Reports** - Download salary data as CSV
- 🔑 **Password Management** - Change admin password
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile

---

## 📁 Project Structure

```
rass-salary-system/
│
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── templates/
│   ├── base.html            # Base template
│   ├── login.html           # Login page
│   ├── dashboard.html       # Dashboard page
│   ├── employees.html       # Employee management
│   └── change_password.html # Password change page
│
├── static/
│   ├── css/
│   │   └── style.css        # Custom styles
│   └── js/
│       └── script.js        # JavaScript functions
│
└── rass_salary.db           # SQLite database (auto-created)
```

---

## 🚀 Installation Guide

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Basic command line knowledge

### Step 1: Install Python

#### Windows:
1. Download Python from [python.org/downloads](https://www.python.org/downloads/)
2. Run installer and **CHECK** "Add Python to PATH"
3. Verify installation:
```bash
python --version
```

#### Mac:
```bash
# Using Homebrew
brew install python3
```

#### Linux:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

### Step 2: Setup Project

1. **Extract the project files** to a folder (e.g., `C:\rass-salary-system`)

2. **Open Terminal/Command Prompt** in that folder:
   - Windows: Right-click in folder → "Open in Terminal" or "Open PowerShell"
   - Mac/Linux: Open Terminal and navigate to folder using `cd`

3. **Create Virtual Environment**:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

4. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

### Step 3: Run the Application

```bash
python app.py
```

You should see:
```
✅ Database initialized! Default admin user created.
   Username: admin
   Password: rass2024
 * Running on http://127.0.0.1:5000
```

### Step 4: Access the System

1. Open your web browser
2. Go to: `http://127.0.0.1:5000`
3. Login with:
   - **Username:** admin
   - **Password:** rass2024

⚠️ **IMPORTANT:** Change the default password immediately after first login!

---

## 🌐 Deployment Options

### Option 1: Local Network (Recommended for Restaurant)

**Best for:** Single restaurant with multiple devices on same WiFi

1. Find your computer's IP address:

**Windows:**
```bash
ipconfig
# Look for "IPv4 Address" (e.g., 192.168.1.100)
```

**Mac/Linux:**
```bash
ifconfig
# or
ip addr show
```

2. Run the app for network access:
```bash
python app.py
```

Then modify `app.py` last line to:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

3. Access from other devices:
```
http://YOUR-IP-ADDRESS:5000
# Example: http://192.168.1.100:5000
```

**Advantages:**
- ✅ Free
- ✅ No internet required
- ✅ Fast
- ✅ Private data (stays on local network)
- ✅ No monthly fees

**Setup for Auto-Start on Windows:**

1. Create `start_rass.bat`:
```batch
@echo off
cd C:\path\to\rass-salary-system
call venv\Scripts\activate
python app.py
pause
```

2. Put shortcut in Windows Startup folder:
   - Press `Win + R`
   - Type: `shell:startup`
   - Put the `.bat` file there

---

### Option 2: Cloud Hosting (PythonAnywhere - Free)

**Best for:** Access from anywhere with internet

1. **Sign up** at [pythonanywhere.com](https://www.pythonanywhere.com)
2. **Upload your code** using their Files tab
3. **Create a web app**:
   - Choose Flask
   - Python 3.10
   - Point to your `app.py`
4. **Install requirements** in their Console:
```bash
pip install --user -r requirements.txt
```
5. **Access** your app at: `yourusername.pythonanywhere.com`

**Advantages:**
- ✅ Access from anywhere
- ✅ Free tier available
- ✅ No setup required
- ✅ Automatic backups

**Disadvantages:**
- ❌ Requires internet
- ❌ Free tier has limitations

---

### Option 3: VPS Hosting (Production)

**Best for:** Multiple restaurants or professional deployment

**Providers:**
- DigitalOcean ($5/month)
- Linode ($5/month)
- AWS Lightsail ($3.50/month)

**Basic Setup:**
```bash
# On VPS
sudo apt update
sudo apt install python3-pip nginx
git clone your-repository
cd rass-salary-system
pip3 install -r requirements.txt

# Setup Gunicorn
pip3 install gunicorn
gunicorn --bind 0.0.0.0:5000 app:app

# Configure Nginx for reverse proxy
# Add SSL certificate with Let's Encrypt
```

---

## 👥 Default Login Credentials

```
Username: admin
Password: rass2024
```

⚠️ **SECURITY:** Change password immediately after first login!

---

## 📖 User Guide

### Adding Employees

1. Navigate to **Employees** page
2. Click **Add Employee** button
3. Fill in:
   - Name
   - Designation
   - Monthly Salary
   - Join Date
4. Click **Add Employee**

### Recording Withdrawals

1. Go to **Employees** page
2. Click the 💰 (dollar) icon next to employee
3. Enter:
   - Withdrawal amount
   - Date
   - Notes (optional)
4. Click **Record Withdrawal**

### Viewing Dashboard

- **Total Employees:** Count of all staff
- **Total Salaries:** Sum of all monthly salaries
- **Total Withdrawn:** Total amount paid out
- **Total Remaining:** Available balance
- **Recent Transactions:** Last 10 withdrawals

### Exporting Reports

1. Click **Export CSV** button
2. File downloads automatically
3. Open in Excel or Google Sheets

### Changing Password

1. Click **Password** in header
2. Enter:
   - Current password
   - New password (min 6 characters)
   - Confirm new password
3. Click **Update Password**

---

## 🔒 Security Best Practices

1. **Change Default Password** immediately
2. **Use Strong Password** (mix of letters, numbers, symbols)
3. **Don't Share Credentials** with unauthorized personnel
4. **Regular Backups** of database file
5. **Update Software** regularly
6. **Use HTTPS** in production (with SSL certificate)
7. **Limit Network Access** if using local network option

---

## 💾 Backup & Restore

### Backup Database

**Manual Backup:**
```bash
# Copy the database file
cp rass_salary.db rass_salary_backup_2024-11-23.db
```

**Automated Backup (Windows):**
Create `backup.bat`:
```batch
@echo off
set date=%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%
copy rass_salary.db backups\rass_salary_%date%.db
```

**Automated Backup (Mac/Linux):**
Create `backup.sh`:
```bash
#!/bin/bash
cp rass_salary.db backups/rass_salary_$(date +%Y%m%d).db
```

### Restore Database

```bash
# Stop the application first
# Then replace the database file
cp rass_salary_backup_2024-11-23.db rass_salary.db
# Restart the application
```

---

## 🛠️ Troubleshooting

### Issue: Port already in use

**Solution:**
```bash
# Find process using port 5000
# Windows
netstat -ano | findstr :5000

# Mac/Linux
lsof -i :5000

# Kill the process or change port in app.py
```

### Issue: Database errors

**Solution:**
```bash
# Delete database and restart (creates fresh database)
rm rass_salary.db
python app.py
```

### Issue: Can't access from other devices

**Solutions:**
1. Check if firewall is blocking port 5000
2. Ensure app is running with `host='0.0.0.0'`
3. Verify devices are on same network
4. Try accessing with computer name instead of IP

### Issue: Forgot password

**Solution:**
```bash
# Delete database (will lose all data) and restart
rm rass_salary.db
python app.py
# Or reset password via Python shell
```

---

## 🎓 Training Guide for Staff

### For Managers:

1. **Daily Tasks:**
   - Check dashboard for overview
   - Review recent transactions
   - Record employee withdrawals

2. **Weekly Tasks:**
   - Review employee balances
   - Export reports for records
   - Verify all transactions

3. **Monthly Tasks:**
   - Update employee salaries if needed
   - Backup database
   - Change password for security

### For Employees:

- View-only access not included in current version
- Managers handle all transactions
- Employees can request balance inquiries from manager

---

## 📞 Support & Maintenance

### Common Maintenance Tasks

1. **Weekly:** Check dashboard, verify transactions
2. **Monthly:** Backup database, review employee records
3. **Quarterly:** Change admin password, update system
4. **Yearly:** Review all employee data, archive old records

### Getting Help

1. Check this README first
2. Review error messages carefully
3. Check Python and Flask documentation
4. Contact system administrator

---

## 🔄 Updating the System

```bash
# Pull latest changes (if using git)
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart application
python app.py
```

---

## 📝 Customization

### Change Restaurant Name

Edit `templates/base.html` and `templates/login.html`:
```html
<h1>YOUR RESTAURANT NAME</h1>
```

### Change Color Scheme

Edit `static/css/style.css`:
```css
:root {
    --primary-color: #your-color;
    --secondary-color: #your-color;
}
```

### Add Features

Contact developer or modify `app.py` and templates as needed.

---

## 📄 License

This project is provided for use by RASS CUISINE RESTAURANT.

---

## 🎯 Quick Start Summary

```bash
# 1. Install Python (python.org)
# 2. Extract project files
# 3. Open terminal in project folder
# 4. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run application
python app.py

# 7. Open browser
# Go to: http://127.0.0.1:5000
# Login: admin / rass2024

# 8. CHANGE PASSWORD IMMEDIATELY!
```

---

## 📧 Contact

For technical support or customization requests, please contact your system administrator.

---

**Version:** 1.0
**Last Updated:** November 2024
**Developer:** Custom Development Team

---

## 🌟 Thank You!

Thank you for using RASS CUISINE Salary Management System. We hope this tool helps streamline your restaurant's salary management processes!

For optimal performance, remember to:
- ✅ Keep regular backups
- ✅ Use strong passwords
- ✅ Train staff properly
- ✅ Monitor system regularly

Happy managing! 🚀