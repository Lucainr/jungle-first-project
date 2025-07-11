# Flask와 관련된 라이브러리들을 가져옴
# Flask: 웹 프레임워크 자체
# request: 클라이언트로부터의 요청을 처리하기 위함
# render_template: HTML 템플릿을 렌더링하기 위함
# jsonify: 파이썬 딕셔너리를 JSON 응답으로 변환하기 위함
import jwt # jwt 라이브러리 임포트
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash # request, jsonify 추가
import random # 랜덤 숫자 생성을 위한 라이브러리
import smtplib
from email.mime.text import MIMEText
import hashlib # 비밀번호 암호화를 위한 라이브러리
import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# MongoDB와 상호작용하기 위한 pymongo 라이브러리를 가져옴
from pymongo import MongoClient
# MongoDB 클라이언트를 생성하여 데이터베이스에 연결
# 'mongodb://test:test@15.164.170.54'는 데이터베이스 주소, 사용자 이름, 비밀번호를 포함
client = MongoClient('mongodb://test:test@15.164.170.54',27017)
# 'dbjungle'이라는 이름의 데이터베이스를 사용
db = client.dbjungle

app = Flask(__name__)

# JWT를 위한 비밀 키
SECRET_KEY = 'JUNGLE'

def get_user_id_from_token():
    token = request.cookies.get('mytoken')
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

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

@app.route('/main')
def mainPage():
    token_receive = request.cookies.get('mytoken')
    try:
        jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # --- 1. 이달의 정글러 찾기 (매월 1일 기준) ---
        # now = datetime.now()
        # start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # end_of_month = start_of_month + relativedelta(months=1) - timedelta(seconds=1)

        # pipeline = [
        #     # [수정] 날짜 필터링($match) 로직 추가
        #     {'$match': {'date': {'$gte': start_of_month, '$lte': end_of_month}}},
        #     {'$unionWith': {
        #         'coll': 'qnaBoard', 
        #         'pipeline': [{'$match': {'date': {'$gte': start_of_month, '$lte': end_of_month}}}]
        #     }},
        #     {'$sort': {'total_likes': -1}},
        #     {'$limit': 1}
        # ]

        # --- 2. 역대 정글러 찾기 (날짜 제한 없음) ---
        pipeline = [
            {'$unionWith': {'coll': 'qnaBoard'}},
            {'$group': {
                '_id': '$writer', 
                'total_likes': {'$sum': '$likes'},
                'post_title': {'$first': '$title'}
            }},
            {'$sort': {'total_likes': -1}},
            {'$limit': 1}
        ]
        result = list(db.shareData.aggregate(pipeline))
        jungler_of_month = None
        if result:
            top_user_id = result[0]['_id']
            # users 컬렉션에서 사용자 이름(username) 찾아오기
            top_user = db.users.find_one({'id': top_user_id})
            if top_user:
                jungler_of_month = {
                    'username': top_user['username'],
                    'post_title': result[0]['post_title']
                }

        # 2. 각 게시판 별 최신 글 3개 가져오기 (실제 DB 조회)
        # ⚠️ 중요: sort('date', -1)는 'date' 필드가 datetime 객체일 때만 정확히 동작함!
        share_posts = list(db.shareData.find({}).sort('date', -1).limit(3))
        qna_posts = list(db.qnaBoard.find({}).sort('date', -1).limit(3))
        study_posts = list(db.studies.find({}).sort('date', -1).limit(3))

        # --- 3. 템플릿에 데이터 전달 ---
        return render_template('MainPage.html', 
                               jungler=jungler_of_month,
                               share_posts=share_posts,
                               qna_posts=qna_posts,
                               study_posts=study_posts)

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        # 토큰이 없거나 유효하지 않으면 로그인 페이지로 리다이렉트
        return redirect(url_for("home"))

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
            'exp': datetime.utcnow() + timedelta(hours=1)  # 1시간 동안 유효?
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

    # 실제 이메일 발송 로직
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
        'exp': datetime.utcnow() + timedelta(minutes=5) # 5분간 유효
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


