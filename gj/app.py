from flask import Flask, render_template, request, jsonify # request, jsonify 추가

# MongoDB 연결 설정
client = MongoClient('mongodb://test:test@15.164.170.54', 27017)
db = client.dbjungle # 'dbjungle' 이라는 이름의 DB를 사용

app = Flask(__name__)

# 기본 URL 접속 시 login.html 파일을 보여줌
@app.route('/')
def home():
   return render_template('LoginPage.html')

## API 역할을 하는 부분

# 회원가입 API
@app.route('/api/signup', methods=['POST'])
def SignUp():
    # 1. 클라이언트로부터 데이터 받아오기
    username_receive = request.form.get('username_give')
    id_receive = request.form.get('id_give')
    password_receive = request.form.get('password_give')
    email_receive = request.form.get('email_give')

    # 2. 비밀번호 암호화 (절대!!! 비밀번호는 그대로 저장하면 안돼)
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