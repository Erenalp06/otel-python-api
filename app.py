from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
import logging

#OpenTelemetry importları
from opentelemetry.trace import Span
from opentelemetry import trace

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

#before_request Hook - İstek gövdesini (body) OpenTelemetry span'e ekle
@app.before_request
def add_request_body_to_trace():
    span = trace.get_current_span()
    if span and isinstance(span, Span):
        span.set_attribute("http.request.body", request.get_data(as_text=True))

@app.after_request
def after_request(response):
    span = trace.get_current_span()
    if span and response.content_type == "application/json":
        span.set_attribute("http.response.body", response.get_data(as_text=True))
    return response

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///test.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
pg_engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

#Model (User)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

#POST /users/add
@app.route("/users/add", methods=["POST"])
def add_user():
    try:
        data = request.json
        name = data.get("name")
        if not name:
            return jsonify({"error": "Name is required"}), 400
        
        session = scoped_session(SessionLocal)
        new_user = User(name=name)
        session.add(new_user)
        session.commit()
        user_id = new_user.id
        session.close()

        return jsonify({
            "message": "User added successfully",
            "user_id": user_id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#POST /users/make_admin
@app.route("/users/make_admin", methods=["POST"])
def make_admin():
    try:
        data = request.json
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        session = scoped_session(SessionLocal)
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            session.close()
            return jsonify({"error": "User not found"}), 404
        
        user.is_admin = True
        session.commit()
        session.close()

        return jsonify({
            "message": f"User {user_id} is now admin"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#POST /users/deactivate
@app.route("/users/deactivate", methods=["POST"])
def deactivate_user():
    try:
        data = request.json
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        session = scoped_session(SessionLocal)
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            session.close()
            return jsonify({"error": "User not found"}), 404

        user.is_active = False
        session.commit()
        session.close()

        return jsonify({
            "message": f"User {user_id} has been deactivated"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5005, debug=False)