# 내 정보 가져오기 API
@app.route('/api/getMyInfo', methods=['GET'])
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

# 회원 정보 수정 API
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
   # 클라이언트로부터 'page' 파라미터를 받아옴 없으면 기본값은 1, 타입은 정수
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

      # 날짜 형식 변환 (오류 처리 강화)
      try:
          date_timestamp = item.get('date')
          # JavaScript의 Date.now()는 밀리초 단위이므로 1000으로 나누어 초 단위로 변환
          dt_object = datetime.fromtimestamp(int(date_timestamp) / 1000)
          item['formatted_date'] = dt_object.strftime('%Y-%m-%d %H:%M')
      except (ValueError, TypeError):
          # 날짜 데이터가 없거나, 비어있거나, 잘못된 형식일 경우
          item['formatted_date'] = '날짜 없음'

   return render_template('readShareDataList.html', shareDatas=paginated_data, total_pages=total_pages, page=page)

# MongoDB의 ObjectId를 다루기 위해 bson 라이브러리에서 ObjectId를 가져옴
from bson import ObjectId

# 댓글 추가
@app.route('/comments/add', methods=['POST'])
def add_comment():
    user_id = get_user_id_from_token()
    if user_id is None:
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})

    share_id = request.form.get('share_id')
    comment_content = request.form.get('comment_content')

    if not share_id or not comment_content:
        return jsonify({'result': 'fail', 'msg': '게시글 ID 또는 댓글 내용이 누락되었습니다.'})

    user_data = db.users.find_one({'id': user_id})
    username = user_data['username'] if user_data and 'username' in user_data else "알 수 없음"

    comment = {
        'shareId': share_id,
        'user_id': user_id,
        'username': username,
        'comment_content': comment_content,
        'timestamp': datetime.now()
    }
    db.comments.insert_one(comment)
    return jsonify({'result': 'success'})

# 댓글 조회
@app.route('/comments/<shareId>', methods=['GET'])
def get_comments(shareId):
    comments = list(db.comments.find({'shareId': shareId}).sort('timestamp', 1)) # 오래된 순서대로 정렬
    for comment in comments:
        comment['_id'] = str(comment['_id'])
        comment['timestamp'] = comment['timestamp'].strftime('%Y-%m-%d %H:%M:%S') # 시간 형식 변경
    return jsonify({'result': 'success', 'comments': comments})

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
   current_user_id = get_user_id_from_token() # 현재 로그인한 사용자 ID 가져오기
   if data:
      # '_id'를 문자열로 변환
      data['_id'] = str(data['_id'])
      # 성공 여부와 함께 게시글의 상세 데이터를 JSON으로 반환
      # writer_id로 users 컬렉션에서 username 찾기
      writer_id = data.get('writer')
      user = db.users.find_one({'id': writer_id})
      writer_username = user.get('username') if user else "알 수 없음"

      return jsonify({
            'result': 'success',
            'title': data.get('title'),
            'content': data.get('content'),
            'writer': data.get('writer'), # writer_id도 계속 포함
            'writerUsername': writer_username, # writerUsername 추가
            'date': data.get('date'),
            'likes': data.get('likes'),
            'current_user_id': current_user_id # 현재 사용자 ID 추가
      })
   else:
      # 해당 게시글을 찾지 못한 경우, 실패 메시지를 JSON으로 반환
      return jsonify({'result': 'fail', 'msg': '해당 게시글을 찾을 수 없습니다.'}), 404

# '/toggleLike/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 특정 게시글의 '좋아요' 수를 토글 (증가 또는 감소)
@app.route('/toggleLike/<shareId>', methods=['POST'])
def toggleLike(shareId):
    user_id = get_user_id_from_token()
    if user_id is None:
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})

    id = ObjectId(shareId)
    share_data = db.shareData.find_one({"_id": id})

    if not share_data:
        return jsonify({'result': 'fail', 'msg': '게시글을 찾을 수 없습니다.'})

    liked_by = share_data.get('liked_by', [])
    current_likes = share_data.get('likes', 0)

    if user_id in liked_by:
        # 이미 좋아요를 눌렀다면, 좋아요 취소
        db.shareData.update_one(
            {"_id": id},
            {"$pull": {"liked_by": user_id}, "$inc": {"likes": -1}}
        )
        new_likes = current_likes - 1
        liked_status = False
    else:
        # 좋아요를 누르지 않았다면, 좋아요 추가
        db.shareData.update_one(
            {"_id": id},
            {"$push": {"liked_by": user_id}, "$inc": {"likes": 1}}
        )
        new_likes = current_likes + 1
        liked_status = True
    
    return jsonify({'result': 'success', 'likes': new_likes, 'liked': liked_status})

