FROM apache/superset:latest

USER root

# מתקינים את פוסטגרס ישירות לתוך תיקיית הפייתון של סופרסט כדי לעקוף בעיות של סביבות וירטואליות
RUN pip install --target /app/pythonpath --no-cache-dir psycopg2-binary==2.9.9

COPY superset_config.py /app/pythonpath/superset_config.py
COPY superset-init.sh /app/superset-init.sh
RUN chmod +x /app/superset-init.sh

USER superset

# שורת הקסם שהייתה חסרה - מכריחה את דוקר להריץ את סקריפט האתחול שלנו!
CMD ["/app/superset-init.sh"]