from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, jsonify, Response, url_for, session, abort
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from flask_mysqldb import MySQL
from flask import send_from_directory
from datetime import datetime
# from dotenv import load_dotenv
import my_YoloV8
import cv2
import json
import random
import imghdr
import requests

# from random import random
# Khởi tạo Flask Server Backend
# load_dotenv()
app = Flask(__name__)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'mp4','webp'])
# Apply Flask CORS
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOAD_FOLDER'] = "static"

# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# app.secret_key = 'dhbsfbsdbc8223bd'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345678'
app.config['MYSQL_DB'] = 'yolov8shrimp'
mysql = MySQL(app)

model = my_YoloV8.YOLOv8_ObjectCounter(model_file="best1686.pt")


app.secret_key = os.environ.get("FLASK_SECRET")

oauth = OAuth(app)
# list of google scopes - https://developers.google.com/identity/protocols/oauth2/scopes
oauth.register(
    "myApp",
    client_id=os.environ.get("OAUTH2_CLIENT_ID"),
    client_secret=os.environ.get("OAUTH2_CLIENT_SECRET"),
    client_kwargs={"scope":os.environ.get("SCOPE")},
    server_metadata_url=f'{os.environ.get("OAUTH2_META_URL")}',
)


@app.route("/")
def home():   
    if (session):
        CS = mysql.connection.cursor()
        CS.execute(f"""SELECT * FROM user where email='{session["user"]["email"]}'""")
        Executed_DATA = CS.fetchall()
        print("Executed_DATA",session["provider"])
        if (Executed_DATA):
            return render_template("home.html", session=Executed_DATA)
        elif(session["provider"] == "Google"):
            CS.execute(
                f"""INSERT INTO user VALUES ('{session["user"]["email"]}','{session["user"]["name"]}','{session["user"]["picture"]}','{session["user"]["picture"]}+{session["user"]["email"]}')""")
            # CS.execute('''INSERT INTO TABLE_NAME VALUES (2, 'Arthor')''')
            mysql.connection.commit()
            CS.execute(f"""SELECT * FROM user where email='{session["user"]["email"]}'""")
            Executed_DATA = CS.fetchall()
            return render_template("home.html", session=Executed_DATA
                               )
    else:
        print("no")
        return render_template("home.html", session="")

@app.route("/signin-google")
def googleCallback():
    # fetch access token and id token using authorization code
    token = oauth.myApp.authorize_access_token()
    personDataUrl = "https://people.googleapis.com/v1/people/me?personFields=genders,birthdays"
    personData = requests.get(personDataUrl, headers={
        "Authorization": f"Bearer {token['access_token']}"
    }).json()
    token["personData"] = personData
   
    # set complete user information in the session
    session["user"] = token["userinfo"]
    session['provider'] = "Google"
    
    # print(session["user"])
    print("ok",session)
    return redirect(url_for("home"))

@app.route("/google-login")
def googleLogin():
    print(session)
    if "user" in session:
        abort(404)
    return oauth.myApp.authorize_redirect(redirect_uri=url_for("googleCallback", _external=True))

@app.route("/login", methods=["GET", "POST"])
def login():
    if session:
        return redirect(url_for('home'))
    if request.method == "POST":
        print("ok")
        email = request.form['email']
        pwd = request.form['password']
        print(email+pwd)
        cur = mysql.connection.cursor()
        cur.execute(f"select * from user where email = '{email}'")
        users = cur.fetchone()
        cur.close()
        print(users)
        if users and pwd == users[3]:
            session['user'] = {"email":users[0]}
            session["provider"] = "sql"
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error = 'Invalid email or password')
    return render_template('login.html')    


@app.route("/register", methods=["GET", "POST"])
def register():
    if session:
        return redirect(url_for('home'))

    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(f"SELECT * FROM user WHERE email = '{email}'")
        existing_user = cur.fetchone()
        cur.close()

        if existing_user:
            return render_template('register.html')
        else:
            cur = mysql.connection.cursor()
            user_name = email.split('@')[0]
            print(user_name)
            cur.execute(f"INSERT INTO user (email,username, avatar, password) VALUES ('{email}','{user_name}','{'https://ps.w.org/user-avatar-reloaded/assets/icon-256x256.png?rev=2540745'}','{password}')")
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login'))
    else:
        return render_template('register.html')
    