# '/getLikeStatus/<shareId>' URL에 대한 GET 요청을 처리
# 이 함수는 특정 게시글에 대한 현재 사용자의 좋아요 상태를 반환
@app.route('/getLikeStatus/<shareId>', methods=['GET'])
def getLikeStatus(shareId):
    user_id = get_user_id_from_token()
    if user_id is None:
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})

    id = ObjectId(shareId)
    share_data = db.shareData.find_one({"_id": id})

    if not share_data:
        return jsonify({'result': 'fail', 'msg': '게시글을 찾을 수 없습니다.'})

    liked_by = share_data.get('liked_by', [])
    current_likes = share_data.get('likes', 0)
    
    liked_status = user_id in liked_by
    
    return jsonify({'result': 'success', 'likes': current_likes, 'liked': liked_status})

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

#flash 위해 필요한 키
app.secret_key = 'studies_secret_key'

#JWT 위해 필요한 키
SECRET_KEY = 'JUNGLE'


#db.studies.delete_many({})   #다 지우기

@app.route('/goToStudy')
def main():
    #return render_template('register.html')
    studies = list(db.studies.find().sort([('date', -1), ('_id', -1)]))
    return render_template('letsStudyMain.html', studies=studies)

@app.route('/study/<study_id>')
def study_detail(study_id):

    # 1. 쿠키에서 토큰 꺼내기
    token_receive = request.cookies.get('mytoken')

        
    try:
            # 2. 토큰 디코딩
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_id = payload['id']
            user_data = db.users.find_one({'id': user_id})
            username = user_data['username'] if user_data else "알 수 없음"
            
    except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
            user_id = "알 수 없음"
            username = "알 수 없음"


    #user에서 data 받아오기
    user_data = db.users.find_one({'id' : user_id})


    try: #ID는 원래 string 타입이 아님 따라서 변환 필요
        obj_id = ObjectId(study_id)
    except:
        return "유효하지 않은 ID입니다.", 400
    #아이디 찾으면
    study = db.studies.find_one({'_id': obj_id})

    if not study:
        return "존재하지 않는 스터디입니다.", 404
    #studyDetail에게 study 값 전달
    return render_template('studyDetail.html', study=study, user_data=user_data, current_user_id=user_id)


@app.route('/study/<study_id>/edit', methods=['GET', 'POST'])
def edit_study(study_id):
    study = db.studies.find_one({'_id': ObjectId(study_id)})
    if request.method == 'POST':
        # 폼에서 넘어온 값으로 업데이트
        title = request.form.get('title')
        capacity = int(request.form.get('capacity', 0))
        post = request.form.get('post')

        db.studies.update_one(
            {'_id': ObjectId(study_id)},
            {'$set': {
                'title': title,
                'capacity': capacity,
                'post': post
            }}
        )
        #수정후에는 studyDetail.html에게 값 전달 후 그 페이지로 이동
        return redirect(url_for('study_detail', study_id=study_id))
    
    else :
    # GET 요청 시 기존 데이터 채워진 폼 보여주기
        return render_template('editStudy.html', study=study)


