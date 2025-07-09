import jwt # jwt 라이브러리 임포트
import datetime # 유효기간 설정을 위한 라이브러리
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify, redirect, url_for # request, jsonify 추가
import random # 랜덤 숫자 생성을 위한 라이브러리
import smtplib
from email.mime.text import MIMEText
import hashlib # 비밀번호 암호화를 위한 라이브러리

# JWT를 위한 비밀 키
SECRET_KEY = 'JUNGLE'

# MongoDB 연결 설정
client = MongoClient('mongodb://test:test@15.164.170.54', 27017)
db = client.dbjungle # 'dbjungle' 이라는 이름의 DB를 사용

app = Flask(__name__)


## 라우팅
# 기본 URL 접속 시 Login 페이지
@app.route('/')
def home():
   return render_template('LoginPage.html')

# 회원가입 페이지
@app.route('/signup')
def signup_page():
    return render_template('SignupPage.html')

# 아이디/비밀번호 찾기 페이지
@app.route('/find-account')
def findAccountPage():
    return render_template('FindAccountPopup.html')



## API
# 로그인 API
@app.route('/api/SignIn', methods=['POST'])
def SignIn():
    # 1. 클라이언트로부터 데이터 받아오기
    id_receive = request.form.get('id_give')
    password_receive = request.form.get('password_give')

    # 2. 비밀번호 암호화
    import hashlib
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    # 3. DB에서 아이디, 암호화된 비밀번호가 일치하는 사용자가 있는지 확인
    result = db.users.find_one({'id': id_receive, 'password': password_hash})

    # 4. 사용자가 존재하면, JWT 생성
    if result is not None:
        # JWT에 담을 정보 (payload)
        # 'id'는 사용자를 식별할 수 있는 정보, 'exp'는 토큰의 만료 시간
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # 1시간 동안 유효?
        }
        # JWT 생성
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')   # payload와 SECRET_KEY를 합쳐서 암호화된 토큰(문자열)을 인코딩?

        # 5. 생성한 토큰을 클라이언트에게 보내주기
        return jsonify({'result': 'success', 'token': token})
    else:
        # 사용자가 없다면, 실패 메시지 전송
        return jsonify({'result': 'fail'})
    
# ID 중복 확인 API
@app.route('/api/CheckId', methods=['POST'])
def CheckId():
    id_receive = request.form.get('id_give')
    existing_id = db.users.find_one({'id': id_receive})
    if existing_id:
        return jsonify({'result': 'fail'}) # 중복이면 fail
    else:
        return jsonify({'result': 'success'}) # 중복이 아니면 success

# 닉네임 중복 확인 API
@app.route('/api/CheckUsername', methods=['POST'])
def CheckUsername():
    username_receive = request.form.get('username_give')
    existing_username = db.users.find_one({'username': username_receive})
    if existing_username:
        return jsonify({'result': 'fail'})
    else:
        return jsonify({'result': 'success'})

# 회원가입 API
@app.route('/api/SignUp', methods=['POST'])
def SignUp():
    # 1. 클라이언트로부터 데이터 받아오기
    username_receive = request.form.get('username_give')
    id_receive = request.form.get('id_give')
    password_receive = request.form.get('password_give')
    email_receive = request.form.get('email_give')

   # 2. 서버 단에서 최종 중복 확인
    if db.users.find_one({'id': id_receive}):
        return jsonify({'result': 'fail_id'})
    if db.users.find_one({'username': username_receive}):
        return jsonify({'result': 'fail_username'})

    # 3. 비밀번호 암호화
    import hashlib
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    # 4. 모든 정보(암호화된 비밀번호 포함)를 DB에 저장
    user = {
        'username': username_receive,
        'password': password_hash, # 암호화된 비밀번호 저장
        'id': id_receive,
        'email': email_receive,
    }
    db.users.insert_one(user)

    return jsonify({'result': 'success'})

# 이메일 발송 API
@app.route('/api/find-account/send-email', methods=['POST'])
def SendAuthEmail():
    email_receive = request.form.get('email_give')
    username_receive = request.form.get('username_give')

    user = db.users.find_one({'email': email_receive, 'username': username_receive}, {'_id': False})

    if not user:
        return jsonify({'result': 'fail'})

    # 4자리 랜덤 인증 코드 생성
    auth_code = str(random.randint(1000, 9999))
    user_id = user['id']

    # --- 실제 이메일 발송 로직 ---
    # ⚠️ 주의: 실제 서비스에서는 이메일, 비밀번호를 코드에 직접 쓰지 말고, 환경변수 등을 사용해야 해!
    sender_email = "junglerKrafton@gmail.com"  # 보내는 사람 구글 이메일
    sender_password = "oulnhdmxinqdalkd"   # 위에서 발급받은 16자리 앱 비밀번호

    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.starttls()
    smtp.login(sender_email, sender_password)

    msg = MIMEText(f'정글 커뮤니티 아이디 찾기 인증 코드: [{auth_code}]')
    msg['Subject'] = '정글 커뮤니티 인증 코드'
    msg['To'] = email_receive

    smtp.sendmail(sender_email, email_receive, msg.as_string())
    smtp.quit()
    # ---------------------------

    # 인증 성공 시, 다음 단계에서 사용할 임시 토큰 발급 (사용자 ID와 인증코드 포함)
    payload = {
        'id': user_id,
        'auth_code': auth_code,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5) # 5분간 유효
    }
    temp_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    return jsonify({'result': 'success', 'temp_token': temp_token})

