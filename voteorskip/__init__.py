from flask import Flask
import settings
app = Flask('voteorskip')
app.config.from_object('voteorskip.settings')

import views