@app.route('/submitStudy', methods=['GET', 'POST'])
def submit_study():
    if request.method == 'POST':
        # 1. 쿠키에서 토큰 꺼내기
        token_receive = request.cookies.get('mytoken')
        
        try:
            # 2. 토큰 디코딩
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_id = payload['id']
            user_data = db.users.find_one({'id': user_id})
            username = user_data['username'] if user_data else "알 수 없음"
            
        except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
            user_id = "알 수 없음"
            username = "알 수 없음"
        
        # except 블록 밖, 즉 여기부터는 예외 발생 여부와 관계없이 실행됨
        # 3. 폼 정보 받기
        capacity = request.form.get('capacity')
        post = request.form.get('post')
        title = request.form.get('title')
        createdTime = datetime.now()

        print(username)
        # 4. MongoDB에 저장
        db.studies.insert_one({
                'capacity': capacity,
                'title': title,
                'post': post,
                'number': 0,
                'date': createdTime,
                'user_id': user_id,
                'username': username
        })

        studies= db.studies.find().sort([('date', -1), ('_id', -1)])
        #success = True
        flash('등록 완료!')
        return render_template("letsStudyMain.html", studies=studies)

        
        
        #return render_template('result.html', title=title, capacity=capacity, post=post,)
    
    else:
        #studies = list(db.studies.find({}, {'_id': False}))
        #return render_template('result.html', studies=studies)
        studies= db.studies.find().sort([('date', -1), ('_id', -1)])

        return render_template('register.html', studies=studies)
    
    

@app.route('/study/delete', methods=['POST'])
def delete_study():
    id = request.form.get('_id')
    try:
        id = ObjectId(id)
    except:
        return "유효하지 않은 ID입니다.", 400

    db.studies.delete_one({'_id': id})

    flash("삭제 완료!")
    return redirect(url_for('main'))  # main 함수 이름에 맞게 변경하세요

    #정원 +1 되게 해주는 거
@app.route('/study/<study_id>', methods=['POST'])
def give_num(study_id):

    id = request.form.get('_id')

    capacity = int(request.form.get('capacity', 0))

    try:
        Obj_id = ObjectId(id)
    except:
        return "유효하지 않은 ID입니다.", 400
    

    study = db.studies.find_one({'_id': Obj_id})
    if not study:
        return "해당 ID가 존재하지 않습니다.", 404
    

    
    # 2. JWT에서 신청자 정보 꺼내기
    token = request.cookies.get('mytoken')
    # if not token:
    #     return "로그인이 필요합니다.", 401

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        applicant_id = payload.get('id') # 토큰에서 꺼낸 payload 에서 id를 꺼냄
        current_user_id = payload.get('id')
        user_data = db.users.find_one({'id': applicant_id})
        applicant_username = user_data['username'] if user_data and 'username' in user_data else "알 수 없음"

    except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
        applicant_id = '알 수 없음'
        applicant_username = '알 수 없음'

    # 같은 아이디 중복 신청 체크
    applicants = study.get('applicants', [])
    if any(applicant['applied_id'] == current_user_id for applicant in applicants):
        return render_template('studyDetail.html', study=study, current_user_id=current_user_id, alert_user="이미 신청하셨습니다!")
    
    new_number = study.get('number', 0) + 1
    ##정원초과면 alert 나오게 함 # 3. 정원 체크
    if new_number > capacity:
        study = db.studies.find_one({'_id': id})
        return render_template('studyDetail.html', alert_number="정원을 초과하였습니다!" ,study=study,current_user_id=applicant_id)
    
    else:
        db.studies.update_one(
        {'_id': ObjectId(study_id)},
        {
            '$set': {'number': new_number},
            '$push': {'applicants': {'applied_id': applicant_id, 'applied_username': applicant_username}}
        }
        )
        #새로고침의 효과
        updated_study = db.studies.find_one({'_id': Obj_id})

        return render_template('studyDetail.html', study=updated_study, current_user_id=applicant_id, alert_new="신청되었습니다!")

