from flask import Flask, render_template, request
from pymongo import MongoClient 

#client = MongoClient('mongodb://test:test@15.164.170.54', 27017)  # mongoDB는 27017 포트로 돌아갑니다.
client = MongoClient('localhost', 27017) 
db = client.dbStudy  # 'dbjungle'라는 이름의 db를 만들거나 사용합니다.

app = Flask(__name__)


@app.route('/')
def main():
    #return render_template('register.html')
    studies = list(db.studies.find({}))
    return render_template('letsStudyMain.html', studies=studies)

@app.route('/study/<study_id>')
def study_detail(study_id):
    from bson import ObjectId
    try:
        obj_id = ObjectId(study_id)
    except:
        return "유효하지 않은 ID입니다.", 400

    study = db.studies.find_one({'_id': obj_id})
    if not study:
        return "존재하지 않는 스터디입니다.", 404
    
    return render_template('studyDetail.html', study=study)


@app.route('/submit', methods=['GET', 'POST'])
def submit_study():
    if request.method == 'POST':
        capacity = request.form.get('capacity')
        post = request.form.get('post')
        title = request.form.get('title')
        db.studies.insert_one({'capacity' : capacity ,'title' : title, 'post' : post , 'number' : 0})

        # 이 부분에서 실제로 DB에 저장해도 됨 (지금은 그냥 변수 전달)
        return render_template('result.html', title=title, capacity=capacity, post=post,)
    
    else:
        #studies = list(db.studies.find({}, {'_id': False}))
        #return render_template('result.html', studies=studies)
        return render_template('register.html')
    

    
@app.route('/study/<study_id>', methods=['POST'])
def give_num(study_id):
    from bson import ObjectId

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
    
    new_number = get_Id.get('number', 0) + 1
    ##정원초과면 못나오게
    if new_number > capacity:
        study = db.studies.find_one({'_id': id})
        return render_template('studyDetail.html', alert_message="정원을 초과하였습니다!" ,study=study)
    
    else:
        db.studies.update_one({'_id': id}, {'$set': {'number': new_number}})
        #새로고침의 효과
        updated_study = db.studies.find_one({'_id': id})

        return render_template('studyDetail.html', study=updated_study)





if __name__ == '__main__':
    app.run('localhost', port=5000, debug=True)