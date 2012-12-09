from voteorskip import app
from models import Category, Item, UserVote
from flask import request, render_template, redirect, flash, url_for, jsonify
from google.appengine.api import users
from google.appengine.ext import db
from decorators import login_required
import random
import string
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

@app.route('/categories/<title>/<owner>',methods=['GET','POST'])
def show_category(title,owner):
	category = category_key(title,owner)
	random_items = get_random_items(category)

	if not request.form.has_key('item') or request.form.has_key('skip'):
		return render_template('category.html',title=title,owner=owner,items=random_items)

	winner = request.form.get('item')
	loser = request.form.get('2') if winner == request.form.get('1') else request.form.get('1')
	
	winner_item = get_item(category,winner)
	loser_item = get_item(category,loser)

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

	all_votes_winner = UserVote.all().ancestor(winner_item)
	all_votes_loser = UserVote.all().ancestor(loser_item)

	winner_w = 0
	winner_l = 0
	loser_w = 0
	loser_l = 0

	for w in all_votes_winner:
		winner_w = winner_w + w.wins
		winner_l = winner_l + w.losses

	for l in all_votes_loser:
		loser_w = loser_w + l.wins
		loser_l = loser_l + l.losses

	return render_template(
		'category.html', title=title, owner=owner, items=random_items, winner=winner, loser=loser,
		winner_w=winner_w, winner_l=winner_l, loser_w=loser_w, loser_l=loser_l
	)

def category_key(title,owner):
	return db.Key.from_path('category', title + owner)

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