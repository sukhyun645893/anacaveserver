from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling  # 🐬 대규모 커넥션 풀링 엔진 장착
import os

app = Flask(__name__)
CORS(app)  # 🛡️ 플러터 앱 통신 개방

# 🐬 MySQL 커넥션 풀(Connection Pool) 환경 구성
# 🐬 MySQL 커넥션 풀(Connection Pool) 환경 구성
db_config = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),  # ⚡ Aiven 클라우드 고유 포트를 동적으로 흡수하도록 엔진 장착!
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Ksh2006@"),  
    "database": os.environ.get("DB_NAME", "anacave_db"),
    "charset": 'utf8mb4'
}
db_pool = None

# 🔄 풀(Pool) 생성 로직을 안전하게 격리
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="anacave_pool",
        pool_size=32,  # 🚀 동시 처리할 최대 DB 연결 수 (트래픽에 따라 50, 100으로 확장 가능)
        pool_reset_session=True,
        **db_config
    )
    print("✅ [MySQL Pool] 대규모 트래픽 대응 커넥션 풀 완공 완료.")
except Exception as e:
    # ⚠️ Render 빌드용 임시 방어선: DB가 없어도 프로세스가 다운되지 않도록 경고만 출력
    print(f"⚠️ [MySQL Pool 초기화 실패 - 임시 우회]: {e}")


def get_db_connection():
    # 🔄 풀이 없으면 예외를 던져 런타임 에러로 처리 (서버 다운 방지)
    if not db_pool:
        raise Exception("현재 데이터베이스 서버와 연결되어 있지 않습니다.")
    return db_pool.get_connection()


def init_db():
    if not db_pool:
        print("⚠️ [init_db] DB Pool이 구성되지 않아 테이블 검증을 스킵합니다.")
        return

    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 🎭 유저 테이블 및 인덱스 정착
        c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NULL,
            password VARCHAR(255) NULL,
            chaptername VARCHAR(255) NULL,
            title VARCHAR(255) NULL,
            content TEXT NULL,
            INDEX idx_chaptername (chaptername)  -- ⚡ 대규모 조회 성능 향상을 위한 인덱스 질서 부여
        )
        ''')
        conn.commit()
        print("✅ [MySQL] posts 테이블 및 성능 인덱스 검증 완료")
    except Exception as e:
        print(f"❌ [DB 초기화 에러]: {e}")
    finally:
        if conn:
            conn.close()


@app.route('/post', methods=['POST'])
def receive_post():
    data = request.get_json()
    
    if not data or 'jsonstring' not in data:
        return jsonify({"success": False, "message": "데이터가 누락되었습니다."}), 400
    
    json_string = data.get('jsonstring', '')
    title = data.get('title', '')
    chaptername = data.get('chaptername', '')
    
    username = data.get('username', '익명')
    password = data.get('password', '')

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
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
            connection.close()


@app.route('/post', methods=['GET']) 
def submit_post():
    target_gallery = request.args.get('gallery')
    
    if not target_gallery:
        return jsonify({"success": False, "message": "gallery 파라미터가 지정되지 않았습니다."}), 400

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

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
        print(f"⚠️ 초기 DB 연결 실패, 서버 기동 유지: {e}")
        
    # Render 환경용 동적 포트 바인딩 안정화
    port = int(os.environ.get("PORT", 5119))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)