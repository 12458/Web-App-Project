###########
# Imports #
###########

from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
from functools import wraps
from graphviz import Graph
from werkzeug.utils import secure_filename
import smtplib

###########
app = Flask('__name__')
#################
# Configuration #
#################

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # limit the maximum allowed payload to 16 megabytes
db_path = 'database.db'
DEBUG = True
UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

#################

# Set secure secret key
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(16)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def open_DB():
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def login_required(func):
    '''
    If you decorate a view with this, it will ensure that the current user is
    logged in and authenticated before calling the actual view. (If they are
    not, it calls the :attr:`LoginManager.unauthorized` callback.) For
    example::
        @app.route('/post')
        @login_required
        def post():
            pass
    If there are only certain times you need to require that your user is
    logged in, you can do so with::
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
    ...which is essentially the code that this function adds to your views.
    It can be convenient to globally turn off authentication when unit testing.
    To enable this, if the application configuration variable `LOGIN_DISABLED`
    is set to `True`, this decorator will be ignored.
    .. Note ::
        Per `W3 guidelines for CORS preflight requests
        <http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0>`_,
        HTTP ``OPTIONS`` requests are exempt from login checks.
    :param func: The view function to decorate.
    :type func: function
    '''
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not 'logged_in' in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated_view


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/admin')
@login_required
def admin():
    con = open_DB()
    cur = con.execute('SELECT * FROM places')
    rows = cur.fetchall()
    con.close()
    username = session['username']
    return render_template('admin.html', username=username, places=rows, graph=get_link())


@app.route('/manage_admin')
@login_required
def manage_admin():
    con = open_DB()
    cur = con.execute('SELECT id FROM admin')
    rows = cur.fetchall()
    con.close()
    return render_template('manage_admin.html', users=rows)

