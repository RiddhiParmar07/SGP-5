from flask import request
from IVANDKEY import *
from flask import Flask,render_template,redirect,url_for,session,flash,send_file
from datetime import date
import MySQLdb
import os
from base64 import b64encode, b64decode, urlsafe_b64decode, urlsafe_b64encode
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
from io import BytesIO

app=Flask(__name__)

app.secret_key=os.urandom(24)

conn = MySQLdb.connect(host="localhost",user="root",password="",db="myapp")
cursor=conn.cursor()
APP_ROOT=os.path.dirname(os.path.abspath(__file__))


@app.route('/adminlogin')
def adminlogin():
    return render_template('adminlogin.html')

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/home')
def home():
    if 'id' in session:
        id = session ['id']
        cursor.execute("SELECT username,email FROM user WHERE id=%s",(id,))
        user=cursor.fetchall()
        email=user[0][1]
        cursor.execute('SELECT fid,file_name,upload_date FROM file where uemail=%s',(email,))
        filedata=cursor.fetchall()
        cursor.execute('SELECT did,file_name,datee FROM download where uemail=%s', (email,))
        download_data = cursor.fetchall()
        cursor.execute('SELECT fid FROM request WHERE uemail=%s AND permission = %s',(email,"YES",))
        fid=cursor.fetchall()
        if fid:
            query=("SELECT fid,file_name,md5 from file where fid IN ({})".format(','.join(['%s'] * len(fid))))
            cursor.execute(query,fid)
            key_details=cursor.fetchall()
            return render_template("home.html",name=user,files=filedata,accepted=key_details,download=download_data)
        else:
            return render_template("home.html",name=user,files=filedata,download=download_data)
    else:
        return redirect('/')

@app.route('/adminhome')
def adminhome():
    if 'aid' in session:

        cursor.execute('SELECT fid,file_name,uemail,upload_date FROM file')
        filedata = cursor.fetchall()
        cursor.execute('SELECT * FROM user')
        all_data=cursor.fetchall()
        cursor.execute('SELECT * FROM request')
        req_data = cursor.fetchall()
        cursor.execute('SELECT * FROM download')
        down_data = cursor.fetchall()
        return render_template("adminhome.html",users=all_data,files=filedata,reqs=req_data,downs=down_data)
    else:
        return redirect('/admin')

@app.route('/login_validation',methods={"POST"})
def login_validation():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

    cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
    users = cursor.fetchone()
    if users and check_password_hash(users[3], password):
        if users[5]=="authorised":
            if len(users) > 0:
                session['id'] = users[0]
                session['loggedin'] = True
                return redirect('/home')
        else:
            return redirect('/')
    else:
         return redirect('/')


@app.route('/adminlogin_validation',methods={"POST"})
def adminlogin_validation():
    if request.method == "POST":
         aemail=request.form.get('aemail')
         apassword = request.form.get('apassword')

    cursor.execute('SELECT * FROM admin WHERE aemail = %s', (aemail,))
    admin=cursor.fetchone()

    if admin and check_password_hash(admin[2],apassword):
         if len(admin)>0:
            session['aid']=admin[0]
            session['loggedin'] = True

            return redirect('/adminhome')
    else:
        return redirect('/adminlogin')

@app.route('/add_user',methods={"POST"})
def add_user():
    username=request.form.get('uname')
    email = request.form.get('uemail')
    password = generate_password_hash(request.form.get('upassword'))
    now=date.today()


    cursor.execute('INSERT INTO user VALUES (NULL, %s, %s, %s, %s,%s)', (username, email,password,now,'unauthorised'))
    conn.commit()
    return "user added successfully"

@app.route('/add_admin',methods={"POST"})
def add_admin():

    aemail = request.form.get('uemail')
    apassword = generate_password_hash(request.form.get('upassword'))


    cursor.execute('INSERT INTO admin VALUES (NULL, %s, %s)', (aemail, apassword,))
    conn.commit()
    return "admin added successfully"