@app.route('/study/<study_id>/cancel', methods=['POST'])
def cancel_application(study_id):
    # study_id는 URL 파라미터로 받았으니, form에서 id 안 받아도 됨
    try:
        Obj_id = ObjectId(study_id)
    except:
        return "유효하지 않은 ID입니다.", 400

    study = db.studies.find_one({'_id': Obj_id})
    if not study:
        return "해당 ID가 존재하지 않습니다.", 404

    # JWT에서 로그인한 유저 ID 꺼내기
    token = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        current_user_id = payload.get('id')
    except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
        return "로그인이 필요합니다.", 401

    # 신청자 리스트에서 current_user_id와 같은 신청자 제외
    new_applicants = [app for app in study.get('applicants', []) if app.get('applied_id') != current_user_id]

    # 인원 수 1 감소, 최소 0
    new_number = max(study.get('number', 1) - 1, 0)

    # DB 업데이트
    db.studies.update_one(
        {'_id': Obj_id},
        {
            '$set': {
                'applicants': new_applicants,
                'number': new_number
            }
        }
    )

    updated_study = db.studies.find_one({'_id': Obj_id})
    return render_template('studyDetail.html', study=updated_study, current_user_id=current_user_id, alert_cancel="신청이 취소되었습니다.")
    
# '/create' URL에 대한 GET 요청을 처리
# 이 함수는 'createQnaBoard.html' 템플릿을 렌더링하여 사용자에게 보여줌
# 즉, 새로운 게시글을 작성하는 페이지를 보여주는 역할
@app.route('/createQnaBoard')
def createQnaBoard():
   return render_template('createQnaBoard.html')

# '/createQnaBoard' URL에 대한 POST 요청을 처리
# 이 함수는 사용자가 작성한 게시글 데이터를 받아 데이터베이스에 저장
@app.route('/createQnaBoard', methods=['POST'])
def addQnaData():
   # 클라이언트가 보낸 폼(form) 데이터에서 각 필드의 값을 가져옴
   qnaTitle = request.form['qnaTitle']  # 제목(title)
   qnaContent = request.form['qnaContent']  # 내용(content)
   qnaDate = request.form['date'] # 작성 시간
   qnaWriter = request.form['writer'] # 작성자 
      
   # 데이터베이스에 저장할 딕셔너리 객체를 생성
   share = {'title':qnaTitle, 'content': qnaContent, 'likes': 0, 'date': qnaDate, 'writer':qnaWriter}

   # mongoDb에 데이터를 삽입(insert)
   db.qnaBoard.insert_one(share)
   # 성공적으로 처리되었음을 알리는 JSON 응답을 반환
   return jsonify({'result': 'success'})

# '/qnaBoardList' URL에 대한 GET 요청을 처리합
# 이 함수는 'readQnaBoardList.html' 템플릿을 렌더링
# 이 페이지는 모든 게시글 목록을 보여주는 역할
@app.route('/qnaBoardList')
def qnaBoardList():
   # 클라이언트로부터 'page' 파라미터를 받아옴 없으면 기본값은 1, 타입은 정수
   page = request.args.get('page', 1, type=int)

   # 한 페이지에 보여줄 게시글의 수를 10으로 설정
   limit = 10
   # 건너뛸 게시글의 수를 계산 (예: 3페이지의 경우 (3-1)*10 = 20개를 건너뜁니다)
   offset = (page - 1) * limit

   # 전체 게시글 수를 계산
   total_count = db.qnaBoard.count_documents({})
   # 전체 페이지 수를 계산 (올림 계산)
   total_pages = math.ceil(total_count / limit)

   # MongoDB에서 데이터를 조회할 때, 계산된 offset만큼 건너뛰고 limit만큼만 가져옴
   paginated_data = list(db.qnaBoard.find({}).sort('date', -1).skip(offset).limit(limit))

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

      # 날짜 형식 변환 (오류 처리 강화)
      try:
          date_timestamp = item.get('date')
          # JavaScript의 Date.now()는 밀리초 단위이므로 1000으로 나누어 초 단위로 변환
          dt_object = datetime.fromtimestamp(int(date_timestamp) / 1000)
          item['formatted_date'] = dt_object.strftime('%Y-%m-%d %H:%M')
      except (ValueError, TypeError):
          # 날짜 데이터가 없거나, 비어있거나, 잘못된 형식일 경우
          item['formatted_date'] = '날짜 없음'

   return render_template('readQnaBoardList.html', shareDatas=paginated_data, total_pages=total_pages, page=page)

# MongoDB의 ObjectId를 다루기 위해 bson 라이브러리에서 ObjectId를 가져옴
from bson import ObjectId

