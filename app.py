from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/telemetry'
app.config['SQLALCHEMY_BINDS'] = {
    'sqlite': 'sqlite:///telemetry.db',
    'postgres': 'postgresql://postgres:postgres@localhost/telemetry'
}
#app.config["SQLALCHEMY_ECHO"] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

pg_engine = create_engine('postgresql://postgres:postgres@localhost/telemetry')

# Create User Model for Postgre
class User(db.Model):
    __bind_key__ = 'postgres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

class SQLiteUser(db.Model):
    __bind_key__ = 'sqlite'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

sqlite_engine = create_engine(app.config['SQLALCHEMY_BINDS']['sqlite']) 


#API Routes
@app.route("/", methods=["GET"])
def get_users():
    try:
        users = User.query.all()
        return jsonify({"users:": [{"id": user.id, "name": user.name} for user in users]}), 200       
    except Exception as e:
        return jsonify({"error": str(e)}), 500   

    
@app.route("/", methods=["POST"])
def add_user():
    try:
        name = request.json['name']

        
        sqlite_session = scoped_session(sessionmaker(bind=sqlite_engine))
        sqlite_user = SQLiteUser(name=name)        
        sqlite_session.add(sqlite_user)
        sqlite_session.commit()  

        pg_session = scoped_session(sessionmaker(bind=pg_engine))

        pg_user = User(name=name)
        pg_session.add(pg_user)
        pg_session.commit()       

        return jsonify({"postgresql_id": pg_user.id, "sqlite_id":sqlite_user.id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fetch-data")
def fetch_data():
    try:
        url =  "https://api.thecatapi.com/v1/images/search"
        response = requests.get(url)
        response.raise_for_status()    
        data = response.json()

        return jsonify(data), 200
    except Exception as e:
        status_code = response.status_code if hasattr(response, 'status_code') else 500
        return jsonify({"error": "Failed to fetch data " + str(e)}), status_code
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()    
        engine = create_engine(app.config['SQLALCHEMY_BINDS']['sqlite'])
        SQLiteUser.metadata.create_all(engine)        
    app.run(host="0.0.0.0", port=5005, debug=False)

    
