# Flask와 관련된 라이브러리들을 가져옴
# Flask: 웹 프레임워크 자체
# request: 클라이언트로부터의 요청을 처리하기 위함
# render_template: HTML 템플릿을 렌더링하기 위함
# jsonify: 파이썬 딕셔너리를 JSON 응답으로 변환하기 위함
from flask import Flask, request, render_template, jsonify
app = Flask(__name__)

# MongoDB와 상호작용하기 위한 pymongo 라이브러리를 가져옴
from pymongo import MongoClient
# MongoDB 클라이언트를 생성하여 데이터베이스에 연결
# 'mongodb://test:test@15.164.170.54'는 데이터베이스 주소, 사용자 이름, 비밀번호를 포함
client = MongoClient('mongodb://test:test@15.164.170.54',27017)
# 'dbjungle'이라는 이름의 데이터베이스를 사용
db = client.dbjungle
# 'shareData'라는 이름의 컬렉션을 사용
collection = db.shareData

# '/createShareData' URL에 대한 GET 요청을 처리
# 이 함수는 'createShareData.html' 템플릿을 렌더링하여 사용자에게 보여줌
# 즉, 새로운 게시글을 작성하는 페이지를 보여주는 역할
@app.route('/createShareData')
def home():
   return render_template('createShareData.html')

# '/createShareData' URL에 대한 POST 요청을 처리
# 이 함수는 사용자가 작성한 게시글 데이터를 받아 데이터베이스에 저장
@app.route('/createShareData', methods=['POST'])
def createShareData():
   # 클라이언트가 보낸 폼(form) 데이터에서 각 필드의 값을 가져옴
   shareTitle = request.form['shareTitle']  # 제목(title)
   shareContent = request.form['shareContent']  # 내용(content)
   shareDate = request.form['date'] # 작성 시간
   shareWriter = request.form['writer'] # 작성자 
      
   # 데이터베이스에 저장할 딕셔너리 객체를 생성
   share = {'title':shareTitle, 'content': shareContent, 'likes': 0, 'date': shareDate, 'writer':shareWriter}

   # mongoDb에 데이터를 삽입(insert)
   collection.insert_one(share)
   # 성공적으로 처리되었음을 알리는 JSON 응답을 반환
   return jsonify({'result': 'success'})

# '/shareDataBoardList' URL에 대한 GET 요청을 처리합
# 이 함수는 'readShareDataList.html' 템플릿을 렌더링
# 이 페이지는 모든 게시글 목록을 보여주는 역할
@app.route('/shareDataBoardList')
def shareDataBoardList():
   return render_template('readShareDataList.html')

import math # 총 페이지 수를 계산하기 위한 math 라이브러리

# '/readShareDataList' URL에 대한 GET 요청을 처리
# 이 함수는 요청된 페이지에 해당하는 게시글 데이터와 전체 페이지 수를 JSON으로 반환
@app.route('/readShareDataList')
def readShareDataList():
   # 클라이언트로부터 'page' 파라미터를 받아옵니다. 없으면 기본값은 1, 타입은 정수
   page = request.args.get('page', 1, type=int)
   
   # 한 페이지에 보여줄 게시글의 수를 10으로 설정
   limit = 10
   # 건너뛸 게시글의 수를 계산 (예: 3페이지의 경우 (3-1)*10 = 20개를 건너뜁니다)
   offset = (page - 1) * limit

   # 전체 게시글 수를 계산
   total_count = collection.count_documents({})
   # 전체 페이지 수를 계산 (올림 계산)
   total_pages = math.ceil(total_count / limit)

   # MongoDB에서 데이터를 조회할 때, 계산된 offset만큼 건너뛰고 limit만큼만 가져옴
   paginated_data = list(collection.find({}).sort('date', -1).skip(offset).limit(limit))
   
   # 각 문서의 '_id'를 JSON으로 변환 가능하도록 문자열로 바꿈
   for item in paginated_data:
       item['_id'] = str(item['_id'])
   
   # 성공 여부, 현재 페이지의 게시글 데이터, 그리고 전체 페이지 수를 함께 JSON으로 반환
   return jsonify({
      'result': 'success', 
      'shareDatas': paginated_data,
      'total_pages': total_pages
      })


# MongoDB의 ObjectId를 다루기 위해 bson 라이브러리에서 ObjectId를 가져옴
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
   data = collection.find_one({"_id": ObjectId(shareId)})
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
   result = collection.update_one(
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
   data = collection.find_one({"_id": ObjectId(shareId)})
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
   result = collection.update_one(
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
   result = collection.delete_one({"_id": ObjectId(shareId)})

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
