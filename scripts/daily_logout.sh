#!/bin/bash
# scripts/daily_logout.sh
# Logs out all users by clearing Django sessions
# Intended to run via cron at 2am daily

# Set the project directory
PROJECT_DIR="/home/morganvooght/lcstats"
VENV_DIR="$PROJECT_DIR/.venv"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Change to project directory
cd "$PROJECT_DIR"

# Run the logout command
echo "$(date): Running daily user logout..."
python manage.py logout_all_users

# Log the result
if [ $? -eq 0 ]; then
    echo "$(date): Daily logout completed successfully"
else
    echo "$(date): Daily logout failed with exit code $?"
fi