# Kurulum ve Yapılandırma Adımları

ElasticSearch ve Kibana kurulumu yapılmalıdır (Kurulumun yapıldığı varsayılmıştır).

## 1. Jaeger Collector Kurulumu

- Trace'leri toplayacak collector'u Docker kullanarak başlatın. Collector olarak Jaeger kullanılmaktadır.

```bash
 docker run -d --name jaeger-es \
  -e COLLECTOR_ZIPKIN_HTTP_PORT=9411 \
  -e SPAN_STORAGE_TYPE=elasticsearch \
  -e ES_SERVER_URLS="https://10.150.238.174:9200" \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 5775:5775/udp \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 14250:14250 \
  -p 9411:9411 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

- Jaeger'ın çalıştığını teyit edin.

```bash
elk@elk:~$ docker ps
CONTAINER ID   IMAGE                             COMMAND                  CREATED        STATUS        PORTS                                                                                                                                                                                                                                                                                                                                                                                                        NAMES
1acb6eef54b6   jaegertracing/all-in-one:latest   "/go/bin/all-in-one-…"   41 hours ago   Up 41 hours   0.0.0.0:4317-4318->4317-4318/tcp, :::4317-4318->4317-4318/tcp, 0.0.0.0:5775->5775/udp, :::5775->5775/udp, 0.0.0.0:5778->5778/tcp, :::5778->5778/tcp, 0.0.0.0:9411->9411/tcp, :::9411->9411/tcp, 0.0.0.0:14250->14250/tcp, :::14250->14250/tcp, 0.0.0.0:14268->14268/tcp, :::14268->14268/tcp, 0.0.0.0:16686->16686/tcp, :::16686->16686/tcp, 0.0.0.0:6831-6832->6831-6832/udp, :::6831-6832->6831-6832/udp   jaeger-es
```

## 2. Bağımlılıkların Yüklenmesi
- Gerekli bağımlılıkların bulunduğu requirements.txt dosyasını oluşturun.

```bash
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation
opentelemetry-instrumentation-flask
opentelemetry-instrumentation-requests
opentelemetry-instrumentation-sqlalchemy
opentelemetry-exporter-otlp
uvicorn
flask
requests
psycopg2-binary
```
- Bağımlılıkları yüklemek için aşağıdaki komutu çalıştırın:

```bash
python -m pip install -r requirements.txt
```
## 3. Flask API Oluşturulması

- Flask kullanılarak bir API oluşturulur. Örnek olarak kullanılacak API, kullanıcı ekleme, görüntüleme ve dış bir API'ye istek atacak şekilde üç endpoint içermektedir. İki veritabanı (SQLite ve PostgreSQL) kullanılarak işlemler yapılmaktadır.

app.py
```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/telemetry'
app.config['SQLALCHEMY_BINDS'] = {
    'sqlite': 'sqlite:///telemetry.db',
    'postgres': 'postgresql://postgres:postgres@localhost/telemetry'
}
app.config["SQLALCHEMY_ECHO"] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

pg_engine = create_engine('postgresql://postgres:postgres@localhost/telemetry')
sqlite_engine = create_engine(app.config['SQLALCHEMY_BINDS']['sqlite'])

# Create User Model for Postgre
class User(db.Model):
    __bind_key__ = 'postgres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

class SQLiteUser(db.Model):
    __bind_key__ = 'sqlite'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))



#API Routes
@app.route("/", methods=["GET"])
def get_users():
    try:
        users = User.query.all()
        return jsonify({"users:": [{"id": user.id, "name": user.name} for user in users]}), 200       
    except Exception as e:
        return jsonify({"error": str(e)}), 500   
    
@app.route("/", methods=["POST"])
def add_user():
    try:
        name = request.json['name']        
        
        sqlite_session = scoped_session(sessionmaker(bind=sqlite_engine))
        sqlite_user = SQLiteUser(name=name)        
        sqlite_session.add(sqlite_user)
        sqlite_session.commit()  

        pg_session = scoped_session(sessionmaker(bind=pg_engine))

        pg_user = User(name=name)
        pg_session.add(pg_user)
        pg_session.commit()       

        return jsonify({"postgresql_id": pg_user.id, "sqlite_id":sqlite_user.id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fetch-data")
def fetch_data():
    try:
        url =  "https://api.thecatapi.com/v1/images/search"
        response = requests.get(url)
        response.raise_for_status()    
        data = response.json()

        return jsonify(data), 200
    except Exception as e:
        status_code = response.status_code if hasattr(response, 'status_code') else 500
        return jsonify({"error": "Failed to fetch data " + str(e)}), status_code
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()    
        engine = create_engine(app.config['SQLALCHEMY_BINDS']['sqlite'])
        SQLiteUser.metadata.create_all(engine)        
    app.run(host="0.0.0.0", port=5005, debug=False) 
```
## 4. OpenTelemetry Bileşenlerinin Yüklenmesi
- OpenTelemetry bileşenlerini yükleyin:

```bash
opentelemetry-bootstrap -a install
```

## 5. Çevre Değişkenlerinin Ayarlanması
- Otomatik enstrümantasyon için çevre değişkenlerini ekleyin:

```bash
export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_RESOURCE_ATTRIBUTES=service.name=api-service-1
```
## 6. Flask Uygulamasının Başlatılması
- "opentelemetry-instrument" CLI aracı ile flask uygulamanızı başlatın.

```bash
opentelemetry-instrument --service_name api-service-1 python3 app.py
```

- Uygulamanız çalışıyor.

![image](https://github.com/limansub/gorevler/assets/79882285/b069b928-5421-4ae4-8e0d-e43ab1dadadb)

## 7. API Endpoint'lerine İstek Gönderme

- Herhangi bir endpoint'e istek göndererek Jaeger UI üzerinde trace verilerini kontrol edin.
```bash
ubuntu@ubuntu:~$ curl -X POST http://localhost:5005      -H "Content-Type: application/json"      -d '{"name": "Test"}'
{"postgresql_id":241,"sqlite_id":9}
```

- Jaeger UI üzerinden trace verilerini görüntüleyebilir ve veritabanı işlemlerini  izleyebilirsiniz.

![image](https://github.com/limansub/gorevler/assets/79882285/a5297b4a-18c9-4126-b29d-bbb3759c36f3)

## 8. ElasticSearch ve Kibana Kullanarak Verilerin Kontrol Edilmesi

- Kibana kullanarak ElasticSearch'teki verileri kontrol edin. Verileriniz ElasticSearch'e gönderilmiş olmalıdır. 

![image](https://github.com/limansub/gorevler/assets/79882285/5e5978e1-47cc-4102-8059-30c8234c915a)

- KQL sorgu dilini kullanarak PostgreSQL için verilere bakalım.
`tags:{ key :"db.system" and value : "postgresql" }`

![image](https://github.com/limansub/gorevler/assets/79882285/ae834971-2540-4429-84b8-f334456e0aad)










