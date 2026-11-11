from flask import Flask, request, jsonify, render_template_string
import sqlite3, os, random
from datetime import datetime

app = Flask(__name__)
DB = "rutas.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    c.execute('CREATE TABLE IF NOT EXISTS ultima (id TEXT PRIMARY KEY, nombre TEXT, ruta TEXT, lat REAL, lon REAL, fecha TEXT, velocidad REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS historial (id INTEGER PRIMARY KEY AUTOINCREMENT, chofer_id TEXT, nombre TEXT, ruta TEXT, lat REAL, lon REAL, fecha TEXT, velocidad REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, chofer_id TEXT, nombre TEXT, ruta TEXT, cliente TEXT, fecha TEXT)')
    c.commit(); c.close()
init()

COLORES = ["#e11d48","#2563eb","#16a34a","#f59e0b","#8b5cf6","#ec4899","#06b6d4","#84cc16","#f97316","#14b8a6","#a855f7","#ef4444"]

HTML_CHOFER = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cremeria Yaqui</title><style>body{font-family:Arial;margin:0;background:#0f172a;color:white;text-align:center;padding:20px} .card{background:white;color:#111;border-radius:16px;padding:20px;max-width:420px;margin:0 auto} input,select{width:100%;padding:14px;font-size:18px;border:2px solid #ddd;border-radius:10px;margin:8px 0;box-sizing:border-box} button{width:100%;padding:18px;font-size:20px;font-weight:bold;background:#16a34a;color:white;border:none;border-radius:12px} .ok{background:#dcfce7;color:#166534;padding:10px;border-radius:10px;margin-top:12px;font-weight:bold;display:none} .small{font-size:13px;color:#666} .btn2{background:#2563eb;margin-top:10px}</style></head><body><h2>🧀 CREMERIA YAQUI</h2><p style="color:#94a3b8">GPS - TODOS LOS CHOFERES</p><div class="card"><h3 style="margin:0">INICIO DE RUTA</h3><label><b>Tu Nombre (así te va a ver el jefe)</b></label><input id="chofer" placeholder="Ej: El Güero, Don Chuy"><label><b>Tu Ruta</b></label><select id="r"><option value="Ruta 1">Ruta 1</option><option value="Ruta 2" selected>Ruta 2</option><option value="Ruta 3">Ruta 3</option><option value="Ruta 4">Ruta 4</option><option value="Ruta 5">Ruta 5</option><option value="Ruta Foranea">Ruta Foránea</option><option value="Reparto">Reparto / Otro</option></select><button onclick="s()">▶ INICIAR RUTA</button><div id="e" class="ok">📡 EN VIVO - ESTÁS ENVIANDO UBICACIÓN</div><p class="small" id="info">1. Pon tu nombre<br>2. Elige tu ruta<br>3. Pícale INICIAR y deja abierto</p><div id="entrega" style="display:none"><hr><label><b>¿Entregaste a un cliente?</b></label><input id="cliente" placeholder="Nombre del cliente / tienda"><button class="btn2" onclick="entregar()">✅ MARCAR ENTREGA</button><p id="msg" class="small"></p></div></div><script>let myId=localStorage.getItem('yaqui_id')||('C'+Date.now()+Math.floor(Math.random()*999));localStorage.setItem('yaqui_id',myId);let on=false;function s(){let ch=document.getElementById('chofer').value.trim();if(!ch){alert('Pon tu nombre primero, compa');return}let r=document.getElementById('r').value;document.getElementById('e').style.display='block';document.getElementById('entrega').style.display='block';on=true;function e(p){let v=p.coords.speed?Math.round(p.coords.speed*3.6):0;fetch('/api/ubicacion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:myId,nombre:ch,ruta:r,lat:p.coords.latitude,lon:p.coords.longitude,velocidad:v})});document.getElementById('info').innerText=ch+' | '+r+' | Vel: '+v+' km/h | '+new Date().toLocaleTimeString()}if(navigator.geolocation){navigator.geolocation.getCurrentPosition(e);setInterval(()=>{if(on) navigator.geolocation.getCurrentPosition(e)},5000)}}function entregar(){let ch=document.getElementById('chofer').value;let r=document.getElementById('r').value;let cl=document.getElementById('cliente').value||'Cliente';fetch('/api/entrega',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:myId,nombre:ch,ruta:r,cliente:cl})}).then(()=>{document.getElementById('msg').innerText='✅ Entrega a '+cl+' guardada';document.getElementById('cliente').value=''})}</script></body></html>"""

HTML_PANEL = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Panel Jefe - Cremeria Yaqui</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{margin:0;font-family:Arial;background:#f1f5f9} .top{background:#0f172a;color:white;padding:12px 16px;display:flex;justify-content:space-between} .wrap{display:flex;height:calc(100vh - 62px)} .side{width:360px;background:white;padding:14px;overflow:auto;border-right:1px solid #ddd} #map{flex:1;min-height:400px} .tarj{border:1px solid #e2e8f0;border-radius:12px;padding:12px;margin-bottom:10px} .btn{background:#0f172a;color:white;border:none;padding:10px;border-radius:8px;cursor:pointer;width:100%;margin-top:6px} .btn2{background:#dc2626;color:white;border:none;padding:10px;border-radius:8px;cursor:pointer;width:100%;margin-top:6px} @media(max-width:800px){.wrap{flex-direction:column}.side{width:100%;height:320px;box-sizing:border-box}#map{height:55vh;min-height:350px}}</style></head><body><div class="top"><div><b>🧀 CREMERIA YAQUI</b><br><small style="color:#94a3b8">PANEL JEFE - TODOS LOS CHOFERES EN VIVO</small></div><div style="text-align:right"><span id="hora"></span><br><small id="total">0 choferes</small></div></div><div class="wrap"><div class="side"><h3 style="margin:0">🚛 Choferes en Ruta</h3><p style="font-size:12px;color:#666">Cada chofer pone su nombre. Se actualiza cada 3 seg.</p><div id="lista">Cargando...</div><button class="btn" onclick="location.reload()">🔄 Actualizar</button><button class="btn2" onclick="if(confirm('¿Borrar todo y empezar nuevo día?')){fetch('/api/limpiar',{method:'POST'}).then(()=>location.reload())}">🗑️ Limpiar Día</button><hr><div id="entregas"><b>✅ Últimas Entregas</b><div id="elista" style="font-size:13px"></div></div></div><div id="map"></div></div><script>var m=L.map('map').setView([27.483,-109.932],12);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(m);setTimeout(()=>{m.invalidateSize()},500);var mk={},lines={};var cols=["#e11d48","#2563eb","#16a34a","#f59e0b","#8b5cf6","#ec4899","#06b6d4","#84cc16","#f97316","#14b8a6"];function tiempo(f){let d=(new Date()-new Date(f.replace(' ','T')))/1000;if(d<60) return 'Hace '+Math.floor(d)+' seg';if(d<3600) return 'Hace '+Math.floor(d/60)+' min';return 'Hace '+Math.floor(d/3600)+' h'}function c(){fetch('/api/rutas').then(r=>r.json()).then(d=>{let h='';let i=0;for(let k in d){let x=d[k];let col=cols[i%cols.length];i++;let dif=(new Date()-new Date(x.fecha.replace(' ','T')))/1000;let est=x.velocidad>3?'🟢 EN MOVIMIENTO':dif>90?'🔴 SIN SEÑAL':'🟡 DETENIDO';if(mk[k]){mk[k].setLatLng([x.lat,x.lon])}else{mk[k]=L.circleMarker([x.lat,x.lon],{color:col,radius:14,fillColor:col,fillOpacity:1,weight:3}).addTo(m).bindPopup('<b>'+x.nombre+'</b><br>'+x.ruta)};fetch('/api/historial/'+k).then(r=>r.json()).then(pts=>{if(lines[k]) m.removeLayer(lines[k]);let co=pts.map(p=>[p.lat,p.lon]);if(co.length>1){lines[k]=L.polyline(co,{color:col,weight:4,opacity:0.8}).addTo(m)}});h+='<div class="tarj"><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:'+col+'"></span> <b>'+x.nombre+'</b> - '+x.ruta+'<br>'+est+'<br>🚀 '+x.velocidad+' km/h<br>🕒 '+x.fecha+'<br><small>'+tiempo(x.fecha)+'</small></div>'}document.getElementById('lista').innerHTML=h||'Sin choferes aún. Que inicien ruta.';document.getElementById('total').innerText=Object.keys(d).length+' choferes activos';document.getElementById('hora').innerText=new Date().toLocaleTimeString()});fetch('/api/entregas').then(r=>r.json()).then(e=>{document.getElementById('elista').innerHTML=e.map(x=>'✅ <b>'+x.nombre+'</b> → '+x.cliente+' <small>('+x.fecha+')</small>').join('<br>')||'Sin entregas aún'})}setInterval(c,3000);c()</script></body></html>"""

@app.route('/')
def a(): return render_template_string(HTML_CHOFER)
@app.route('/panel')
def b(): return render_template_string(HTML_PANEL)

@app.route('/api/ubicacion', methods=['POST'])
def u():
    d=request.get_json(); cid=str(d.get('id')); nombre=d.get('nombre','Chofer'); ruta=d.get('ruta','Ruta 1')
    lat=float(d.get('lat')); lon=float(d.get('lon')); vel=float(d.get('velocidad',0) or 0)
    fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c=db(); c.execute('INSERT OR REPLACE INTO ultima VALUES (?,?,?,?,?,?,?)',(cid,nombre,ruta,lat,lon,fecha,vel))
    c.execute('INSERT INTO historial (chofer_id,nombre,ruta,lat,lon,fecha,velocidad) VALUES (?,?,?,?,?,?,?)',(cid,nombre,ruta,lat,lon,fecha,vel))
    c.commit(); c.close(); return jsonify({'ok':True})

@app.route('/api/rutas')
def r():
    c=db(); rows=c.execute('SELECT * FROM ultima').fetchall(); c.close()
    return jsonify({x['id']:{'id':x['id'],'nombre':x['nombre'],'ruta':x['ruta'],'lat':x['lat'],'lon':x['lon'],'fecha':x['fecha'],'velocidad':x['velocidad']} for x in rows})

@app.route('/api/historial/<cid>')
def hist(cid):
    c=db(); rows=c.execute('SELECT lat,lon FROM historial WHERE chofer_id=? ORDER BY id DESC LIMIT 400',(cid,)).fetchall(); c.close()
    return jsonify([{'lat':x['lat'],'lon':x['lon']} for x in reversed(rows)])

@app.route('/api/entrega', methods=['POST'])
def ent():
    d=request.get_json(); fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c=db(); c.execute('INSERT INTO entregas (chofer_id,nombre,ruta,cliente,fecha) VALUES (?,?,?,?,?)',(d.get('id'),d.get('nombre'),d.get('ruta'),d.get('cliente'),fecha)); c.commit(); c.close()
    return jsonify({'ok':True})

@app.route('/api/entregas')
def ents():
    c=db(); rows=c.execute('SELECT * FROM entregas ORDER BY id DESC LIMIT 30').fetchall(); c.close()
    return jsonify([{'nombre':x['nombre'],'ruta':x['ruta'],'cliente':x['cliente'],'fecha':x['fecha']} for x in rows])

@app.route('/api/limpiar', methods=['POST'])
def limpiar():
    c=db(); c.execute('DELETE FROM ultima'); c.execute('DELETE FROM historial'); c.execute('DELETE FROM entregas'); c.commit(); c.close()
    return jsonify({'ok':True})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
