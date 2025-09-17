# VPN Project Quickstart

## Django Admin App
1. Apply database migrations:
   ```bash
   python3 manage.py migrate
   ```
2. Collect static assets:
   ```bash
   python3 manage.py collectstatic --noinput
   ```
3. Create an admin user:
   ```bash
   python3 manage.py createsuperuser
   ```
4. Run the server:
   ```bash
   python3 manage.py runserver 0.0.0.0:8000
   ```

## Client Info API (other node)
Start the FastAPI service with uvicorn:
```bash
uvicorn client_info_api:app --reload --host 0.0.0.0 --port 8080
```
