from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from database import Database 
from werkzeug.security import check_password_hash
from werkzeug.security import check_password_hash, generate_password_hash
import os
import jwt
from datetime import datetime, timedelta, timezone

app = Flask(__name__, static_url_path='', static_folder='build', template_folder='build')
CORS(app, supports_credentials=True)

db = Database("BFLOW.db")

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret_key')

def generate_token(user_id):
    expiration_time = timedelta(hours=1)
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + expiration_time 
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user, role = db.get_user_by_email(email)

    if not user or not check_password_hash(user[2], password): 
        return jsonify({"error": "Invalid username or password"}), 401
    
    token = generate_token(user[0])
    
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user_id": user[0],  
        "user_name": user[1], 
        "role": role
    })


@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_data(user_id):
    role = request.args.get('role')
    print(f"Role: {role}")  # Print the role for debugging
    if not role:
        return jsonify({"error": "Role is required"}), 400

    try:
        user = db.get_user(user_id, role)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not user:
        return jsonify({"error": "User not found"}), 404

    if role == 'player':
        user_data = {
            "id": user[0],
            "username": user[1],
            "password": user[2],
            "email": user[3],
            "name": user[4],
            "birthYear": user[6],
            "country": user[7],
            "number": user[8],
            "parent": user[9],
            "parentEmail": user[10],
            "parentPhone": user[11],
            "coach": user[12],
            "coachEmail": user[13],
            "coachPhone": user[14],
            "team": user[15],
            "shirtNumber": user[16],
            "team_id": user[17]
        }
    elif role == 'coach':
        user_data = {
            "id": user[0],
            "username": user[1],
            "password": user[2],
            "email": user[3],
            "name": user[4],
            "birthYear": user[6],
            "country": user[7],
            "team": user[8],
            "team_id": user[9]
        }
    elif role == 'parent':
        user_data = {
            "id": user[0],
            "username": user[1],
            "password": user[2],
            "email": user[3],
            "name": user[4],
            "birthYear": user[6],
            "country": user[7],
            "child_name": user[8],
            "child_email": user[9]
        }
    else:
        return {"error": "Invalid role provided"}, 400
    print(f"Fetched user data for {role}: {user_data}")
    return jsonify(user_data)

@app.route('/api/training/<int:user_id>', methods=['GET'])
def get_user_training_data(user_id):
   
    training_data = db.get_categories_and_exercises_with_ratings(user_id)

    if not training_data:
        return jsonify({"error": "No training data found for this user"}), 404

    return jsonify(training_data)

@app.route('/api/training/<int:user_id>', methods=['PUT'])
def update_training_data(user_id):
    data = request.json
    try:
        db.update_exercise(data)
        return jsonify({"message": "Training data updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


#Todo This needs to store password as a hash
@app.route('/api/register', methods=['POST'])
def add_user():
    data = request.json
    try:
        app.logger.debug(f"Received data: {data}")
        hashed_password = generate_password_hash(data["password"])
        
        user_id = db.add_user(
            username=data["username"], 
            password=hashed_password,
            email=data["email"],
            name=data["name"],
            birthYear=data["birthYear"],
            country=data["country"],
            role = data.get('role'),
            number=data.get("pelinumero"),  
            team_id=data.get("joukkue_id", None)  
        )
    
        app.logger.debug(f"User added with ID: {user_id}")
        return jsonify({"message": "User added successfully", "user_id": user_id}), 201
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    
@app.route('/api/verify-session', methods=['GET'])
def verify_session():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Token is missing"}), 401

    try:
        token = token.split(" ")[1]
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user_id = payload['user_id']

   
        user = db.get_user(user_id)
        if user:
            return jsonify({"valid": True, "userId": user_id}), 200
        else:
            return jsonify({"valid": False}), 401

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401




@app.route('/api/user/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.json
    role = data.get('role')
    if not role:
        return jsonify({"error": "Role is required"}), 400

    if 'id' in data:
        del data['id']
    if 'role' in data:
        del data['role']
    try:
        db.update_user(id, role, **data)
        return jsonify({"message": "User updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/api/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        db.delete_user(user_id)
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/team', methods=['POST'])
def create_team():
    data = request.json
    team_name = data.get('teamName')
    coach_id = data.get('coachId')

    if not team_name or not coach_id:
        return jsonify({"error": "Team name and coach ID are required"}), 400

    try:
        db.create_team(team_name, coach_id)
        return jsonify({"message": "Team created successfully"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/team/<int:coach_id>', methods=['GET'])
def get_team_by_coach(coach_id):
    try:
        team = db.get_team_by_coach(coach_id)
        if team:
            return jsonify(team)
        else:
            return jsonify({"error": "Team not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/api/join-team', methods=['POST'])
def join_team():
    data = request.json
    team_name = data.get('teamName')
    player_id = data.get('playerId')

    if not team_name or not player_id:
        return jsonify({"error": "Team name and player ID are required"}), 400

    try:
        db.join_team(team_name, player_id)
        return jsonify({"message": "Joined team successfully"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/link-child', methods=['POST'])
def link_child():
    data = request.json
    child_username = data.get('childUsername')
    parent_id = data.get('parentId')

    if not child_username or not parent_id:
        return jsonify({"error": "Child username and parent ID are required"}), 400

    try:
        db.link_child(child_username, parent_id)
        return jsonify({"message": "Child linked successfully"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)