# '/qnaBoard/<shareId>' URL에 대한 GET 요청을 처리
# <shareId>는 동적으로 변하는 값(게시글의 고유 ID)
# 이 함수는 특정 게시글의 상세 내용을 보여주는 'readQnaBoard.html' 페이지를 렌더링
@app.route('/qnaBoard/<shareId>')
def qnaBoard(shareId):
   return render_template('readQnaBoard.html', shareId=shareId)

# '/detail/qnaBoard/<shareId>' URL에 대한 GET 요청을 처리
# 이 함수는 특정 게시글의 상세 데이터를 조회하여 JSON 형태로 반환
@app.route('/detail/qnaBoard/<shareId>')
def showQnaBoard(shareId):
   # shareId를 ObjectId로 변환하여 해당 ID를 가진 문서를 찾음
   data = db.qnaBoard.find_one({"_id": ObjectId(shareId)})
   current_user_id = get_user_id_from_token() # 현재 로그인한 사용자 ID 가져오기
   if data:
      # '_id'를 문자열로 변환
      data['_id'] = str(data['_id'])
      # 성공 여부와 함께 게시글의 상세 데이터를 JSON으로 반환
      # writer_id로 users 컬렉션에서 username 찾기
      writer_id = data.get('writer')
      user = db.users.find_one({'id': writer_id})
      writer_username = user.get('username') if user else "알 수 없음"

      return jsonify({
            'result': 'success',
            'title': data.get('title'),
            'content': data.get('content'),
            'writer': data.get('writer'), # writer_id도 계속 포함
            'writerUsername': writer_username, # writerUsername 추가
            'date': data.get('date'),
            'likes': data.get('likes'),
            'current_user_id': current_user_id # 현재 사용자 ID 추가
      })
   else:
      # 해당 게시글을 찾지 못한 경우, 실패 메시지를 JSON으로 반환
      return jsonify({'result': 'fail', 'msg': '해당 게시글을 찾을 수 없습니다.'}), 404

# '/editQnaBoard/<shareId>' URL에 대한 GET 요청을 처리
# 이 함수는 기존 게시글을 수정하는 'editQnaBoard.html' 페이지를 렌더링
# 페이지에 기존 데이터를 채워넣기 위해 먼저 데이터를 조회
@app.route('/editQnaBoard/<shareId>')
def editQnaBoard(shareId):
   data = db.qnaBoard.find_one({"_id": ObjectId(shareId)})
   if data:
      data['_id'] = str(data['_id'])  # '_id'를 문자열로 변환
      # 조회한 데이터를 'editQnaBoard.html' 템플릿에 전달하여 렌더링
      return render_template('editQnaBoard.html', data=data)
   else:
      return "해당 게시글을 찾을 수 없습니다.", 404

# '/editQnaBoard/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 사용자가 수정한 게시글 데이터를 받아 데이터베이스를 업데이트
@app.route('/editQnaBoard/<shareId>', methods=['POST'])
def updateQnaBoard(shareId):
   # 수정된 제목과 내용을 폼 데이터에서 가져옴
   title = request.form['title']
   content = request.form['content']

   # 해당 ID를 가진 문서의 'title'과 'content' 필드를 업데이트($set)
   result = db.qnaBoard.update_one(
      {"_id": ObjectId(shareId)},
      {"$set": {"title": title, "content": content}}
   )

   # 업데이트 성공 여부에 따라 결과를 JSON으로 반환
   if result.modified_count == 1:
      return jsonify({'result': 'success'})
   else:
      return jsonify({'result': 'fail'})

# '/deleteQnaBoard/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 특정 게시글을 데이터베이스에서 삭제
@app.route('/deleteQnaBoard/<shareId>', methods=['POST'])
def deleteQnaBoard(shareId):
   # 해당 ID를 가진 문서를 삭제
   result = db.qnaBoard.delete_one({"_id": ObjectId(shareId)})

   # 삭제 성공 여부에 따라 결과를 JSON으로 반환
   if result.deleted_count == 1:
      return jsonify({'result': 'success'})
   else:
      return jsonify({'result': 'fail'})
  