@app.route("/check_email", methods=["POST"])
def check_email():
    email = request.json["email"]

    cur = mysql.connection.cursor()
    cur.execute(f"SELECT * FROM user WHERE email = '{email}'")
    existing_user = cur.fetchone()
    cur.close()

    if existing_user:
        return jsonify({"exists": True})
    else:
        return jsonify({"exists": False})
@app.route("/check_password", methods=["POST"])
def check_pass():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Thực hiện truy vấn để kiểm tra mật khẩu
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT password FROM user WHERE email = '{email}'")
    user_data = cur.fetchone()
    cur.close()

    # So sánh mật khẩu trong cơ sở dữ liệu với mật khẩu được cung cấp
    if user_data and user_data[0] == password:
        return jsonify({"valid": True})
    else:
        return jsonify({"valid": False})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/settings")
def settings():
    if session:

        CS = mysql.connection.cursor()
        CS.execute(f"""SELECT * FROM user where email='{session["user"]["email"]}'""")
        Executed_DATA = CS.fetchone()

        return render_template('settings.html', session = Executed_DATA)
    else:
        return redirect(url_for('login'))

@app.route("/classification")
def classification():
    if session:
        CS = mysql.connection.cursor()
        CS.execute(f"""SELECT * FROM user where email='{session["user"]["email"]}'""")
        Executed_DATA = CS.fetchone()
        print(Executed_DATA)
        return render_template('classification.html', session = Executed_DATA)
    else:
        return redirect(url_for('login'))
    
@app.route("/history")
def history():
    if session:
        CS = mysql.connection.cursor()
        email = session['user']['email']
        CS.execute(f"""SELECT * FROM history where email = '{email}'""")
        Executed_DATA = CS.fetchall()
        CS.execute(f"""SELECT * FROM user where email = '{email}'""")
        user = CS.fetchone()

        print(Executed_DATA)
        
        # trả về tổng shrimp trong cả toàn bộ lịch sử nhận dạng
        total_shrimp = 0
        total_medium_shrimp = 0
        total_big_shrimp = 0
        total_small_shrimp = 0
        for record in Executed_DATA:
            # tong tom
            shrimp_data = record[3]  # Assume shrimp data is always at index 2
            total_shrimp += shrimp_data
            
            
            shrimp_datakind = record[2]  # Giả sử dữ liệu của tôm luôn nằm ở chỉ mục 2
            shrimp_data_dict = json.loads(shrimp_datakind)  # Chuyển đổi chuỗi JSON thành từ điển
            shrimp_total_medium = shrimp_data_dict.get("MediumShrimp", 0) 
            shrimp_total_big = shrimp_data_dict.get("BigShrimp", 0) 
            shrimp_total_small = shrimp_data_dict.get("SmallShrimp", 0)
            
            total_medium_shrimp += shrimp_total_medium 
            total_big_shrimp += shrimp_total_big
            total_small_shrimp += shrimp_total_small

        print("Tổng số lượng MediumShrimp:", total_medium_shrimp)
        print("Tổng số lượng bigShrimp:", total_big_shrimp)
        print("Tổng số lượng SmallShrimp:", total_small_shrimp)
        
        return render_template('history.html',session = user, sessions = Executed_DATA, total = total_shrimp,big = total_big_shrimp,medium = total_medium_shrimp,small = total_small_shrimp)
 
    else:
        return redirect(url_for('login'))
@app.route('/delete_data', methods=['POST'])
def delete_data():
    id = request.form['id']
    CS = mysql.connection.cursor()
    try:
        CS.execute(f"""DELETE FROM history WHERE id = '{id}'""")
        mysql.connection.commit()
        CS.close()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        CS.close()
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/delete_selected_records', methods=['POST'])
def delete_selected_records():
    selected_records = request.json
    if not selected_records:
        return jsonify({'success': False, 'error': 'No records selected'})
    CS = mysql.connection.cursor()

    try:
        for record_id in selected_records:
            CS.execute(f"""DELETE FROM history WHERE id = '{record_id}'""")
        mysql.connection.commit()
        CS.close()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        CS.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/video_feed/<path:subpath>")