@app.route('/manage_admin/delete/<user>')
@login_required
def remove_admin(user):
    con = open_DB()
    cur = con.execute('DELETE FROM admin WHERE id=?',(user,))
    con.commit()
    con.close()
    return redirect(url_for('manage_admin'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        con = open_DB()
        cur = con.cursor()
        userNotExist = 'This username does not exist'
        incorrectPass = 'Incorrect password. Please try again. '
        username = request.form['userId']
        password = request.form['password']
        cur.execute('SELECT id FROM admin WHERE id=?', (username,))
        row = cur.fetchall()
        if len(row) == 0:
            flash(userNotExist, 'user_error')
        else:
            cur.execute('SELECT * FROM admin WHERE id=?', (username,))
            row = cur.fetchone()
            if check_password_hash(row['password'], password):
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('admin'))
            else:
                flash(incorrectPass, 'pass_error')
    return render_template('login.html')


@ app.route('/')
def home():
    con = open_DB()
    cur = con.execute('SELECT * FROM places')
    rows = cur.fetchall()
    return render_template('main.html', places=rows)


@ app.route('/add_location')
@login_required
def show_add_location_form():
    return render_template('add_place.html')


@ app.route('/submit', methods=['POST'])
@login_required
def submit_add_location():
    name = request.form['name']
    description = request.form['description']
    capacity = request.form['capacity']
    availability = request.form['availability']
    con = open_DB()
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and allowed_file(image_file.filename):
            image_file_name = secure_filename(image_file.filename)
            image_file.save(app.config['UPLOAD_FOLDER'] + image_file_name)
            try:
                con.execute('INSERT INTO places(Name, Description, Capacity, Availability, Image) VALUES (?,?,?,?,?)',
                            (name, description, capacity, availability, image_file_name))
            except Exception as e:
                print(str(e))
    else:
        try:
            con.execute('INSERT INTO places(Name, Description, Capacity, Availability) VALUES (?,?,?,?)',
                        (name, description, capacity, availability))
        except Exception as e:
            print(str(e))
    con.commit()
    con.close()
    return redirect(url_for('home'))


@ app.route('/view_location/<location>', methods=['GET', 'POST'])
def view_location(location):
    linked_locations = []
    try:
        con = open_DB()
        cur = con.cursor()
        cur.execute('SELECT * FROM places WHERE id=?', (location,))
        row = cur.fetchone()
        sql_get_link = \
        '''
        SELECT p.name, p.ID FROM link l 
        INNER JOIN places p
        ON l.location2 = p.id
        WHERE l.location1=? 
        UNION 
        SELECT p.name, p.ID FROM link l 
        INNER JOIN places p
        ON l.location1 = p.id
        WHERE l.location2=? 
        '''
        cur.execute(sql_get_link, (location,location))
        linked_locations = cur.fetchall()
        con.close()
    except Exception as e:
        print(str(e))
    exitFlag = len(linked_locations)
    return render_template('view_place.html', place=row, linked_locations=linked_locations, exitFlag=exitFlag, Location=location)


@ app.route('/edit/<location>', methods=['GET'])
@login_required
def edit_location(location):
    try:
        con = open_DB()
        cur = con.cursor()
        cur.execute('SELECT * FROM places where name=?', (location,))
        row = cur.fetchone()
        con.close()
    except Exception as e:
        print(str(e))
    return render_template('edit_place.html', place=row, Location=location)


@ app.route('/edit/<location>', methods=['POST'])
@login_required
def update_location(location):
    image_file_name = ''
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and allowed_file(image_file.filename):
            image_file_name = secure_filename(image_file.filename)
            image_file.save(app.config['UPLOAD_FOLDER'] + image_file_name)
    try:
        con = open_DB()
        cur = con.cursor()
        if request.form['submit'] == 'update' and image_file_name == '':
            cur.execute('UPDATE places SET name=?, description=?, capacity=?, availability=? WHERE name=?',
                        (request.form['name'], request.form['description'], request.form['capacity'], request.form['availability'], request.form['name']))
        elif request.form['submit'] == 'update' and image_file_name != '':
            cur.execute('UPDATE places SET name=?, description=?, capacity=?, availability=?, image=? where name=?)',
                        (request.form['name'], request.form['description'], request.form['capacity'], request.form['availability'], request.form['image'], request.form['name']))
        elif request.form['submit'] == 'delete':
            cur.execute('DELETE FROM link WHERE location1 = ? OR location2 = ?', (location, location))
            cur.execute('DELETE FROM places where name=?', (location,))
            msg = 'Location Deleted.'
        con.commit()
        con.close()
    except Exception as e:
        print(str(e))
    try:
        con = open_DB()
        cur = con.cursor()
        cur.execute('SELECT * FROM places WHERE name=?', (location,))
        row = cur.fetchone()
        con.close()
    except Exception as e:
        print(str(e))
    if request.form['submit'] == 'delete':
        return redirect('/home')
    return render_template('view_place.html', place=row)


@ app.route('/add_link', methods=['GET', 'POST'])
@login_required
def add_link():
    if request.method == 'POST':
        try:
            con = open_DB()
            cur = con.cursor()
            if request.form['submit'] == 'update':
                cur.execute('INSERT INTO link (location1, location2) VALUES (?,?)',
                            (request.form['location_1'], request.form['location_2']))
            con.commit()
            con.close()
        except Exception as e:
            print(str(e))
        return redirect(url_for('add_link'))
    else:
        try:
            con = open_DB()
            cur = con.cursor()
            cur.execute('SELECT ID, name FROM places')
            location_list = cur.fetchall()
            con.commit()
            con.close()
        except Exception as e:
            print(str(e))
        return render_template('add_link.html', location_list=location_list, graph=get_link())


@app.route('/logout')
@login_required
def logout():
    '''
    Logout the current user
    '''
    session.clear()
    return redirect(url_for('home'))


def get_link():
    try:
        con = open_DB()
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute('SELECT DISTINCT a.name,b.name FROM link l \
        INNER JOIN places a \
        ON l.location2 = a.id \
        INNER JOIN places b \
        ON l.location1 = b.id')
        con.row_factory = sqlite3.Row
        edges_raw = cur.fetchall()
        cur.execute('SELECT DISTINCT Name FROM places')
        nodes_raw = cur.fetchall()
        con.close()
    except Exception as e:
        print(str(e))
    return render_graph(node=nodes_raw, edge=edges_raw)


def render_graph(**data):
    '''
    Uses Graphviz to create a visual representation of the links between places
    Takes in Arbitrary Keyword Arguments, **kwargs
    Expects 2 parameters: Node and Edge
    Node should be a 1D list --> ['A','B','C']
    Edge should be a nested list --> [['A','B'],['B','C']]
    Returns SVG code: Put in render_template directly
    '''
    graph = Graph('Places', engine='neato')
    for node in data['node']:
        graph.node(str(node[0]))
    for edge in data['edge']:
        graph.edge(str(edge[0]), str(edge[1]))
        print(f'Connected {str(edge[0])} <--> {str(edge[1])}')
    chart_output = graph.pipe(format='svg').decode('utf-8')
    return chart_output


if __name__ == '__main__':
    app.run(debug=True)