@app.route('/action/<uid>/',methods={"POST","GET"})
def action(uid):

    cursor.execute('SELECT  status FROM user where  id=%s',(uid,))
    status=cursor.fetchone()
    print(status)
    if(status[0]=="unauthorised"):
        cursor.execute("UPDATE user SET status = 'authorised' WHERE id = %s",(uid,))
    if (status[0] == "authorised"):
        cursor.execute("UPDATE user SET status = 'unauthorised' WHERE id = %s",(uid,))
    conn.commit()
    return redirect(url_for('adminhome'))

@app.route('/request_acc/<fid>/',methods={"POST","GET"})
def request_acc(fid):

    cursor.execute('SELECT  fid,file_name,uemail FROM file where  fid=%s',(fid,))
    req_file=cursor.fetchone()
    print(req_file)
    cursor.execute("INSERT INTO request VALUES (NULL,%s,%s,%s,%s,%s)",(req_file[0],req_file[1],req_file[2],"NO","NO"))
    conn.commit()
    flash("REQUEST WAS SENT SUCCESSFULLY")
    return redirect(url_for('home'))

@app.route('/delete_file/<fid>/',methods={"POST","GET"})
def delete_file(fid):

    cursor.execute("DELETE FROM file WHERE fid=%s",(fid,))
    cursor.execute("DELETE FROM request WHERE fid=%s",(fid,))
    cursor.execute("DELETE FROM download WHERE fid=%s", (fid,))
    conn.commit()
    flash("FILE DELETED SUCCESSFULLY")

    return redirect(url_for('home'))


@app.route('/areq/<rid>/',methods={"POST","GET"})
def areq(rid):
    print(rid)
    cursor.execute('SELECT  permission,fid FROM request where  rid=%s',(rid,))
    status=cursor.fetchone()
    print(status)
    if(status[0]=="NO"):
        cursor.execute("UPDATE request SET permission = 'YES' WHERE rid = %s",(rid,))
        cursor.execute("SELECT uemail FROM file WHERE fid=%s",(status[1],))
        sender=cursor.fetchone()
        print(sender)
        flash("REQUEST WAS ACCEPTED")
        conn.commit()
    return redirect(url_for('adminhome'))


@app.route('/ulogout')
def ulogout():
    session.pop('loggedin',None)
    session.pop('id',None)
    return redirect(url_for('login'))


@app.route('/alogout')
def alogout():
    session.pop('loggedin',None)
    session.pop('aid',None)
    return redirect(url_for('adminlogin'))

@app.route('/upload_file', methods={'POST'})
def upload_file():

    filename=request.form.get('filename')
    if 'id' in session:
        id=session['id']
        cursor.execute('SELECT email FROM user Where id =%s',(id,))
        email=cursor.fetchone()
        print(email)
        now = date.today()
        ff=request.files['file']
        data=ff.read()
        img_key = hashlib.md5(data).hexdigest()
        cursor.execute("select file_name from file where md5=%s",(img_key,))
        check=cursor.fetchone()
        if check is None:
            cursor.execute("INSERT INTO  file (fid,uemail,file_name,fdata,md5,upload_date) VALUES(NULL ,%s,%s,%s,%s,%s)",(email,filename,data,img_key,now,))
            conn.commit()
            flash("FILE UPLOADED SUCCESSFULLY")
            return redirect('/home')

        else:
            flash("Duplicate Entry Detected")
            return redirect('/home')
    else:
        return 'ERROR'


@app.route('/get_download_data/<fid>', methods={"POST","GET"})
def get_download_data(fid):
    if fid is not None:
        cursor.execute("SELECT file_name,fdata FROM file WHERE fid=%s",(fid,))
        download=cursor.fetchone()
        flash("FILE DOWNLOADED")
        return send_file(BytesIO(download[1]),attachment_filename=download[0],as_attachment=True)
    else:
        flash("FILE NOT DOWNLOADED")

    return redirect('/home')


if __name__=="__main__":
    app.run(debug=True)
