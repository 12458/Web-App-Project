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

###########

app = Flask('__name__')

#################
# Configuration #
#################

# limit the maximum allowed payload to 16 megabytes
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db_path = 'database.db'
UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

#################

# Set secure secret key
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(16)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def open_DB():
    '''
    Opens and returns a DB connection
    '''
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
    '''
    Ensure no funny filenames are uploaded
    '''
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_locations():
    '''
    Retrieve ALL locations ordered by alphabetical order in ascending order
    '''
    con = open_DB()
    cur = con.cursor()
    cur.execute('SELECT * FROM places ORDER BY Name')
    location_list = cur.fetchall()
    con.close()
    return location_list


def get_admin():
    '''
    Helper function to retreive admin(s) from DB
    '''
    con = open_DB()
    cur = con.execute('SELECT id FROM admin')
    rows = cur.fetchall()
    con.close()
    return rows


def get_link():
    '''
    Returns Graph (SVG) of the current edges between locations
    '''
    try:
        con = open_DB()
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        sql_statement = \
            '''
        SELECT DISTINCT a.name,b.name FROM link l 
        INNER JOIN places a 
        ON l.location2 = a.id 
        INNER JOIN places b 
        ON l.location1 = b.id
        '''
        cur.execute(sql_statement)
        con.row_factory = sqlite3.Row
        edges_raw = cur.fetchall()
        cur.execute('SELECT DISTINCT Name FROM places')
        nodes_raw = cur.fetchall()
        con.close()
    except Exception as e:
        flash(str(e))
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
    graph = Graph('Places', engine='fdp')
    for node in data['node']:
        graph.node(str(node[0]))
    for edge in data['edge']:
        graph.edge(str(edge[0]), str(edge[1]))
        print(f'Connected {str(edge[0])} <--> {str(edge[1])}')
    chart_output = graph.pipe(format='svg').decode('utf-8')
    return chart_output


@ app.route('/')
def home():
    '''
    Viewfunction to serve main tour page seen by unauthenticated user
    '''
    try:
        con = open_DB()
        cur = con.execute('SELECT * FROM places')
        rows = cur.fetchall()
    except:
        flash('An error has occured') # User is not trusted
    return render_template('main.html', places=rows)