def video_feed(subpath):
    if( subpath=="camera"):
        print(subpath)
        return Response(generate(colors=color()),
                    mimetype="multipart/x-mixed-replace; boundary=frame")
    else:
        return Response(generate(videoPath=subpath,CAP_DSHOWN=None,colors=color()),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route('/classify', methods=['POST'])
def upload_file():
    print(request.files.getlist('uploadFile[]'))
    if 'uploadFile[]' not in request.files:
        return redirect(request.url)
    files = request.files.getlist('uploadFile[]')
    if files:
        file_names = []
        results_pre = []
        results_pre_temp = []
        results_dict = []
        is_video = False
        for file in files:
            if imghdr.what(file) and file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path_save = os.path.join(app.config['UPLOAD_FOLDER'] + "/image/img_process/", filename)
                file.save(path_save)
                frame = cv2.imread(path_save)
                results = model.predict_img(frame)
                result_img = model.custom_display(colors=color())
                msg = 'File predict successfully'
                # print(file_names)
                if len(results) > 0:
                    dictObject, save_name = model.count_object(results, app.config['UPLOAD_FOLDER'], result_img)
                    results_pre_temp.append(dictObject)

                    file_names.append(save_name)
            else:
                is_video = True
                path_save = os.path.join(app.config['UPLOAD_FOLDER'] + "/image/img_process/", file.filename)
                file.save(path_save)
                msg = 'File predict successfully'
                file_names.append(path_save)
        results_dict.extend(results_pre_temp)
        if results_pre_temp.__len__() > 0:
            if results_pre.__len__() > 0:
                results_pre.clear()
            results_pre.extend(results_pre_temp)
            results_pre_temp.clear()
        if(is_video):
            # generate(, CAP_DSHOWN=None, colors=color())
            return jsonify(
                {"video": True,
                 'success': True,
                 "file":file_names[0]})
        else:


            cur = mysql.connection.cursor()
            for i in range(len(results_dict)):
                filtered_dict = {k: v for k, v in results_dict[i].items() if k != 'SumShrimp'}
                # print(file_names)
                key = json.dumps(filtered_dict)
                current_time = datetime.now()
                sumShrimp = results_dict[i]["SumShrimp"]
                email = session['user']['email']
                cur.execute(f"""INSERT INTO history (shrimp_image,shrimp_kind, shrimp_total, c_time, email) 
                            VALUES ('{file_names[i]}','{key}','{sumShrimp}','{current_time}','{email}')""")
                mysql.connection.commit()
            cur.close()
            return jsonify(
                {'htmlresponse': render_template('response.html', msg=msg, filenames=file_names),
                 "Filename": file_names,
                 "Info": results_pre,
                 "video": False,
                 'success': True, })
    else:
        return {'htmlresponse': 'Error!',
                'success': False, }

@app.route('/download', methods=['POST'])
def download():
    try:
        # Ensure the 'url' key is present in the JSON data
        data = request.get_json()
        url = data['url']
        r = requests.get(url)
        if not url:
            raise ValueError("URL is missing in the request data.")

        print(f"Downloading image from: {url}")

        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        filename = get_filename_from_url(url)
        image_path = os.path.join(upload_folder, filename)

        # Save the image locally
        with open(image_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        # Check the file type using imghdr
        file_type = imghdr.what(image_path)

        if file_type:
            # # Read the image using OpenCV
            frame = cv2.imread(image_path)
            # # Perform image prediction using the 'model'
            results = model.predict_img(frame)
            print(f"Image prediction results: {results}")

            # Display the results with custom colors
            result_img = model.custom_display(colors=color())
    
            # If there are positive results, count objects and save the image
            if len(results) > 0:
                dictObject, save_name = model.count_object(results, upload_folder, result_img)
                filtered_dict = {k: v for k, v in dictObject.items() if k != 'SumShrimp'}
                key = json.dumps(filtered_dict)
                current_time = datetime.now()
                cur = mysql.connection.cursor()
                sumShrimp = dictObject['SumShrimp']
                email = session['user']['email']

                cur.execute(f"""INSERT INTO history (shrimp_image,shrimp_kind, shrimp_total, c_time, email) 
                                        VALUES ('{save_name}','{key}','{sumShrimp}','{current_time}','{email}')""")
                mysql.connection.commit()
                cur.close()
                msg = 'File predict successfully'
                print(f"Saved result image to: {save_name}")
                return jsonify({'success': True,  "Info": dictObject,
                                'htmlresponse': render_template('response.html', is_video=False, msg=msg, filenames=[save_name])})
        else:
            # Check the image type using imghdr
            totalCount, dictObject, save_file = model.predict_video(video_path=image_path,
                                                                    save_dir=app.config[
                                                                                 'UPLOAD_FOLDER'] + "/video/",
                                                                    save_format="mp4",
                                                                    display='custom',
                                                                    colors=color())
            video = model.convert_video(save_file, app.config['UPLOAD_FOLDER'] + "/videoOut/")
            msg = 'File predict successfully'
            return jsonify({'success': True, "Info": dictObject,
                            'htmlresponse': render_template('response.html', is_video=True, msg=msg,
                                                            filenames=[video])})
        return jsonify({'success': True, 'image_path': "No positive results", "Info": {}})
    
    except requests.RequestException as req_err:
        return jsonify({'success': False, 'error': f"Request error: {str(req_err)}"})
    
    except Exception as e:
        return jsonify({'success': False, 'error': f"An error occurred: {str(e)}"})



@app.route("/change-password", methods=["POST"])
def change_password():
    if "user" in session:
        current_pwd = request.form['current_password']
        new_pwd = request.form['new_password']

        cur = mysql.connection.cursor()

        cur.execute(f"SELECT password FROM user WHERE email = '{session['user']['email']}'")
        user_data = cur.fetchone()
        print(user_data)
        if user_data and current_pwd == user_data[0]:
            cur.execute(f"UPDATE user SET password = '{new_pwd}' WHERE email = '{session['user']['email']}'")
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('home'))
        else:
            return render_template('settings.html', error='Current password is incorrect')
    else:
        return redirect(url_for('login'))
    
@app.route("/change-username", methods=["POST"])
def change_username():
    if "user" in session:
        current_username = request.form['current_username']
        current_avatar = request.files['current_avatar']
        print(current_username)
        print(current_avatar)
        filename = secure_filename(current_avatar.filename)
        if(filename):
            path_save = os.path.join(app.config['UPLOAD_FOLDER'] + "/upload/users/", filename)
            current_avatar.save(path_save)
        else:
            path_save = request.form['temp']
        email = session['user']['email']
        print(path_save)
        cur = mysql.connection.cursor()
        cur.execute(f"SELECT username FROM user WHERE email = '{email}'")
        user_data = cur.fetchone()

        if user_data:
            cur.execute(f"UPDATE user SET username = '{current_username}', avatar='{path_save}' WHERE email = '{email}'")
            mysql.connection.commit()
            # cur.execute(f"SELECT username FROM user WHERE email = '{email}'")
            # Executed_DATA= cur.fetchone()
            # print(Executed_DATA)
            cur.close()
            return redirect(url_for('settings'))
        else:
            return render_template('settings.html', error='Current password is incorrect')
    else:
        return redirect(url_for('login'))

def generate(videoPath=0,CAP_DSHOWN=cv2.CAP_DSHOW,colors=None):
    return model.predict_videoStream(videoPath,colors, CAP_DSHOWN)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_filename_from_url(url):
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    return filename


def color():
    colors = []
    for _ in range(80):
        rand_tuple = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        colors.append(rand_tuple)
    return colors


def random_color():
    return tuple(random.randint(0, 255) for _ in range(3))
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=os.environ.get(
        "FLASK_PORT"), debug=True)

