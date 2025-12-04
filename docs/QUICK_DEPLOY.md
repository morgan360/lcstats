# Quick Deployment Guide for PythonAnywhere EU

## ✓ COMPLETED:
- Database backup uploaded to PythonAnywhere

## NEXT STEPS:

### 1. Open your terminal and SSH to PythonAnywhere:
```bash
ssh morganmck@ssh.eu.pythonanywhere.com
```
Password: `Newtcsp@8899`

### 2. Once connected, copy and paste ALL these commands at once:

```bash
# Setup project
cd ~
rm -rf lcstats 2>/dev/null
git clone https://github.com/morgan360/lcstats.git
cd lcstats

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies (takes 3-5 minutes)
pip install --upgrade pip
pip install -r requirements.txt
pip install mysqlclient

echo "✓ Setup complete! Now creating .env file..."
```

### 3. After installation finishes, you need MySQL database info

Go to: https://eu.pythonanywhere.com/user/morganmck/databases/

Note your:
- Database name (create one called: `morganmck$lcaim` if needed)
- MySQL password (you can see/reset it there)
- Host will be: `morganmck.mysql.eu.pythonanywhere-services.com`

### 4. Come back here and tell me your MySQL database info, then I'll create the .env file for you!
