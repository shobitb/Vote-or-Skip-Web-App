from voteorskip import app
from models import Category, Item, UserVote, UserComment
from flask import request, Response, render_template, redirect, flash, url_for, jsonify
from google.appengine.api import users, files, images
from google.appengine.ext import db, blobstore
from datetime import datetime
from decorators import login_required
import random
import string
import urllib,urllib2
from werkzeug import parse_options_header
from xml.etree.ElementTree import fromstring, tostring, Element, SubElement

@app.route('/')
@login_required
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
	existing = Category.all().filter('title =',category).filter('owner =',users.get_current_user()).get()
	if existing:
		return Response(status=400)
	else:
		items = request.form.get('items').split(',')
		cat = Category(title=category, owner=users.get_current_user())
		cat.put()
		for i in items:
			if not i == '':
				item = Item(parent=cat.key(),title=i)
				item.put()
		return Response(status=200)

@app.route('/save_edited_category',methods=['POST'])
@login_required
def save_edited_category():
	cat_name = request.form.get('category')
	key = request.form.get('key')
	existing = Category.all().filter('title =', cat_name).filter('owner =',users.get_current_user()).get()
	if not str(existing.key()) == key:
		error = "You already have a category with that name. Please choose a different name"
		return Response(status=400)
	category = Category.get(key)
	items_from_form = request.form.get('items').split(',')
	old_items_from_db = Item.all().ancestor(category)
	for item in old_items_from_db:
		if not item.title in items_from_form:
			db.delete(item)
		else:
			items_from_form.remove(item.title)

	for new_item in items_from_form:
		if not new_item == '':
			i = Item(parent=category,title=new_item)
			i.put()
	category.title = request.form.get('category')
	category.put()
	return jsonify(new_items = items_from_form)

@app.route('/edit')
@login_required
@login_required
def edit():
	categories = Category.all().filter('owner = ',users.get_current_user())
	return render_template('edit.html',categories=categories)

@app.route('/edit/categories/<key>', methods=['GET','POST'])
@login_required
def edit_category(key):
	category = Category.get(key)
	expiration = ""
	if category.expiration:
		expiration = category.expiration.strftime("%m/%d/%Y")
	if category.owner != users.get_current_user():
		error = "You cannot edit a category that you do not own!"
		return render_template('errors.html',error=error)
	items = Item.all().ancestor(category)
	return render_template('edit_category.html', items=items, count=items.count(), key=key, title=category.title, owner=category.owner.email(), expiration=expiration)

@app.route('/set_expiration_date/<key>',methods=['POST'])
def set_expiration(key):
	category = Category.get(key)
	date = request.form.get('date')
	category.expiration = datetime.strptime(date, "%m/%d/%Y")
	category.put()
	return jsonify(date = category.expiration.strftime("%m/%d/%Y"))

@app.route('/categories/<key>',methods=['GET','POST'])
@login_required
def show_category(key):
	category = Category.get(key)

	if category.expiration and datetime.now() > category.expiration:
		return results(key)

	if not request.form.has_key('item') or request.form.has_key('skip'):
		random_items = get_random_items(category)
		return render_template('category.html', key=key, title=category.title, owner=category.owner.email(), items=random_items)

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

	random_items = get_random_items(category)
	return render_template('category.html', key=key, title=category.title, owner=category.owner.email(), items=random_items, winner=winner, loser=loser)

