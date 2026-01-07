#!/bin/bash

# Safe Question Sync Script for LCAI Maths Database
# Uses natural keys to avoid ID conflicts between local and production
# Best for updating existing topics with new questions

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LCAI Maths Safe Question Sync ===${NC}\n"

# Configuration
PA_USERNAME="morganmck"
PA_HOST="ssh.eu.pythonanywhere.com"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Check if user wants to export by IDs or section
echo -e "${BLUE}Select export method:${NC}"
echo "  1) Export specific question IDs"
echo "  2) Export entire section"
echo -e "\n"
read -p "Choice (1 or 2): " CHOICE

if [ "$CHOICE" = "1" ]; then
    read -p "Enter question IDs (space-separated): " IDS

    if [ -z "$IDS" ]; then
        echo -e "${RED}Error: No IDs provided${NC}"
        exit 1
    fi

    echo -e "\n${YELLOW}Step 1: Exporting questions by ID...${NC}"
    python manage.py export_questions_safe --ids $IDS --output questions_safe_${TIMESTAMP}.json

elif [ "$CHOICE" = "2" ]; then
    # Show available sections
    echo -e "\n${BLUE}Available sections:${NC}"
    python manage.py shell -c "from interactive_lessons.models import Section; [print(f'{s.topic.name} → {s.name} ({s.questions.count()} questions)') for s in Section.objects.all().order_by('topic__name', 'order')]"

    echo -e "\n"
    read -p "Enter exact section name: " SECTION_NAME

    if [ -z "$SECTION_NAME" ]; then
        echo -e "${RED}Error: No section name provided${NC}"
        exit 1
    fi

    echo -e "\n${YELLOW}Step 1: Exporting section '$SECTION_NAME'...${NC}"
    python manage.py export_questions_safe --section "$SECTION_NAME" --output questions_safe_${TIMESTAMP}.json

else
    echo -e "${RED}Invalid choice${NC}"
    exit 1
fi

if [ ! -f "questions_safe_${TIMESTAMP}.json" ]; then
    echo -e "${RED}Error: Export file not created${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Export successful!${NC}\n"

echo -e "${YELLOW}Step 2: Uploading to PythonAnywhere...${NC}"
echo -e "${YELLOW}NOTE: If SSH/SCP times out, use manual upload method below${NC}\n"

# Try automatic upload
if scp -o ConnectTimeout=30 questions_safe_${TIMESTAMP}.json ${PA_USERNAME}@${PA_HOST}:~/lcstats/ 2>/dev/null; then
    echo -e "${GREEN}✓ File uploaded automatically!${NC}\n"
else
    echo -e "${RED}✗ Automatic upload failed (SSH timeout)${NC}"
    echo -e "${YELLOW}Please use MANUAL UPLOAD METHOD:${NC}\n"
    echo -e "  1. Go to: https://www.pythonanywhere.com/user/${PA_USERNAME}/files/home/${PA_USERNAME}/lcstats/"
    echo -e "  2. Click 'Upload a file' button"
    echo -e "  3. Upload: questions_safe_${TIMESTAMP}.json"
    echo -e ""
fi

echo -e "${YELLOW}Step 3: Import questions on PythonAnywhere${NC}\n"
echo -e "${BLUE}Open a Bash console at: https://www.pythonanywhere.com/user/${PA_USERNAME}/consoles/${NC}\n"
echo -e "Then run these commands:\n"
echo -e "  ${GREEN}cd ~/lcstats${NC}"
echo -e "  ${GREEN}source venv/bin/activate${NC}"
echo -e "  ${GREEN}git pull origin main${NC}  ${BLUE}# Get latest import command${NC}"
echo -e "  ${GREEN}python manage.py import_questions_safe questions_safe_${TIMESTAMP}.json${NC}"
echo -e "  ${GREEN}touch /var/www/morgan360_pythonanywhere_com_wsgi.py${NC}"
echo -e ""

echo -e "${YELLOW}Step 4: Verify on PythonAnywhere${NC}"
echo -e "  Check section question counts:\n"
echo -e "  ${GREEN}python manage.py shell -c \"from interactive_lessons.models import Topic, Section; t = Topic.objects.get(name='Your Topic'); [print(f'{s.name}: {s.questions.count()}') for s in Section.objects.filter(topic=t)]\"${NC}\n"

echo -e "${GREEN}Export file created:${NC}"
echo -e "  - questions_safe_${TIMESTAMP}.json\n"

echo -e "${BLUE}Why use this instead of sync_to_production_simple.sh?${NC}"
echo -e "  ✅ Avoids ID conflicts between local and production databases"
echo -e "  ✅ Uses topic/section names instead of primary keys"
echo -e "  ✅ Won't fail with 'Duplicate entry' errors"
echo -e "  ✅ Perfect for adding questions to existing topics/sections\n"

echo -e "${YELLOW}When to use sync_to_production_simple.sh instead:${NC}"
echo -e "  • Creating brand new topics that don't exist in production"
echo -e "  • Fresh production database setup"
echo -e "  • Syncing notes (not affected by this issue)\n"