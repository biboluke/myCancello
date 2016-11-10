from flask import Flask, render_template, request, redirect, url_for , session ,make_response, jsonify, flash
from functools import wraps
import mysql.connector
import hashlib
import random
import pyperclip

#import RPi.GPIO as GPIO ## Import GPIO library #da implementare su raspberry
#GPIO.setmode(GPIO.BOARD) ## Use board pin numbering #da implementare su raspberry
#GPIO.setup(7, GPIO.OUT) ## Setup GPIO Pin 7 to OUT #da implementare su raspberry
#-----------------------------------------------------------------------------------------
app = Flask(__name__)
#-----------------------------------------------------------------------------------------
app.secret_key = "cippalippa"

#-----------------------------------------------------------------------------------------
connection=mysql.connector.connect(user='root',password='defcon1',database='ServerCancello')
cursor=connection.cursor()
permessi = False
#-----------------------------------------------------------------------------------------
def get_random_string(length=8,allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789'):
    return ''.join(random.choice(allowed_chars) for i in range(length))
#-----------------------------------------------------------------------------------------
def login_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			return redirect(url_for('login'))
	return wrap	
#-----------------------------------------------------------------------------------------		
@app.route("/", methods=['GET','POST'])
@login_required
def home():
	return render_template('home.html',permessi=permessi)
#-----------------------------------------------------------------------------------------
@app.route("/login", methods=['GET','POST'])
def login():
	error=None
	if request.method=='POST':
		if request.form['username'] and request.form['password']:
			user= request.form['username'].lower()
			password=hashlib.sha1(request.form['password'])
			password=password.hexdigest()
			cursor.execute('SELECT * FROM  users WHERE user=%(user)s AND password=%(password)s',{'user':user,'password':password})
			if cursor.fetchone():
				cursor.execute('SELECT * FROM users WHERE user=%(user)s AND (expiredate>=NOW() or expiredate is NULL)',{'user':user})
				if cursor.fetchone():	
					session['logged_in'] = True
					session['user']=user
					cursor.execute('SELECT permessi FROM  users WHERE user=%(user)s',{'user':user})
					permessi=cursor.fetchone()
					if permessi[0]=='admin':
						session['permessi']=True
					return redirect(url_for('home'))
				else:
					error="Your account has been deleted!"
			else:
				error="Wrong username or password!"
	return render_template('login.html',error=error)
#-----------------------------------------------------------------------------------------
@app.route("/logout", methods=['GET','POST'])
@login_required
def logout():
	session.pop('logged_in',None)
	session.pop('permessi',None)
	return redirect(url_for('login'))
#-----------------------------------------------------------------------------------------
@app.route("/open", methods=['GET','POST'])
@login_required
def open():
#	GPIO.output(7,True) #da implementare su raspberry
	return redirect(url_for('home'))
#-----------------------------------------------------------------------------------------
@app.route("/settings", methods=['GET','POST'])
@login_required
def settings():
	if 'permessi' in session:
		permessi=True
	else:
		permessi=False
	if 'randomUsername' in session:
		username=session['randomUsername']
		password=session['randomPassword']
		session.pop('randomUsername',None)
		session.pop('randomPassword',None)
	else:
		username=""
		password=""
	if 'tab' in session:
		if session['tab']=='add':
			update=''
			remove=''
			add='is-active'
		if session['tab']=='remove':
			update=''
			remove='is-active'
			add=''
		if session['tab']=='update':
			update='is-active'
			remove=''
			add=''
	else:
		add='is-active'
		remove=''
		update=''
	user = session['user']
	cursor.execute('SELECT user,permessi,expiredate FROM users WHERE user=%(user)s',{'user':user})	
	info_user= list(cursor.fetchone())
	#info_user =list(info_user)
	info_user[0]='User: '+info_user[0].title()
	if info_user[1]=='admin':
		info_user[1]='Type: Super User'
	else:
		info_user[1]='Type: Regular User'
	if info_user[2]==None:
		info_user[2]='Expire: Infinity'
	else:
		info_user[2]='Expire: '+info_user[2]
	return render_template('sett.html',permessi=permessi,username=username,password=password,remove=remove,add=add,update=update,info_user=info_user)
#-----------------------------------------------------------------------------------------
@app.route("/regular", methods=['GET','POST'])
@login_required
def regular():
	if request.method=='POST':
		user=session['user']
		if request.form['newpassword']:
			newpassword=request.form['newpassword']
			newpasswordCheck=request.form['newpasswordCheck']
			if newpassword==newpasswordCheck:
				
				newpassword=hashlib.sha1(request.form['newpassword'])
				newpassword=newpassword.hexdigest()
				
				cursor.execute('UPDATE users SET password=%(newpassword)s WHERE user=%(user)s',{'newpassword':newpassword,'user':user})
				connection.commit()
				flash('New password set.','new_password')
			else:
				flash('Passwords doesn\'t match','new_password')
		if request.form['newusername']:
			newuser=request.form['newusername'].lower()
			cursor.execute('SELECT * FROM users WHERE user=%(newuser)s',{'newuser':newuser})
			if cursor.fetchone():
				flash('Username already exist!','new_username')
			else:
				cursor.execute('UPDATE users SET user=%(newuser)s WHERE user=%(user)s',{'newuser':newuser,'user':user})
				connection.commit()
				session['user']=newuser
				flash('New username set.','new_username')
	return redirect(url_for('settings'))
#-----------------------------------------------------------------------------------------
@app.route("/generate",methods=['GET','POST'])
@login_required
def generate():
	if request.method=='POST':
		ok=False
		while ok==False:
			user=get_random_string()
			cursor.execute('SELECT * FROM users WHERE user=%(user)s',{'user':user})
			if not cursor.fetchone():
				ok=True
				request.form.username=user
				password=get_random_string()
				session['randomUsername']=user
				session['randomPassword']=password
				account='User: '+user+' Password: '+password
				pyperclip.copy(account)
				copied = pyperclip.paste()
				password=hashlib.sha1(password)
				password=password.hexdigest()
		session['tab']='add'
	return redirect(url_for('settings'))
#-----------------------------------------------------------------------------------------
@app.route("/check", methods=['GET','POST'])
@login_required
def check():
	if request.method=='POST':
		try:
			if request.form['a_username']:
				user=request.form['a_username']
				cursor.execute('SELECT user FROM users WHERE user=%(user)s',{'user':user})
				session['tab']='add'
		except:
			try:
				if request.form['r_username']:
					user=request.form['r_username']
					cursor.execute('SELECT user FROM users WHERE user=%(user)s',{'user':user})
					session['tab']='remove'
			except:
				if request.form['u_username']:
					user=request.form['u_username']
					cursor.execute('SELECT user FROM users WHERE user=%(user)s',{'user':user})
					session['tab']='update'
		if cursor.fetchone():
			flash("Username already exist",'new_username')
		else:
			flash("Username available",'new_username')
	return redirect(url_for('settings'))
#-----------------------------------------------------------------------------------------
@app.route("/provamaterial", methods=['GET','POST'])
def provamaterial():
	if request.method=='POST':
		if request.form['homebtn']:
			return redirect(url_for('home'))
	return render_template('provamaterial.html')
#-----------------------------------------------------------------------------------------
@app.route("/add", methods=['GET','POST'])
def add():
	if request.method=='POST':
		if request.form['a_username'] and request.form['a_password']:
			user=request.form['a_username'].lower()
			password=hashlib.sha1(request.form['a_password'])
			password=password.hexdigest()
			passwordCheck=hashlib.sha1(request.form['a_passwordCheck'])
			passwordCheck=passwordCheck.hexdigest()
			if password==passwordCheck:
				if request.form.get('a_permessi'):
					permessi='admin'
				else:
					permessi='user'
				cursor.execute('SELECT * FROM users WHERE user=%(user)s',{'user':user})
				if cursor.fetchone():
					flash('Username already exist!','new_username')
				else:
					cursor.execute('INSERT INTO users(user,password,permessi) VALUES(%s,%s,%s)',(user,password,permessi))
					connection.commit()
					if request.form['a_expiredate'] or request.form.get('a_permessi'):
						hours=request.form['a_expiredate']
						if request.form.get('a_noexpire'):
							cursor.execute('UPDATE users SET expiredate=NULL WHERE user=%(user)s',{'user':user})
							connection.commit()
						else:
							cursor.execute('UPDATE users SET expiredate=DATE_ADD(NOW(),interval %(hours)s hour) WHERE user=%(user)s',{'hours':hours,'user':user})
							connection.commit()
			else:
				flash('Password doesn\'t match','new_password')
		else:
			if not request.form['a_username']:
				flash('Username cannot be blank','new_username')
			if not request.form['a_password']:
				flash('Password cannot be blank','new_password')	 
		session['tab']='add'
	return redirect(url_for('settings'))
#-----------------------------------------------------------------------------------------
@app.route("/remove", methods=['GET','POST'])
def remove():
	if request.method=='POST':
		if request.form['r_username']:
			user = request.form['r_username'].lower()
			cursor.execute('SELECT * FROM users WHERE user=%(user)s',{'user':user})
			if cursor.fetchone():
				cursor.execute('DELETE FROM users WHERE user=%(user)s',{'user':user})
				connection.commit()
			else:
				flash('Account do not exist','new_username')
		else:
			flash('You must fill the field!')
		session['tab']='remove'
	return redirect(url_for('settings'))
#-----------------------------------------------------------------------------------------
@app.route("/update", methods=['GET','POST'])
def update():
	if request.method=='POST':
		if request.form['u_username']:
			user = request.form['u_username'].lower()
			if request.form.get('u_permessi'):
				permessi='admin'
			else:
				permessi='user'
			cursor.execute('SELECT * FROM users WHERE user=%(user)s',{'user':user})
			if cursor.fetchone():
				cursor.execute('UPDATE users SET permessi=%(permessi)s WHERE user=%(user)s',{'permessi':permessi,'user':user})
				connection.commit()
			else:
				flash('Account do not exist','new_username')
			if request.form['u_expiredate'] or request.form.get('u_noexpire'):
				hours=request.form['u_expiredate']
				if request.form.get('u_noexpire'):
					cursor.execute('UPDATE users SET expiredate=NULL WHERE user=%(user)s',{'user':user})
					connection.commit()
				else:
					cursor.execute('UPDATE users SET expiredate=date_add(now(),interval %(hours)s hour) WHERE user=%(user)s',{'hours':hours,'user':user})
					connection.commit()
					flash('Expire date updated','expiredate')
					flash(hours,'expiredate')
			if request.form['u_password']:
				if request.form['u_passwordCheck']:
					password=hashlib.sha1(request.form['u_password'])
					password=password.hexdigest()
					passwordCheck=hashlib.sha1(request.form['u_passwordCheck'])
					passwordCheck=passwordCheck.hexdigest()
					if password==passwordCheck:
						cursor.execute('UPDATE users SET password=%(password)s WHERE user=%(user)s',{'user':user,'password':password})
						connection.commit()
		session['tab']='update'
	return redirect(url_for('settings'))
#-----------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------
if __name__ == '__main__':
	#app.run(debug=True)
	app.run(debug=True, host='0.0.0.0', port=80)
