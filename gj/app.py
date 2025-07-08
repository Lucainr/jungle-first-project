from flask import Flask, render_template

app = Flask(__name__)

# 기본 URL 접속 시 login.html 파일을 보여줌
@app.route('/')
def home():
   return render_template('LoginPage.html')

if __name__ == '__main__':
   app.run('0.0.0.0', port=9392, debug=True)