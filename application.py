# Udacity Full Stack Nanodegree Project: Item Catalog
# a web application that provides a list of items within a variety of
# categories and integrates third party user registration and authentication.
# Authenticated users have the ability to post, edit, and delete
# their own items

from flask import (Flask, render_template, request, redirect,
                   jsonify, url_for, flash)
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# google plus login function
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already \
                                            connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;\
                -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


# logout fron google plus
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view catalog information
@app.route('/catalog/JSON')
def catalogJSON():
    categories = session.query(Category).all()
    CategoryItems = []
    for cat in categories:
        serializedCat = cat.serialize
        items = session.query(Item).filter_by(category_id=cat.id).all()
        serializedItems = []
        for i in items:
            serializedItems.append(i.serialize)
        serializedCat['items'] = serializedItems
        CategoryItems.append(serializedCat)
    return jsonify(Category=CategoryItems)


@app.route('/catalog/<int:category_id>/items/JSON')
def categoryJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    return jsonify(CategoryItems=[i.serialize for i in items])


@app.route('/catalog/<int:category_id>/items/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    Item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=Item.serialize)


# add a new item to the database
@app.route('/catalog/new-item/', methods=['GET', 'POST'])
def newItem():
    if 'username' not in login_session:
        flash('You must be logged in to create a new item')
        return redirect('/login')
    if request.method == 'POST':
        name = request.form['item']
        description = request.form['description']
        cat = request.form['category']
        if cat == 'new':
            newCategory = Category(name=request.form['new-category'])
            cat = newCategory
            session.add(cat)
        else:
            existingCat = session.query(Category).filter_by(name=cat).one()
            cat = existingCat
        user = session.query(User).filter_by(id=login_session['user_id']).one()
        # create new item and commit to the database
        newItem = Item(name=name, description=description, category=cat,
                       user=user)
        session.add(newItem)
        session.commit()
        flash('New Item %s successfully created' % (newItem.name))
        return redirect(url_for('showCategory',
                                category_id=newItem.category_id))
    else:
        categories = session.query(Category).all()
        return render_template('new-item.html', categories=categories)


# edit an existing item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/edit/',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != editedItem.user_id:
        # RETURN AN ERROR MESSAGE
        flash('You cannot edit an item that you did not create')
        return redirect(url_for('showItem', category_id=category_id,
                                item_id=item_id))
    if request.method == 'POST':
        if request.form['item']:
            editedItem.name = request.form['item']
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showItem', category_id=category_id,
                                item_id=item_id))
    else:
        return render_template('edit-item.html', category_id=category_id,
                               item=editedItem)


# delete an existing item from the database
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/delete/',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != itemToDelete.user_id:
        # RETURN AN ERROR MESSAGE
        flash('You cannot delete an item that you did not create')
        return redirect(url_for('showItem', category_id=category_id,
                                item_id=item_id))
    if request.method == 'POST':
        confirm = request.form['answer']
        if confirm == 'yes':
            deletedCatID = itemToDelete.category_id
            session.delete(itemToDelete)
            session.commit()
            flash('item successfully deleted')
            # if no items left in category - delete the category
            categoryToDelete = session.query(Category).filter_by(
                id=category_id).one()
            itemsInCategory = session.query(Item).filter_by(
                category_id=category_id).first()
            if itemsInCategory is None:
                # get rid of empty category
                session.delete(categoryToDelete)
                session.commit()
            return redirect(url_for('showCatalog'))
        else:
            return redirect(url_for('showItem', category_id=category_id,
                                    item_id=item_id))
    else:
        return render_template('delete-item.html', item=itemToDelete)


# display the selected category's items
@app.route('/catalog/category/<int:category_id>/')
def showCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    categories = session.query(Category).order_by(asc(Category.name))
    return render_template('category.html', category=category, items=items,
                           categories=categories)


# display the selected item
@app.route('/catalog/category/<int:category_id>/item/<int:item_id>/')
def showItem(category_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return render_template('item.html', item=item)


# home page
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    categories = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(desc(Item.id)).limit(5).all()
    return render_template('main-catalog.html', categories=categories,
                           items=items)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
