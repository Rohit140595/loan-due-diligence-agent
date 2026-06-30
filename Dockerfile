# Single image, two services (see docker-compose.yml): the data API and
# the Streamlit UI both run from this same image with different
# commands, rather than maintaining two near-identical Dockerfiles.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# db/loan_data.db and db/chroma/ are gitignored (regenerated from
# fixtures/, not committed) -- docker-compose's "migrate" service runs
# the two migration scripts before "api"/"ui" start, so a fresh
# container always has current data without baking a stale DB into the
# image.

EXPOSE 8000 8501
