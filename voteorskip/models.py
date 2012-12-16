from google.appengine.ext import db

class Category(db.Model):
	title = db.StringProperty(required = True)
	when = db.DateTimeProperty(auto_now_add = True)
	owner = db.UserProperty(required = True)
	expiration = db.DateTimeProperty()

class Item(db.Model):
	title = db.StringProperty(required = True)
	wins = db.IntegerProperty(default = 0)
	losses = db.IntegerProperty(default = 0)
	blob_key = db.StringProperty(default="None")
	image_url = db.StringProperty(default="None")

class UserVote(db.Model):
	wins = db.IntegerProperty(default=0)
	losses = db.IntegerProperty(default=0)
	voter = db.UserProperty(required = True)

class UserComment(db.Model):
	comment = db.StringProperty()
	commenter = db.UserProperty(required = True)