# '/toggleLike/<shareId>' URL에 대한 POST 요청을 처리
# 이 함수는 특정 게시글의 '좋아요' 수를 토글 (증가 또는 감소)
@app.route('/qna/toggleLike/<shareId>', methods=['POST'])
def qnaToggleLike(shareId):
    user_id = get_user_id_from_token()
    if user_id is None:
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})

    id = ObjectId(shareId)
    share_data = db.qnaBoard.find_one({"_id": id})

    if not share_data:
        return jsonify({'result': 'fail', 'msg': '게시글을 찾을 수 없습니다.'})

    liked_by = share_data.get('liked_by', [])
    current_likes = share_data.get('likes', 0)

    if user_id in liked_by:
        # 이미 좋아요를 눌렀다면, 좋아요 취소
        db.qnaBoard.update_one(
            {"_id": id},
            {"$pull": {"liked_by": user_id}, "$inc": {"likes": -1}}
        )
        new_likes = current_likes - 1
        liked_status = False
    else:
        # 좋아요를 누르지 않았다면, 좋아요 추가
        db.qnaBoard.update_one(
            {"_id": id},
            {"$push": {"liked_by": user_id}, "$inc": {"likes": 1}}
        )
        new_likes = current_likes + 1
        liked_status = True
    
    return jsonify({'result': 'success', 'likes': new_likes, 'liked': liked_status})

# '/getLikeStatus/<shareId>' URL에 대한 GET 요청을 처리
# 이 함수는 특정 게시글에 대한 현재 사용자의 좋아요 상태를 반환
@app.route('/qna/getLikeStatus/<shareId>', methods=['GET'])
def getQnaLikeStatus(shareId):
    user_id = get_user_id_from_token()
    if user_id is None:
        return jsonify({'result': 'fail', 'msg': '로그인이 필요합니다.'})

    id = ObjectId(shareId)
    share_data = db.qnaBoard.find_one({"_id": id})

    if not share_data:
        return jsonify({'result': 'fail', 'msg': '게시글을 찾을 수 없습니다.'})

    liked_by = share_data.get('liked_by', [])
    current_likes = share_data.get('likes', 0)
    
    liked_status = user_id in liked_by
    
    return jsonify({'result': 'success', 'likes': current_likes, 'liked': liked_status})

@app.route('/recommendPost')
# 추천 게시글 출력
@app.route('/recommendPost')
def recommendPost():
    user_id = get_user_id_from_token()
    if user_id is None:
        return redirect(url_for("home")) # 로그인 페이지로 리다이렉트

    recommended_posts = []

    # db.qnaBoard에서 사용자가 좋아요를 누른 게시글 조회
    qna_liked_posts = list(db.qnaBoard.find({'liked_by': user_id}))
    for post in qna_liked_posts:
        post['_id'] = str(post['_id'])
        post['board_type'] = 'qna' # 게시판 종류 추가
        
        # 작성자 username 가져오기
        writer_id = post.get('writer')
        user = db.users.find_one({'id': writer_id})
        post['writerUsername'] = user.get('username') if user else "알 수 없음"

        # 날짜 형식 변환
        try:
            date_timestamp = post.get('date')
            dt_object = datetime.fromtimestamp(int(date_timestamp) / 1000)
            post['formatted_date'] = dt_object.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            post['formatted_date'] = '날짜 없음'
        
        recommended_posts.append(post)

    # db.shareData에서 사용자가 좋아요를 누른 게시글 조회
    share_liked_posts = list(db.shareData.find({'liked_by': user_id}))
    for post in share_liked_posts:
        post['_id'] = str(post['_id'])
        post['board_type'] = 'share' # 게시판 종류 추가

        # 작성자 username 가져오기
        writer_id = post.get('writer')
        user = db.users.find_one({'id': writer_id})
        post['writerUsername'] = user.get('username') if user else "알 수 없음"

        # 날짜 형식 변환
        try:
            date_timestamp = post.get('date')
            dt_object = datetime.fromtimestamp(int(date_timestamp) / 1000)
            post['formatted_date'] = dt_object.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            post['formatted_date'] = '날짜 없음'

        recommended_posts.append(post)
    
    # 날짜 기준으로 최신순 정렬
    recommended_posts.sort(key=lambda x: x.get('date', 0), reverse=True)

    # 페이지네이션을 위한 변수 계산
    page = request.args.get('page', 1, type=int)
    limit = 10 # 한 페이지에 보여줄 게시글 수
    offset = (page - 1) * limit

    # 전체 게시글 수를 계산 (좋아요 누른 게시글 전체)
    total_count = len(recommended_posts)
    total_pages = math.ceil(total_count / limit)

    # 현재 페이지에 해당하는 게시글만 슬라이싱
    paginated_recommended_posts = recommended_posts[offset:offset + limit]

    return render_template('recommendPost.html',
                           recommended_posts=paginated_recommended_posts,
                           total_pages=total_pages,
                           page=page)

