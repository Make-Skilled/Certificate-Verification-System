# Certificate Verification System

A web application for certificate issuance and verification using Flask and MongoDB.

## Prerequisites
- Python 3.7+
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account (or local MongoDB instance)

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Certificate-Verification-System
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure MongoDB**
   - The app uses a MongoDB Atlas connection string by default (see `app.py`).
   - To use your own database, update the `MongoClient` URI in `app.py`.

4. **Run the application**
   ```bash
   python app.py
   ```
   The app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Notes
- For certificate generation, the app uses the `Pillow` and `reportlab` libraries.
- To verify certificates, PNG files are required.
- For production, update the `app.secret_key` and secure your database credentials. 