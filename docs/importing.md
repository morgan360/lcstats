
### Importing note summary PDF from media
python manage.py import_summary_sections media/StatssSummary.pdf --topic "Statistics Summary"
### Testing embeddings
python manage.py test_embeddings descriptive-statistics

python manage.py test_embeddings descriptive-statistics --prompt "explain how to calculate the mean"

python manage.py test_embeddings

python manage.py test_embeddings descriptive-statistics --prompt "define mode" --top 5

