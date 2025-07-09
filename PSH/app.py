from flask import Flask, render_template, request , redirect, url_for, flash
from pymongo import MongoClient 
from datetime import datetime
from bson import ObjectId
import jwt

client = MongoClient('mongodb://test:test@15.164.170.54', 27017)  # mongoDB는 27017 포트로 돌아갑니다.
#client = MongoClient('localhost', 27017) 
db = client.dbjungle  # 'dbjungle'라는 이름의 db를 만들거나 사용합니다.

app = Flask(__name__)

#flash 위해 필요한 키
app.secret_key = 'studies_secret_key'

#JWT 위해 필요한 키
SECRET_KEY = 'JUNGLE'


#db.studies.delete_many({})   #다 지우기

@app.route('/goToStudy')
def main():
    #return render_template('register.html')
    studies = list(db.studies.find({}))
    return render_template('letsStudyMain.html', studies=studies)

@app.route('/study/<study_id>')
def study_detail(study_id):
    try: #ID는 원래 string 타입이 아님 따라서 변환 필요
        obj_id = ObjectId(study_id)
    except:
        return "유효하지 않은 ID입니다.", 400
    #아이디 찾으면
    study = db.studies.find_one({'_id': obj_id})
    if not study:
        return "존재하지 않는 스터디입니다.", 404
    #studyDetail에게 study 값 전달
    return render_template('studyDetail.html', study=study)


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
            username = payload['username']  # username도 토큰에 포함돼 있어야 함

        except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
            user_id = "알 수 없음"
            username = "알 수 없음"
        
# except 블록 밖, 즉 여기부터는 예외 발생 여부와 관계없이 실행됨
        # 3. 폼 정보 받기
        capacity = request.form.get('capacity')
        post = request.form.get('post')
        title = request.form.get('title')
        createdTime = datetime.now()

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

        #success = True
        flash('등록 완료!')
        return redirect(url_for('main')) # 메인 페이지로 리다이렉트

        
        
        #return render_template('result.html', title=title, capacity=capacity, post=post,)
    
    else:
        #studies = list(db.studies.find({}, {'_id': False}))
        #return render_template('result.html', studies=studies)
        return render_template('register.html')
    

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
    #capacity = request.form.get('capacity')
    capacity = int(request.form.get('capacity', 0))

    try:
        id = ObjectId(id)
    except:
        return "유효하지 않은 ID입니다.", 400

    get_Id = db.studies.find_one({'_id': id})
    if not get_Id:
        return "해당 ID가 존재하지 않습니다.", 404
    
    # 2. JWT에서 신청자 정보 꺼내기
    token = request.cookies.get('mytoken')
    # if not token:
    #     return "로그인이 필요합니다.", 401

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        applicant_id = payload.get('id', '알 수 없음')
        applicant_username = payload.get('username', '알 수 없음')
    except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
        applicant_id = '알 수 없음'
        applicant_username = '알 수 없음'

    
    new_number = get_Id.get('number', 0) + 1
    ##정원초과면 alert 나오게 함 # 3. 정원 체크
    if new_number > capacity:
        study = db.studies.find_one({'_id': id})
        return render_template('studyDetail.html', alert_message="정원을 초과하였습니다!" ,study=study)
    
    else:
        db.studies.update_one(
        {'_id': ObjectId(study_id)},
        {
            '$set': {'number': new_number},
            '$push': {'applicants': {'applied_id': applicant_id, 'applied_username': applicant_username}}
        }
        )
        #새로고침의 효과
        updated_study = db.studies.find_one({'_id': id})

        return render_template('studyDetail.html', study=updated_study)





if __name__ == '__main__':
    app.run('localhost', port=5000, debug=True)