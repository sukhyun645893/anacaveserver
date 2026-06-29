from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling  # 🐬 대규모 커넥션 풀링 엔진 장착
import os

app = Flask(__name__)
CORS(app)  # 🛡️ 플러터 앱 통신 개방

# 🐬 MySQL 커넥션 풀(Connection Pool) 환경 구성
# 매번 새로 연결하는 것이 아니라, 거대한 연결 저장소를 만들어 동시 다발적 요청을 격리 처리합니다.
db_config = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Ksh2006@"),  # 환경 변수가 없으면 로컬 비밀번호 사용
    "database": os.environ.get("DB_NAME", "anacave_db"),
    "charset": 'utf8mb4'
}
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="anacave_pool",
        pool_size=32,  # 🚀 동시 처리할 최대 DB 연결 수 (트래픽에 따라 50, 100으로 확장 가능)
        pool_reset_session=True,
        **db_config
    )
    print("✅ [MySQL Pool] 대규모 트래픽 대응 커넥션 풀 완공 완료.")
except Exception as e:
    print(f"❌ [MySQL Pool 초기화 실패]: {e}")
    raise e


def get_db_connection():
    # 🔄 풀(Pool)에서 이미 준비된 대기열 연결을 광속으로 가로채 반환합니다.
    return db_pool.get_connection()


def init_db():
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 🎭 유저 테이블 및 인덱스 정착
        # 대규모 조회 성능 향상을 위해 갤러리 검색 조건인 chaptername에 INDEX를 부여합니다.
        c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255),
            password VARCHAR(255),
            chaptername VARCHAR(255),
            title VARCHAR(255),
            content TEXT,
            INDEX idx_chaptername (chaptername)  -- ⚡ 대규모 조회 성능 향상을 위한 인덱스 질서 부여
        )
        ''')
        conn.commit()
        print("✅ [MySQL] posts 테이블 및 성능 인덱스 검증 완료")
    except Exception as e:
        print(f"❌ [DB 초기화 에러]: {e}")
    finally:
        if conn:
            conn.close()  # 실제 연결을 파괴하지 않고 Pool로 안전하게 반환합니다.


@app.route('/post', methods=['POST'])
def receive_post():
    data = request.get_json()
    
    if not data or 'jsonstring' not in data:
        return jsonify({"success": False, "message": "데이터가 누락되었습니다."}), 400
    
    json_string = data.get('jsonstring', '')
    title = data.get('title', '')
    chaptername = data.get('chaptername', '')
    
    # NULL 값 튕김 방지를 위한 프론트엔드 데이터 보정 장치
    username = data.get('username', '익명')
    password = data.get('password', '')

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # username과 password도 안전하게 적립될 수 있도록 수식 확장
        sql = "INSERT INTO posts (username, password, chaptername, title, content) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (username, password, chaptername, title, json_string))
        
        connection.commit()
        cursor.close()
        
        return jsonify({
            "success": True, 
            "message": "데이터가 대규모 풀 아키텍처를 거쳐 성공적으로 안착되었습니다."
        }), 200

    except Exception as e:
        print(f"❌ [대규모 글쓰기 중 DB 에러]: {e}")
        return jsonify({"success": False, "message": f"데이터베이스 저장 실패: {e}"}), 500
    finally:
        if connection:
            connection.close()  # 자원 반환 (Pool 리턴)


@app.route('/post', methods=['GET']) 
def submit_post():
    target_gallery = request.args.get('gallery')
    
    if not target_gallery:
        return jsonify({"success": False, "message": "gallery 파라미터가 지정되지 않았습니다."}), 400

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 🐬 NULL 유입 크래시 방지 및 인덱싱 활용 고속 쿼리 실행
        sql = """
            SELECT 
                id, 
                COALESCE(username, '익명') AS username, 
                COALESCE(password, '') AS password, 
                chaptername, 
                title, 
                content 
            FROM posts 
            WHERE chaptername = %s 
            ORDER BY id DESC
        """
        cursor.execute(sql, (target_gallery,))
        posts_list = cursor.fetchall()
        cursor.close()

        return jsonify({"ok": posts_list}), 200

    except Exception as e:
        print(f"❌ [대규모 조회 중 DB 에러]: {e}")
        return jsonify({"success": False, "message": f"서버 에러: {e}"}), 500
    finally:
        if connection:
            connection.close()

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f"⚠️ [인프라 구동 경고] 초기 DB 연결에 실패했으나, 서버 기동을 강제 유지합니다: {e}")
        
    # ⚠️ 대규모 배포 모드로 갈 때는 debug=False로 두고, WSGI 컨테이너(Gunicorn 등)로 감싸 기동하게 됩니다.
    app.run(host='0.0.0.0', port=5119, debug=False, threaded=True)