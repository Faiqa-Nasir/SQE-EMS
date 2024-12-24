from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_pymongo import PyMongo
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure MongoDB
app.config["MONGO_URI"] = "mongodb+srv://faiqanasir60:Cv6Ww5mwwMYoO3Rf@spotifycluster.bxgjx.mongodb.net/evote?retryWrites=true&w=majority&appName=SpotifyCluster"
app.config["MONGO_DBNAME"] = "evote"
mongo = PyMongo(app)

def format_response(success, message, data=None):
    return jsonify({"success": success, "message": message, "data": data})

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize admin user
@app.before_first_request
def create_admin():
    if not mongo.db.admins.find_one({"cnic": "admin_cnic"}):
        mongo.db.admins.insert_one({
            "admin_id": "admin",
            "name": "Admin",
            "cnic": "admin_cnic",
            "dob": "1970-01-01"
        })

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # Render login page
    elif request.method == 'POST':
        data = request.json
        cnic = data.get('cnic')
        dob = data.get('dob')

        user = mongo.db.voters.find_one({"cnic": cnic, "dob": dob})
        if user:
            session['user'] = {"id": user['voter_id'], "role": "voter"}
            return format_response(True, "Login successful", {"role": "voter"})
        
        admin = mongo.db.admins.find_one({"cnic": cnic, "dob": dob})
        if admin:
            session['user'] = {"id": admin['admin_id'], "role": "admin"}
            return format_response(True, "Login successful", {"role": "admin"})
        
        return format_response(False, "Invalid credentials")

# Voter Registration
@app.route('/register_voter', methods=['POST'])
@admin_required
def register_voter():
    data = request.json
    name = data.get('name')
    cnic = data.get('cnic')
    dob = data.get('dob')
    age = data.get('age')

    if mongo.db.voters.find_one({"cnic": cnic}):
        return format_response(False, "Voter already registered.")
    if int(age) < 18:
        return format_response(False, "Voter must be at least 18 years old.")

    mongo.db.voters.insert_one({"name": name, "cnic": cnic, "dob": dob, "age": age, "voted": False})
    return format_response(True, "Voter registered successfully.")

# Candidate Management
@app.route('/add_candidate', methods=['POST'])
@admin_required
def add_candidate():
    data = request.json
    name = data.get('name')
    party = data.get('party')

    if mongo.db.candidates.find_one({"name": name, "party": party}):
        return format_response(False, "Candidate already exists.")

    mongo.db.candidates.insert_one({"name": name, "party": party})
    return format_response(True, "Candidate added successfully.")

# Election Scheduling
@app.route('/create_election', methods=['POST'])
@admin_required
def create_election():
    data = request.json
    name = data.get('name')
    start_date = datetime.fromisoformat(data.get('start_date'))
    end_date = datetime.fromisoformat(data.get('end_date'))

    if start_date >= end_date:
        return format_response(False, "Invalid election schedule.")

    mongo.db.elections.insert_one({"name": name, "start_date": start_date, "end_date": end_date, "votes": {}})
    return format_response(True, "Election created successfully.")

@app.route('/delete_election/<election_id>', methods=['DELETE'])
@admin_required
def delete_election(election_id):
    result = mongo.db.elections.delete_one({"_id": election_id})
    if result.deleted_count == 0:
        return format_response(False, "Election not found.")
    return format_response(True, "Election deleted successfully.")


# Results and Analytics
@app.route('/get_results/<election_id>', methods=['GET'])
@login_required
def get_results(election_id):
    election = mongo.db.elections.find_one({"_id": election_id})
    if not election:
        return format_response(False, "Election not found.")

    votes = election.get('votes', {})
    if not votes:
        return format_response(False, "No votes cast yet.")

    winner_id = max(votes, key=votes.get)
    winner = mongo.db.candidates.find_one({"_id": winner_id})
    return format_response(True, "Results retrieved successfully.", {
        "results": votes,
        "winner": {
            "candidate_id": winner_id,
            "name": winner['name'],
            "votes": votes[winner_id]
        }
    })

@app.route('/available_elections', methods=['GET'])
@login_required
def available_elections():
    current_time = datetime.now()
    elections = mongo.db.elections.find({"start_date": {"$lte": current_time}, "end_date": {"$gte": current_time}})
    election_list = [{"election_id": str(election["_id"]), "name": election["name"]} for election in elections]
    return format_response(True, "Available elections retrieved successfully.", election_list)

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/login_page')
def login_page():
    return render_template('login.html')
@app.route('/send_notification', methods=['POST'])
@admin_required
def send_notification():
    data = request.json
    recipient_id = data.get('recipient_id')
    message = data.get('message')

    if not recipient_id or not message:
        return format_response(False, "Recipient ID and message are required.")

    # Save the notification to the database
    mongo.db.notifications.insert_one({
        "recipient_id": recipient_id,
        "message": message,
        "timestamp": datetime.now()
    })

    return format_response(True, "Notification sent successfully.")

@app.route('/get_notifications/<recipient_id>', methods=['GET'])
@login_required
def get_notifications(recipient_id):
    # Fetch all notifications for the recipient
    notifications = list(mongo.db.notifications.find({"recipient_id": recipient_id}))
    notifications_list = [
        {
            "message": notification["message"],
            "timestamp": notification["timestamp"]
        }
        for notification in notifications
    ]

    return format_response(True, "Notifications retrieved successfully.", notifications_list)
@app.route('/cast_vote', methods=['POST'])
@login_required
def cast_vote():
    data = request.json
    voter_id = session['user']['id']
    election_id = data.get('election_id')
    candidate_id = data.get('candidate_id')

    # Existing logic for vote casting...

    # Notify the voter about the successful vote
    mongo.db.notifications.insert_one({
        "recipient_id": voter_id,
        "message": f"Your vote in election {election_id} has been successfully cast.",
        "timestamp": datetime.now()
    })

    return format_response(True, "Vote cast successfully.")


if __name__ == '__main__':
    app.run(debug=True)