@app.route('/results/<key>')
@login_required
def results(key):
	my_votes = {}
	my_comments = {}
	user_comments = {}
	expired = ""
	category = Category.get(key)
	if category.expiration and datetime.now() > category.expiration:
		expired = "This category has expired. Voting is no longer possible."
	items = Item.all().ancestor(category).order('-wins').order('losses')
	count = 0
	for i in items:
		item = UserVote.all().ancestor(i).order('-wins').order('losses').filter('voter =', users.get_current_user()).get()
		if not item:
			my_votes[count] = [i.title, "-", "-"]
		else:
			my_votes[count] = [i.title, item.wins, item.losses] # the count helps maintain the order -wins and losses
		count += 1

	for c in items:
		user_comments[c.title] = UserComment.all().ancestor(c)
		my_comment = UserComment.all().ancestor(c).filter('commenter =',users.get_current_user()).get()
		if my_comment:
			my_comments[c.title] = my_comment.comment
	return render_template('results.html',items=items, key=key, title=category.title, owner=category.owner.email(), my_votes=my_votes, my_comments=my_comments, user_comments=user_comments,expired=expired)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
	items = []
	if request.method == 'POST':
		xml = request.files.get('xml-file').read()
		root = fromstring(xml)
		xml_category = root.findall('NAME')[0].text
		for child in root.findall('ITEM'):
			for item in child.findall('NAME'):
				items.append(item.text)
	if request.form.has_key('edit'):
		return render_template('edit_category.html',xml_items=items,title=xml_category,count=len(items),key=request.form.get('key'))
	return render_template('create_category.html',xml_items=items,xml_category=xml_category)

@app.route('/export/<key>')
def export_xml(key):
	category = Category.get(key)
	items = Item.all().ancestor(category)
	disposition_filename = category.title + "_" + category.owner.email() + ".xml"
	root = Element('CATEGORY')
	SubElement(root,'NAME').text = category.title
	for item in items:
		i = SubElement(root,'ITEM')
		SubElement(i,'NAME').text = item.title
	return Response(tostring(root),status=200,mimetype="application/xml",headers={"Content-Disposition":"attachment;filename="+disposition_filename})

@app.route('/comment/<key>')
@login_required
def options_to_comment(key):
	category = Category.get(key)
	items = Item.all().ancestor(category)
	return render_template('comment.html',items=items,key=key,title=category.title,owner=category.owner.email())	

@app.route('/postcomment',methods=['POST'])
@login_required
def post_comment():
	key = request.form.get('key')
	item_name = request.form.get('item')
	user_comment = request.form.get('comment')
	category = Category.get(key)
	item = Item.all().ancestor(category).filter('title =',item_name).get()
	comment = UserComment.all().ancestor(item.key()).filter('commenter =',users.get_current_user()).get()
	if comment:
		return Response(status=400)
	else:
		comment = UserComment(parent=item.key(),comment=user_comment,commenter=users.get_current_user())
		comment.put()
		return Response(status=200)

@app.route('/edit/images/<key>')
def edit_image(key):
	category = Category.get(key)
	upload_url = blobstore.create_upload_url('/saveimage/'+key)
	items = Item.all().ancestor(category)
	return render_template('edit_images.html',items=items,key=key,title=category.title,owner=category.owner.email(), upload_url=upload_url)

@app.route('/saveimage/<key>',methods=['POST'])
def saveimage(key):
	category = Category.get(key)
	items = Item.all().ancestor(category)
	item = Item.all().ancestor(category).filter('title =',request.form.get('items')).get()
	if request.method == 'POST':
		image_file = request.files['image']
		headers = image_file.headers['Content-Type']
		blob_key = parse_options_header(headers)[1]['blob-key']
		item.blob_key = blob_key
		item.image_url = images.get_serving_url(blob_key)
		item.put()
	return redirect('edit/images/'+key)

@app.route('/battles/search/<keywordslist>')
def search(keywordslist):
	keywords = keywordslist.split(" ")
	categories = {}
	keys = {}
	cat_count = {}
	for key in keywords:
		for category in Category.all():
			if category.title.lower().__contains__(key.lower()):
				categories[category.title] = Item.all().ancestor(category)
				keys[category.title] = category.key()
	for key in keywords:
		for item in Item.all():
			if item.title.lower().__contains__(key.lower()):
				categories[item.parent().title] = Item.all().ancestor(item.parent())
				keys[item.parent().title] = item.parent().key()
	return render_template('search_results.html',categories=categories, keys=keys, keywords=keywordslist)

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
	return [items[one], items[two]]