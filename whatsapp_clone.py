from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import random
import string

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

users = {}  # {session_id: username}
groups = {}  # {group_code: {members: [user1, user2]}}
contacts = {}  # {username: [contact1, contact2]}

# Fungsi untuk membuat kode grup unik
def generate_group_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Route utama untuk menampilkan halaman
@app.route("/")
def home():
    return app.send_static_file("index.html")

# Menampilkan daftar user online
@app.route("/users_online", methods=["GET"])
def users_online():
    return jsonify({"users": list(users.values())})

# Endpoint untuk membuat grup
@app.route('/create_group', methods=['POST'])
def create_group():
    group_code = generate_group_code()
    groups[group_code] = {'members': []}
    return jsonify({'group_code': group_code})

# Endpoint untuk bergabung ke grup
@app.route('/join_group', methods=['POST'])
def join_group():
    data = request.json
    group_code = data['group_code']
    user = data['user']
    
    if group_code in groups:
        groups[group_code]['members'].append(user)
        return jsonify({'status': 'Joined group'})
    return jsonify({'error': 'Group not found'}), 404

# Endpoint untuk menambahkan kontak
@app.route('/add_contact', methods=['POST'])
def add_contact():
    data = request.json
    user = data['user']
    contact = data['contact']

    if user not in contacts:
        contacts[user] = []
    contacts[user].append(contact)

    return jsonify({"message": f"{contact} added to {user}'s contact list."})

# Endpoint untuk mengirim pesan langsung
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    recipient = data['recipient']
    message = data['message']
    
    if recipient in users:
        socketio.emit('new_message', {'sender': data['sender'], 'message': message}, room=users[recipient])
        return jsonify({'status': 'Message sent'})
    return jsonify({'error': 'User not found'}), 404

# WebSocket event saat user terhubung
@socketio.on('connect')
def connect():
    username = request.args.get("username")
    if username:
        users[request.sid] = username
        emit("user_list", list(users.values()), broadcast=True)
        socketio.emit('notification', {'message': f"{username} is online!"}, broadcast=True)
        print(f"{username} connected")

# WebSocket event untuk mengirim pesan ke grup
@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    message = data['message']
    sender = users.get(request.sid, "Unknown")

    if room in groups:
        send({"user": sender, "message": message}, room=room)
        socketio.emit('notification', {"message": f"New message from {sender} in {room}!"}, room=room)

# WebSocket event untuk bergabung ke grup
@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    username = users.get(request.sid, "Unknown")

    if room in groups:
        join_room(room)
        send({"message": f"{username} has joined the group!"}, room=room)

# WebSocket event untuk keluar dari grup
@socketio.on('leave_room')
def handle_leave_room(data):
    room = data['room']
    username = users.get(request.sid, "Unknown")

    if room in groups:
        leave_room(room)
        send({"message": f"{username} has left the group!"}, room=room)

# WebSocket event saat user terputus
@socketio.on('disconnect')
def disconnect():
    if request.sid in users:
        username = users.pop(request.sid)
        emit("user_list", list(users.values()), broadcast=True)
        print(f"{username} disconnected")

if __name__ == "__main__":
    socketio.run (app, host='0.0.0.0', port=5000, debug=True)