# 인증코드 확인 및 ID 반환 API
@app.route('/api/find-account/verify', methods=['POST'])
def VerifyFindAccountCode():
    token_receive = request.form.get('token_give')
    code_receive = request.form.get('code_give')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        
        user_id = payload['id']
        auth_code = payload['auth_code']

        if auth_code == code_receive:
            return jsonify({'result': 'success', 'user_id': user_id})
        else:
            return jsonify({'result': 'fail'})
            
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({'result': 'fail', 'msg': '인증 시간이 만료되었습니다. 다시 시도해주세요.'})
    
    # 비밀번호 재설정 API
@app.route('/api/reset-password', methods=['POST'])
def ResetPassword():
    token_receive = request.form.get('token_give')
    new_password_receive = request.form.get('new_password_give')

    try:
        # 1. 임시 토큰을 디코딩해서 사용자 ID를 다시 한번 확인
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']

        # 2. 새로운 비밀번호를 암호화
        new_password_hash = hashlib.sha256(new_password_receive.encode('utf-8')).hexdigest()

        # 3. DB에서 해당 ID를 가진 사용자의 비밀번호를 업데이트
        db.users.update_one({'id': user_id}, {'$set': {'password': new_password_hash}})

        return jsonify({'result': 'success'})
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({'result': 'fail', 'msg': '인증 시간이 만료되었습니다. 다시 시도해주세요.'})

# app.py의 페이지 렌더링 부분에 추가
@app.route('/AccountEditPage')
def AccountEditPage():
    # 토큰을 통해 로그인 여부 확인
    token_receive = request.cookies.get('mytoken')
    try:
        # 토큰이 유효하면 AccountEditPage.html을 보여줌
        jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('AccountEditPage.html')
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        # 토큰이 없거나 유효하지 않으면 로그인 페이지로 리다이렉트
        return redirect(url_for("home"))

# --- API 부분에 아래 3개 추가 ---

# [추가] 내 정보 가져오기 API
@app.route('/api/get-my-info', methods=['GET'])
def getMyInfo():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']
        
        # DB에서 해당 ID의 사용자 정보를 찾음 (비밀번호는 제외)
        user_info = db.users.find_one({'id': user_id}, {'_id': 0, 'password': 0})
        
        return jsonify({'result': 'success', 'user_info': user_info})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})

# [수정] updateMyInfo API (기존 함수를 이걸로 교체)
@app.route('/api/update-my-info', methods=['POST'])
def updateMyInfo():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']

        username_receive = request.form.get('username_give')
        email_receive = request.form.get('email_give')
        new_password_receive = request.form.get('password_give')

        # 이메일, 닉네임 중복 재확인 (다른 사람이 그 사이에 바꿨을 수도 있으므로)
        if db.users.find_one({'username': username_receive, 'id': {'$ne': user_id}}):
            return jsonify({'result': 'fail', 'msg': '이미 존재하는 닉네임입니다.'})
        if db.users.find_one({'email': email_receive, 'id': {'$ne': user_id}}):
            return jsonify({'result': 'fail', 'msg': '이미 존재하는 이메일입니다.'})

        doc = {'username': username_receive, 'email': email_receive}
        if new_password_receive:
            new_password_hash = hashlib.sha256(new_password_receive.encode('utf-8')).hexdigest()
            doc['password'] = new_password_hash

        db.users.update_one({'id': user_id}, {'$set': doc})
        return jsonify({'result': 'success', 'msg': '정보가 수정되었습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})
    
@app.route('/api/check-email', methods=['POST'])
def CheckEmail():
    email_receive = request.form.get('email_give')

    # DB에서 해당 이메일을 가진 사용자가 있는지 확인
    existing_email = db.users.find_one({'email': email_receive})

    # 이메일이 존재하기만 하면 fail 응답 (누가 쓰든 상관없이)
    if existing_email:
        return jsonify({'result': 'fail'})
    else:
        return jsonify({'result': 'success'})


if __name__ == '__main__':
   app.run('0.0.0.0', port=9391, debug=True)