from google.appengine.ext import db

class Category(db.Model):
	title = db.StringProperty(required = True)
	when = db.DateTimeProperty(auto_now_add = True)
	owner = db.UserProperty(required = True)

class Item(db.Model):
	title = db.StringProperty(required = True)

class UserVote(db.Model):
	wins = db.IntegerProperty(default=0)
	losses = db.IntegerProperty(default=0)
	voter = db.UserProperty(required = True)

