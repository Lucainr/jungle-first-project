# Flask와 관련된 라이브러리들을 가져옴
# Flask: 웹 프레임워크 자체
# request: 클라이언트로부터의 요청을 처리하기 위함
# render_template: HTML 템플릿을 렌더링하기 위함
# jsonify: 파이썬 딕셔너리를 JSON 응답으로 변환하기 위함
import jwt
import datetime
import math # 총 페이지 수를 계산하기 위한 math 라이브러리
from flask import Flask, request, render_template, jsonify
app = Flask(__name__)

# MongoDB와 상호작용하기 위한 pymongo 라이브러리를 가져옴
from pymongo import MongoClient
# MongoDB 클라이언트를 생성하여 데이터베이스에 연결
# 'mongodb://test:test@15.164.170.54'는 데이터베이스 주소, 사용자 이름, 비밀번호를 포함
client = MongoClient('mongodb://test:test@15.164.170.54',27017)
# 'dbjungle'이라는 이름의 데이터베이스를 사용
db = client.dbjungle

# JWT를 위한 비밀 키
SECRET_KEY = 'JUNGLE'


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

@app.route('/getUserInfo')
def getUserInfo():
   token = request.cookies.get('mytoken')
   
   if token is None:
      return jsonify({'result': 'fail'})
   
   try:
      payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
      user_id = payload['id']

      user = db.users.find_one({'id': user_id})

      if user:
             return jsonify({
                'result': 'success',
                'id': user['id'],
                'username': user['username']
            })
      else:
         return jsonify({'result': 'fail', 'msg': '사용자를 찾을 수 없습니다.'})
   except jwt.ExpiredSignatureError:
      return jsonify({'result': 'fail', 'msg': '토큰이 만료되었습니다.'})
   except jwt.InvalidTokenError:
      return jsonify({'result': 'fail', 'msg': '유효하지 않은 토큰입니다.'})
      
   
# '/createShareData' URL에 대한 GET 요청을 처리
# 이 함수는 'createShareData.html' 템플릿을 렌더링하여 사용자에게 보여줌
# 즉, 새로운 게시글을 작성하는 페이지를 보여주는 역할
@app.route('/createShareData')
def createShareData():
   return render_template('createShareData.html')

# '/createShareData' URL에 대한 POST 요청을 처리
# 이 함수는 사용자가 작성한 게시글 데이터를 받아 데이터베이스에 저장
@app.route('/createShareData', methods=['POST'])
def addShareData():
   # 클라이언트가 보낸 폼(form) 데이터에서 각 필드의 값을 가져옴
   shareTitle = request.form['shareTitle']  # 제목(title)
   shareContent = request.form['shareContent']  # 내용(content)
   shareDate = request.form['date'] # 작성 시간
   shareWriter = request.form['writer'] # 작성자 
      
   # 데이터베이스에 저장할 딕셔너리 객체를 생성
   share = {'title':shareTitle, 'content': shareContent, 'likes': 0, 'date': shareDate, 'writer':shareWriter}

   # mongoDb에 데이터를 삽입(insert)
   db.shareData.insert_one(share)
   # 성공적으로 처리되었음을 알리는 JSON 응답을 반환
   return jsonify({'result': 'success'})

# '/shareDataBoardList' URL에 대한 GET 요청을 처리합
# 이 함수는 'readShareDataList.html' 템플릿을 렌더링
# 이 페이지는 모든 게시글 목록을 보여주는 역할
@app.route('/shareDataBoardList')
def shareDataBoardList():
   # 클라이언트로부터 'page' 파라미터를 받아옵니다. 없으면 기본값은 1, 타입은 정수
   page = request.args.get('page', 1, type=int)

   # 한 페이지에 보여줄 게시글의 수를 10으로 설정
   limit = 10
   # 건너뛸 게시글의 수를 계산 (예: 3페이지의 경우 (3-1)*10 = 20개를 건너뜁니다)
   offset = (page - 1) * limit

   # 전체 게시글 수를 계산
   total_count = db.shareData.count_documents({})
   # 전체 페이지 수를 계산 (올림 계산)
   total_pages = math.ceil(total_count / limit)

   # MongoDB에서 데이터를 조회할 때, 계산된 offset만큼 건너뛰고 limit만큼만 가져옴
   paginated_data = list(db.shareData.find({}).sort('date', -1).skip(offset).limit(limit))

   # 각 게시글마다 writer의 username을 찾아서 추가
   for item in paginated_data:
      item['_id'] = str(item['_id'])
      writer_id = item.get('writer')

      # writer id로 users 컬렉션에서 username 찾기
      user = db.users.find_one({'id': writer_id})
      if user:
         item['writerUsername'] = user.get('username')
      else:
         item['writerUsername'] = "알 수 없음"  # 만약 없으면 기본값

   return render_template('readShareDataList.html', shareDatas=paginated_data, total_pages=total_pages)

