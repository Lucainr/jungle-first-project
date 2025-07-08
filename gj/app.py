import jwt # jwt 라이브러리 임포트
import datetime # 유효기간 설정을 위한 라이브러리
from pymongo import MongoClient
from flask import Flask, render_template, request, jsonify # request, jsonify 추가

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



## API
# 로그인 API
@app.route('/api/login', methods=['POST'])
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
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# 회원가입 API
@app.route('/api/signup', methods=['POST'])
def SignUp():
    # 1. 클라이언트로부터 데이터 받아오기
    username_receive = request.form.get('username_give')
    id_receive = request.form.get('id_give')
    password_receive = request.form.get('password_give')
    email_receive = request.form.get('email_give')

    # 2. 비밀번호 암호화
    import hashlib
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    # 3. 아이디 중복 확인
    existing_username = db.users.find_one({'username': username_receive})
    existing_id = db.users.find_one({'id': id_receive})
    if existing_username:
        return jsonify({'result': 'fail', 'msg': '이미 존재하는 닉네임입니다.'})
    if existing_id:
        return jsonify({'result': 'fail', 'msg': '이미 존재하는 아이디입니다.'})

    # 4. 모든 정보(암호화된 비밀번호 포함)를 DB에 저장
    user = {
        'username': username_receive,
        'password': password_hash, # 암호화된 비밀번호 저장
        'id': id_receive,
        'email': email_receive,
    }
    db.users.insert_one(user)

    return jsonify({'result': 'success', 'msg': '회원가입이 완료되었습니다!'})

if __name__ == '__main__':
   app.run('0.0.0.0', port=9392, debug=True)