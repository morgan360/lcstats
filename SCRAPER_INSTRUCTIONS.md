# 🔍 Career Guidance Contact Scraper

This tool automatically scrapes school websites to find career guidance counsellor contact information.

## 📋 What It Does

The scraper:
1. Visits each school's website
2. Looks for pages mentioning "career guidance" or "guidance counsellor"
3. Extracts names and email addresses near these keywords
4. Updates your database with the secondary contact information

## ⚙️ Requirements

Install required packages:

```bash
pip install beautifulsoup4 requests
```

## 🧪 Step 1: Test First

**Always test before running on all schools!**

```bash
python test_scraper.py
```

This will:
- Test the scraper on 5 sample schools
- Show you what it finds
- Let you verify it's working correctly

**Review the output:**
- Does it find guidance-related keywords?
- Does it find email addresses?
- Are the emails relevant?

## 🚀 Step 2: Run in Dry-Run Mode

Once testing looks good, run on all schools WITHOUT saving:

```bash
python manage.py scrape_guidance_contacts --dry-run
```

This shows what WOULD be updated without actually changing the database.

**Review the results:**
- How many schools had guidance contacts found?
- Do the names/emails look reasonable?
- Any false positives?

## ✅ Step 3: Run For Real

If dry-run looks good, run it for real:

```bash
python manage.py scrape_guidance_contacts
```

This will update your database with the found contacts.

## 📊 Step 4: Check Results

After running, check how many contacts were found:

```bash
python manage.py shell
```

Then run:
```python
from schools.models import School

total = School.objects.count()
with_guidance = School.objects.exclude(
    secondary_contact_email=''
).filter(
    secondary_contact_email__isnull=False
).count()

print(f"Total schools: {total}")
print(f"With guidance contacts: {with_guidance}")
print(f"Success rate: {with_guidance/total*100:.1f}%")
```

## 🎯 Advanced Options

### Scrape a Single School

Test on one specific school:

```bash
python manage.py scrape_guidance_contacts --school-id 5 --verbose
```

### Verbose Output

See detailed scraping progress:

```bash
python manage.py scrape_guidance_contacts --dry-run --verbose
```

## ⚠️ Important Notes

### 1. Respect Websites
- The scraper includes 2-second delays between requests
- Don't run it repeatedly in short periods
- This is respectful to school servers

### 2. Accuracy Expectations
- **Success Rate**: Expect 30-60% success rate
- Not all schools list guidance counsellors online
- Some schools use PDF staff lists (harder to scrape)
- Some use images instead of text

### 3. Manual Follow-Up Required

For schools where scraping fails:
1. Visit the school website manually
2. Look for "Staff", "Contact", or "Guidance" pages
3. Note the guidance counsellor's name and email
4. Update in Django admin

### 4. Verification

Always verify before sending emails:
- Check that emails look legitimate (not generic info@ addresses)
- Verify names are actual people (not "Career Guidance Counsellor")
- Remove obviously wrong entries

## 🔧 Troubleshooting

### "No module named 'bs4'"

Install BeautifulSoup:
```bash
pip install beautifulsoup4
```

### "Connection timeout"

Some school websites are slow or down:
- These will be skipped
- Note which schools failed
- Try them manually later

### Low success rate (<20%)

If scraper finds very few contacts:
- Run test_scraper.py on a few schools
- Check if websites are blocking scrapers
- May need to adjust scraping logic

### False positives

If scraper finds wrong contacts:
- Use --dry-run first to review
- Manually verify before sending emails
- Update scraper logic to filter better

## 📈 Expected Results

Based on typical Irish secondary school websites:

| Outcome | Expected % |
|---------|-----------|
| Successfully scraped | 30-60% |
| No guidance info online | 20-40% |
| Website down/broken | 5-10% |
| Manual research needed | 30-50% |

## 🔄 Next Steps After Scraping

1. **Review found contacts** in Django admin
2. **Manually research** schools where scraping failed
3. **Verify email addresses** are correct
4. **Update the email campaign** to target guidance counsellors
5. **Send targeted emails** to guidance counsellors specifically

## 💡 Tips for Better Results

### Improve Scraping

If you want to improve the scraper:
- Add more common page paths to check
- Add more guidance-related keywords
- Adjust the name extraction logic

### Manual Research Tips

For schools where scraping fails:
1. **Call the school** - Often fastest method
2. **Check LinkedIn** - Search "guidance counsellor [school name]"
3. **Email main office** - Ask them to forward
4. **Check school reports/PDFs** - Sometimes listed there

## 📞 Need Help?

If you encounter issues:
1. Run test_scraper.py and share the output
2. Check Django logs for errors
3. Try scraping a single school with --verbose
4. Share the school website URL if it's failing

---

**Remember**: Scraping is just a starting point. Manual verification and research will always be needed for complete coverage!