# MongoDB의 ObjectId를 다루기 위해 bson 라이브러리에서 ObjectId를 가져옴.
from bson import ObjectId

# '/shareDataBoard/<shareId>' URL에 대한 GET 요청을 처리
# <shareId>는 동적으로 변하는 값(게시글의 고유 ID)
# 이 함수는 특정 게시글의 상세 내용을 보여주는 'readShareData.html' 페이지를 렌더링
@app.route('/shareDataBoard/<shareId>')
def shareDataBoard(shareId):
   return render_template('readShareData.html', shareId=shareId)

# '/detail/shareDataBoard/<shareId>' URL에 대한 GET 요청을 처리
# 이 함수는 특정 게시글의 상세 데이터를 조회하여 JSON 형태로 반환
@app.route('/detail/shareDataBoard/<shareId>')
def showShareData(shareId):
   # shareId를 ObjectId로 변환하여 해당 ID를 가진 문서를 찾음
   data = db.shareData.find_one({"_id": ObjectId(shareId)})
   if data:
      # '_id'를 문자열로 변환
      data['_id'] = str(data['_id'])
      # 성공 여부와 함께 게시글의 상세 데이터를 JSON으로 반환
      return jsonify({
            'result': 'success',
            'title': data.get('title'),
            'content': data.get('content'),
            'writer': data.get('writer'),
            'date': data.get('date'),
            'likes': data.get('likes'),
      })
   else:
      # 해당 게시글을 찾지 못한 경우, 실패 메시지를 JSON으로 반환
      return jsonify({'result': 'fail', 'msg': '해당 게시글을 찾을 수 없습니다.'}), 404

# '/addLikes/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 특정 게시글의 '좋아요' 수를 1 증가
@app.route('/addLikes/<shareId>', methods=['POST'])
def addLikes(shareId):
   
   # shareId를 ObjectId로 변환
   id = ObjectId(shareId)
   
   # 해당 ID를 가진 문서의 'likes' 필드를 1 증가($inc)
   result = db.shareData.update_one(
      {"_id": id},
      {"$inc": {"likes": 1}}
   )
   
   # 업데이트가 성공적으로 이루어졌는지 확인하고 결과를 JSON으로 반환
   if result.modified_count == 1:
      return jsonify({'result': 'success'})
   else:
      return jsonify({'result': 'fail'})

# '/editShareData/<shareId>' URL에 대한 GET 요청을 처리
# 이 함수는 기존 게시글을 수정하는 'editShareData.html' 페이지를 렌더링
# 페이지에 기존 데이터를 채워넣기 위해 먼저 데이터를 조회
@app.route('/editShareData/<shareId>')
def editShareData(shareId):
   data = db.shareData.find_one({"_id": ObjectId(shareId)})
   if data:
      data['_id'] = str(data['_id'])  # '_id'를 문자열로 변환
      # 조회한 데이터를 'editShareData.html' 템플릿에 전달하여 렌더링
      return render_template('editShareData.html', data=data)
   else:
      return "해당 게시글을 찾을 수 없습니다.", 404

# '/editShareData/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 사용자가 수정한 게시글 데이터를 받아 데이터베이스를 업데이트
@app.route('/editShareData/<shareId>', methods=['POST'])
def updateShareData(shareId):
   # 수정된 제목과 내용을 폼 데이터에서 가져옴
   title = request.form['title']
   content = request.form['content']

   # 해당 ID를 가진 문서의 'title'과 'content' 필드를 업데이트($set)
   result = db.shareData.update_one(
      {"_id": ObjectId(shareId)},
      {"$set": {"title": title, "content": content}}
   )

   # 업데이트 성공 여부에 따라 결과를 JSON으로 반환
   if result.modified_count == 1:
      return jsonify({'result': 'success'})
   else:
      return jsonify({'result': 'fail'})

# '/deleteShareData/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 특정 게시글을 데이터베이스에서 삭제
@app.route('/deleteShareData/<shareId>', methods=['POST'])
def deleteShareData(shareId):
   # 해당 ID를 가진 문서를 삭제
   result = db.shareData.delete_one({"_id": ObjectId(shareId)})

   # 삭제 성공 여부에 따라 결과를 JSON으로 반환
   if result.deleted_count == 1:
      return jsonify({'result': 'success'})
   else:
      return jsonify({'result': 'fail'})

# 이 스크립트가 직접 실행될 때만 아래 코드를 실행
# (다른 파일에서 이 파일을 import할 때는 실행되지 않음)
if __name__ == '__main__':   
    # Flask 개발 서버를 실행
    # '0.0.0.0'은 모든 IP 주소에서 접근 가능
    # port=5001은 5001번 포트를 사용하도록 설정합니다. - 5000 으로 변환 예정
    # debug=True는 디버그 모드를 활성화하여 코드 변경 시 서버가 자동으로 재시작되고, 오류 발생 시 자세한 정보를 보여줌
    app.run('0.0.0.0',port=5001,debug=True)
