from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!123'
socketio = SocketIO(app)

rooms = {}

# creates a unique code for a room - and prevents duplicates
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code


@app.route('/', methods=['POST', 'GET'])
def home():
    # direct user to home page 
    session.clear()

    # variables that obtain information of user's inputs
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        join = request.form.get('join', False)
        create = request.form.get('create', False)

        if not name:
            return render_template('home.html', error='Please enter a name.', code=code, name=name)
        
        if join != False and not code:
            return render_template('home.html', error='Please enter a room code.', code=code, name=name)
        
        # creating a room
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members":0, "messages": []}
        
        # joining a room 
        elif code not in rooms:
            return render_template('home.html', error='Room does not exist.', code=code, name=name)
        
        # alternative to auth - save temporary data of room and user's name / sesison data will still be present even if website is refreshed 
        session['room'] = room
        session['name'] = name

        # redirects user to the room after joining/ creating
        return redirect(url_for('room'))
    
     # Get the list of room codes
    room_codes = list(rooms.keys())

    # Pass the room codes to the template
    return render_template('home.html', room_codes=room_codes)


@app.route('/room')
def room():
    room = session.get('room')
    
    # prevents user from accessing /room directly without first inpoutting name 
    if room is None or session.get('name') is None or room not in rooms:
        return redirect(url_for('home'))
    
    return render_template('room.html', code=room, messages=rooms[room]['messages'])


@socketio.on('message')
def message(data):
    # getting room user is in
    room = session.get('room')

    # if user is sending message in a non existant room:
    if room not in rooms:
        return
    
    #generating content we want to send (later on add time stamps in this section)
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    # send message to room
    send(content, to=room)
    rooms[room]['messages'].append(content)
    print(f"{session.get('name')} said {data['data']}")


@socketio.on('connect')
def connect(auth):

    # get user's room and name
    room = session.get('room')
    name = session.get('name')

    # prevents user from accessing /room directly without first going through home page
    if not room or not name: 
        return
    
    if room not in rooms:
        leave_room(room)
        return
    
    # join user to room
    join_room(room)
    # sends message to show user joining room
    send({'name': name, 'message': 'has entered the room'}, to=room)
    # keep track of # of users after they connected to socket and joined
    rooms[room]['members'] += 1
    print(f'{name} joined room {room}')


@socketio.on('disconnect')
def disconnect():
    
    # get user's room and name
    room = session.get('room')
    name = session.get('name')

    # leave user from room
    leave_room(room)

    # updates member count - if it reaches 0 then deletes room
    if room in rooms:
        rooms[room]['members'] -= 1
        if rooms[room]['members'] <= 0:
            del rooms[room]
        
    # sends message to show user leaving room
    send({'name': name, 'message': 'has left the room'}, to=room)
    print(f'{name} left room {room}')

        


if __name__ == '__main__':
    socketio.run(app, debug=True)