# 이 스크립트가 직접 실행될 때만 아래 코드를 실행
# (다른 파일에서 이 파일을 import할 때는 실행되지 않음)
# 내가 쓴 글 출력
@app.route('/writtenPost')
def writtenPosts():
    user_id = get_user_id_from_token()
    if user_id is None:
        return redirect(url_for("home")) # 로그인 페이지로 리다이렉트

    written_posts = []

    # db.qnaBoard에서 사용자가 작성한 게시글 조회
    qna_authored_posts = list(db.qnaBoard.find({'writer': user_id}))
    for post in qna_authored_posts:
        post['_id'] = str(post['_id'])
        post['board_type'] = 'qna' # 게시판 종류 추가
        
        # 작성자 username 가져오기 (이미 writer 필드에 user_id가 있으므로, user_id로 username을 찾음)
        user = db.users.find_one({'id': user_id})
        post['writerUsername'] = user.get('username') if user else "알 수 없음"

        # 날짜 형식 변환
        try:
            date_timestamp = post.get('date')
            dt_object = datetime.fromtimestamp(int(date_timestamp) / 1000)
            post['formatted_date'] = dt_object.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            post['formatted_date'] = '날짜 없음'
        
        written_posts.append(post)

    # db.shareData에서 사용자가 작성한 게시글 조회
    share_authored_posts = list(db.shareData.find({'writer': user_id}))
    for post in share_authored_posts:
        post['_id'] = str(post['_id'])
        post['board_type'] = 'share' # 게시판 종류 추가

        # 작성자 username 가져오기
        user = db.users.find_one({'id': user_id})
        post['writerUsername'] = user.get('username') if user else "알 수 없음"

        # 날짜 형식 변환
        try:
            date_timestamp = post.get('date')
            dt_object = datetime.fromtimestamp(int(date_timestamp) / 1000)
            post['formatted_date'] = dt_object.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            post['formatted_date'] = '날짜 없음'

        written_posts.append(post)
    
    # 날짜 기준으로 최신순 정렬
    written_posts.sort(key=lambda x: x.get('date', 0), reverse=True)

    # 페이지네이션을 위한 변수 계산
    page = request.args.get('page', 1, type=int)
    limit = 10 # 한 페이지에 보여줄 게시글 수
    offset = (page - 1) * limit

    # 전체 게시글 수를 계산
    total_count = len(written_posts)
    total_pages = math.ceil(total_count / limit)

    # 현재 페이지에 해당하는 게시글만 슬라이싱
    paginated_written_posts = written_posts[offset:offset + limit]

    return render_template('writtenPost.html',
                           written_posts=paginated_written_posts,
                           total_pages=total_pages,
                           page=page)

if __name__ == '__main__':   
    # Flask 개발 서버를 실행
    # '0.0.0.0'은 모든 IP 주소에서 접근 가능
    # port=5001은 5001번 포트를 사용하도록 설정합니다. - 5000 으로 변환 예정
    # debug=True는 디버그 모드를 활성화하여 코드 변경 시 서버가 자동으로 재시작되고, 오류 발생 시 자세한 정보를 보여줌
    app.run('0.0.0.0',port=5001,debug=True)