@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    Viewfunction to serve and handle admin authentication
    '''
    if 'logged_in' in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        con = open_DB()
        cur = con.cursor()
        userNotExist = 'This username does not exist'
        incorrectPass = 'Incorrect password. Please try again. '
        username = request.form['userId']
        password = request.form['password']
        try:
            cur.execute('SELECT id FROM admin WHERE id=?', (username,))
        except:
            flash('An error has occured', 'user_error')
        row = cur.fetchall()
        if len(row) == 0:
            flash(userNotExist, 'user_error')
        else:
            try:
                cur.execute('SELECT * FROM admin WHERE id=?', (username,))
                row = cur.fetchone()
            except:
                flash('An error has occured', 'user_error')
            if check_password_hash(row['password'], password):
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('admin'))
            else:
                flash(incorrectPass, 'pass_error')
    return render_template('login.html')


@app.route('/admin')
@login_required
def admin():
    '''
    Viewfunction to serve main admin page
    '''
    try:
        location_list = get_locations()
    except Exception as error:
        # Admin is trusted so showing them raw error messages is OK
        flash(str(error))
        con = open_DB()
    username = session['username']
    return render_template('admin.html', username=username, places=location_list, graph=get_link())


@app.route('/manage_admin', methods=['GET', 'POST'])
@login_required
def manage_admin():
    '''
    Viewfunction to serve admin management page
    '''
    if request.method == 'POST':
        user = request.form['delete']
        try:
            con = open_DB()
            cur = con.execute('SELECT COUNT(*) FROM admin')
            count = cur.fetchone()
            con.close()
        except Exception as e:
            flash(str(e))
        if count[0] > 1:
            try:
                con = open_DB()
                cur = con.execute('DELETE FROM admin WHERE id=?', (user,))
                con.commit()
                con.close()
            except Exception as e:
                flash(str(e))
        else:
            flash('There must be at least 1 admin account')
        return redirect(url_for('manage_admin'))
    else:
        rows = get_admin()
        return render_template('manage_admin.html', users=rows)


@app.route('/manage_admin/add', methods=['POST'])
@login_required
def add_admin():
    '''
    Viewfunction to handle adding administrators
    '''
    username = request.form['userId']
    password = request.form['password']
    confirm_password = request.form['password_confirm']
    if len(username) == 0:
        return render_template("manage_admin.html", error_user="Username cannot be left blank", user_color='is-danger', users=get_admin())
    if len(password) == 0:
        return render_template("manage_admin.html", error_pass="Password cannot be left blank", pass_color='is-danger', users=get_admin())
    if password != confirm_password:
        return render_template('manage_admin.html', error_pass='Password does not match', pass_color='is-danger', users=get_admin())
    con = open_DB()
    cur = con.cursor()
    cur.execute('SELECT id FROM admin')
    row = cur.fetchall()
    existing_usernames = [i['id'] for i in row]
    if username in existing_usernames:
        return render_template('manage_admin.html', error_user='This username already exists', user_color='is-danger', users=get_admin())
    try:
        con = open_DB()
        con.execute("INSERT INTO admin(id, password) VALUES(?,?)", (username, generate_password_hash(password)))
        con.commit()
        con.close()
        return redirect(url_for('manage_admin'))
    except Exception as e:
        flash(str(e))


@ app.route('/add_location', methods=['GET', 'POST'])
@login_required
def add_location():
    '''
    Viewfunction to handle adding locations
    '''
    if request.method == 'POST':
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
                    flash(str(e))
        else:
            try:
                con.execute('INSERT INTO places(Name, Description, Capacity, Availability) VALUES (?,?,?,?)',
                            (name, description, capacity, availability))
            except Exception as e:
                flash(str(e))
        con.commit()
        con.close()
        return redirect(url_for('home'))
    else:
        try:
            location = get_locations()
        except Exception as e:
            flash(str(e))
        return render_template('add_place.html', places=location)


@ app.route('/update_link', methods=['POST'])
@login_required
def update_link():
    '''
    Viewfunction to handle updating links via checkbox form
    '''
    location_id = request.form['id']
    linked_locations = request.form.getlist('updated_locations')
    try:
        con = open_DB()
        # Delete all current links
        cur = con.execute('DELETE FROM link WHERE location1=? OR location2=?', (location_id, location_id))
        for new_link_id in linked_locations:
            cur = con.execute('INSERT INTO link (location1, location2) VALUES (?,?)', (location_id, new_link_id))
        con.commit()
        con.close()
    except Exception as e:
        flash(str(e))
    return redirect(url_for('home'))


@ app.route('/view_location/<location>')
def view_location(location):
    '''
    Viewfunction to serve an location requested by the user
    '''
    linked_locations = []  # Stop flask from complaining when there is no links
    try:
        locations = get_locations()
        locations = [i['id'] for i in locations]
        location_id = int(location)
    except Exception as e:
        if session['logged_in']:
            flash(str(e))
        else:
            flash('An error has occured. Please try again')
    if location_id not in locations:
        abort(404)
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
        cur.execute(sql_get_link, (location, location))
        linked_locations = cur.fetchall()
        con.close()
    except Exception as e:
        if session['logged_in']:
            flash(str(e))
        else:
            flash('An error has occured. Please try again')
    return render_template('view_place.html', place=row, linked_locations=linked_locations)


# Note radio button not working need to fix
@ app.route('/edit/<location_id>', methods=['GET', 'POST'])
@login_required
def update_location(location_id):
    '''
    Viewfunction to edit or delete existing location
    '''
    if request.method == 'POST':
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
                cur.execute('UPDATE places SET name=?, description=?, capacity=?, availability=? WHERE id=?',
                            (request.form['name'], request.form['description'], request.form['capacity'], request.form['availability'], location_id))
            elif request.form['submit'] == 'update' and image_file_name != '':
                cur.execute('UPDATE places SET name=?, description=?, capacity=?, availability=?, image=? where id=?)',
                            (request.form['name'], request.form['description'], request.form['capacity'], request.form['availability'], request.form['image'], location_id))
            elif request.form['submit'] == 'delete':
                cur.execute(
                    'DELETE FROM link WHERE location1 = ? OR location2 = ?', (location_id, location_id))
                cur.execute('DELETE FROM places where id=?', (location_id,))
            con.commit()
            con.close()
        except Exception as e:
            flash(str(e))
        if request.form['submit'] == 'delete':
            return redirect(url_for('admin'))
        return redirect(url_for('view_location', location=location_id))
    else:
        try:
            con = open_DB()
            cur = con.cursor()
            sql_get_link = \
                '''
            SELECT places.name as Place, places.ID as ID, IFNULL((p.id > 0),0) as Linked
            FROM places LEFT OUTER JOIN
            (SELECT p.name, p.ID FROM link l 
            INNER JOIN places p
            ON l.location2 = p.id
            WHERE l.location1=?
            UNION 
            SELECT p.name, p.ID FROM link l 
            INNER JOIN places p
            ON l.location1 = p.id
            WHERE l.location2=?) p
            ON places.id = p.id
            ORDER BY Linked DESC, Place ASC
            '''
            cur.execute(sql_get_link, (location_id, location_id))
            linked_locations = cur.fetchall()
            con.close()
        except Exception as e:
            flash(str(e))
        try:
            con = open_DB()
            cur = con.cursor()
            cur.execute('SELECT * FROM places where id=?', (location_id,))
            row = cur.fetchone()
            con.close()
        except Exception as e:
            flash(str(e))
        return render_template('edit_place.html', place=row, Location=location_id, linked_locations=linked_locations)


@ app.route('/add_link', methods=['GET', 'POST'])
@login_required
def add_link():
    '''
    Viewfunction to add a exit between two locations via Manage Link page
    '''
    if request.method == 'POST':
        try:
            con = open_DB()
            cur = con.cursor()
            if request.form['submit'] == 'update':
                cur.execute('INSERT INTO link (location1, location2) VALUES (?,?)', (request.form['location_1'], request.form['location_2']))
            con.commit()
            con.close()
        except Exception as error:
            flash(str(error))
        return redirect(url_for('add_link'))
    else:
        try:
            location_list = get_locations()
        except Exception as error:
            flash(str(error))
        return render_template('add_link.html', location_list=location_list, graph=get_link())


@ app.route('/remove_link', methods=['POST'])
@login_required
def remove_link():
    '''
    Viewfunction to handle removing exit between two locations via Manage Link page
    '''
    location1 = request.form['location_1']
    location2 = request.form['location_2']
    try:
        con = open_DB()
        cur = con.cursor()
        if request.form['submit'] == 'update':
            cur.execute('DELETE FROM link WHERE ((location1 = ? AND location2 = ?) OR (location1 = ? AND location2 = ?))', (location1, location2, location2, location1))
        con.commit()
        con.close()
    except Exception as error:
        abort(500)
    return redirect('add_link')


@app.route('/logout')
@login_required
def logout():
    '''
    Logout the current user
    '''
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run()
