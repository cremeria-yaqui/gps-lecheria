from flask import Flask, request, jsonify, render_template_string
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
DB = "rutas.db"

def init():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS ultima (ruta TEXT PRIMARY KEY, nombre TEXT, lat REAL, lon REAL, fecha TEXT)')
    c.commit(); c.close()
init()

NOMBRES = {"1":"Ruta 1","2":"Ruta 2","3":"Ruta 3"}

HTML1 = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="font-family:Arial;text-align:center;padding:20px"><h2>CREMERIA YAQUI</h2><select id="r" style="font-size:20px;padding:10px"><option value="1">Ruta 1</option><option value="2" selected>Ruta 2</option><option value="3">Ruta 3</option></select><br><br><button onclick="s()" style="font-size:22px;background:green;color:white;padding:15px 30px;border:none;border-radius:10px">INICIAR RUTA</button><p id="e">Esperando...</p><script>function s(){let r=document.getElementById('r').value;function e(p){fetch('/api/ubicacion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ruta:r,lat:p.coords.latitude,lon:p.coords.longitude})});document.getElementById('e').innerText='Enviando: '+p.coords.latitude.toFixed(5)};navigator.geolocation.getCurrentPosition(e);setInterval(()=>{navigator.geolocation.getCurrentPosition(e)},5000)}</script></body></html>"""

HTML2 = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>#map{height:75vh}</style></head><body><h2 style="text-align:center">CREMERIA YAQUI - EN VIVO</h2><div id="map"></div><div id="l"></div><script>var m=L.map('map').setView([27.48,-109.93],12);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);var mk={};function c(){fetch('/api/rutas').then(r=>r.json()).then(d=>{let h='';for(let k in d){let x=d[k];let col=k=='1'?'red':k=='2'?'blue':'green';if(mk[k]){mk[k].setLatLng([x.lat,x.lon])}else{mk[k]=L.circleMarker([x.lat,x.lon],{color:col,radius:12,fillColor:col,fillOpacity:1}).addTo(m)}h+='<div><b>'+x.nombre+'</b> - '+x.fecha+'</div>'};document.getElementById('l').innerHTML=h})}setInterval(c,3000);c()</script></body></html>"""

@app.route('/')
def a(): return render_template_string(HTML1)
@app.route('/panel')
def b(): return render_template_string(HTML2)

@app.route('/api/ubicacion', methods=['POST'])
def u():
    d=request.get_json(); ruta=str(d.get('ruta','1')); lat=float(d.get('lat')); lon=float(d.get('lon'))
    fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S'); nombre=NOMBRES.get(ruta,'Ruta '+ruta)
    c=sqlite3.connect(DB); c.execute('INSERT OR REPLACE INTO ultima VALUES (?,?,?,?,?)',(ruta,nombre,lat,lon,fecha)); c.commit(); c.close()
    return jsonify({'ok':True})

@app.route('/api/rutas')
def r():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    rows=c.execute('SELECT * FROM ultima').fetchall(); c.close()
    return jsonify({x['ruta']:{'nombre':x['nombre'],'lat':x['lat'],'lon':x['lon'],'fecha':x['fecha']} for x in rows})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
