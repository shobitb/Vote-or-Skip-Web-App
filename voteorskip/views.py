from voteorskip import app
from models import Category, Item, UserVote
from flask import request, render_template, redirect, flash, url_for, jsonify
from google.appengine.api import users
from google.appengine.ext import db
from decorators import login_required
import random
import string
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
import urllib,urllib2

@app.route('/')
def index():
	categories = Category.all()
	return render_template('index.html',categories=categories)

@app.route('/create_category', methods=['GET','POST'])
@login_required
def create_category():
	return render_template('create_category.html')

@app.route('/save_new_category',methods=['POST'])
@login_required
def save_new_category():
	category = request.form.get('category')
	items = request.form.get('items').split(',')
	key = category_key(category,users.get_current_user().nickname())
	cat = Category(key_name=category+users.get_current_user().nickname(), title=category, owner=users.get_current_user())
	cat.put()
	for i in items:
		if not i == '':
			item = Item(parent=key,title=i)
			item.put()
	return jsonify(items=items)

@app.route('/save_edited_category',methods=['POST'])
@login_required
def save_edited_category():
	new_category_name = request.form.get('category')
	old_category_name = request.form.get('oldCategory')
	items_from_form = request.form.get('items').split(',')
	old_key = category_key(old_category_name,users.get_current_user().nickname())
	old_category = Category.all().filter('owner =',users.get_current_user()).filter('title =',old_category_name).get()
	old_items_from_db = Item.all().ancestor(old_key)
	
	for item in old_items_from_db:
		if item.title not in items_from_form:
			db.delete(item)

	old_category.title = new_category_name
	old_category.put()

	return jsonify(items=items_from_form)

@app.route('/edit')
@login_required
def edit():
	categories = Category.all().filter('owner = ',users.get_current_user())
	return render_template('edit.html',categories=categories)

@app.route('/edit/categories/<title>/<owner>',methods=['GET','POST'])
def edit_category(title,owner):
	if owner != users.get_current_user().nickname():
		error = "You cannot edit a category that you do not own!"
		return render_template('errors.html',error=error)
	items = Item.all().ancestor(category_key(title,owner))
	return render_template('edit_category.html',items=items,title=title)

@app.route('/categories/<title>/<owner>',methods=['GET','POST'])
@login_required
def show_category(title,owner):
	category = category_key(title,owner)
	random_items = get_random_items(category)

	if not request.form.has_key('item') or request.form.has_key('skip'):
		return render_template('category.html',title=title,owner=owner,items=random_items)

	winner = request.form.get('item')
	loser = request.form.get('2') if winner == request.form.get('1') else request.form.get('1')
	
	winner_item = get_item(category,winner)
	loser_item = get_item(category,loser)

	winner_item.wins = winner_item.wins + 1
	loser_item.losses = loser_item.losses + 1

	uservote_winner = get_uservote(winner_item)
	uservote_loser = get_uservote(loser_item)

	if not uservote_winner:
		uservote_winner = UserVote(parent=winner_item,voter=users.get_current_user(),wins=1)
	else:
		uservote_winner.wins = uservote_winner.wins + 1

	if not uservote_loser:
		uservote_loser = UserVote(parent=loser_item,voter=users.get_current_user(),losses=1)
	else:
		uservote_loser.losses = uservote_loser.losses + 1

	uservote_winner.put()
	uservote_loser.put()
	winner_item.put()
	loser_item.put()

	return render_template('category.html', title=title, owner=owner, items=random_items, winner=winner, loser=loser)

@app.route('/results/<title>/<owner>')
@login_required
def results(title,owner):
	my_votes = {}
	category = category_key(title,owner)
	items = Item.all().ancestor(category).order('-wins').order('losses')
	count = 0
	for i in items:
		item = UserVote.all().ancestor(i).order('-wins').order('losses').filter('voter =', users.get_current_user()).get()
		if not item:
			my_votes[count] = [i.title, "-", "-"]
		else:
			my_votes[count] = [i.title, item.wins, item.losses] # the count helps maintain the order -wins and losses
		count += 1
	return render_template('results.html',items=items, title=title, owner=owner, my_votes=my_votes)

@app.route('/upload',methods=['POST'])
def upload():
	xml = self.form.get('xml-file').file.read()
	return render_template('create_category.html', xml=xml)

def category_key(title,owner):
	return db.Key.from_path('Category', title + owner)

def get_item(category,title):
	items = Item.all().filter('title =',title).ancestor(category)
	return items.get()

def get_uservote(item):
	return UserVote.gql("WHERE ANCESTOR IS :1 AND voter = :2",item,users.get_current_user()).get()

def get_random_items(category):
	items = Item.gql("WHERE ANCESTOR IS :1",category)
	length = items.count()
	one = random.randint(0, length-1)
	two = one
	while two == one:
		two = random.randint(0, length-1)
	return [items[one].title, items[two].title]