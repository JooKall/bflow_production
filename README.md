    *   Create a virtual environment: `python3 -m venv venv` (Use `python` if `python3` isn't available)
    *   Activate the virtual environment:
            Windows: `.\venv\Scripts\activate` (It may also be the bin folder for your system)
            Mac/Linux: `source venv/bin/activate`
    *   Install Flask: `pip install -r requirements.txt`
    *   Launch: `gunicorn app:app`