from flask import Flask, request, jsonify, render_template_string
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
DB = "rutas.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    c.execute('CREATE TABLE IF NOT EXISTS ultima (ruta TEXT PRIMARY KEY, nombre TEXT, chofer TEXT, lat REAL, lon REAL, fecha TEXT, velocidad REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS historial (id INTEGER PRIMARY KEY AUTOINCREMENT, ruta TEXT, nombre TEXT, chofer TEXT, lat REAL, lon REAL, fecha TEXT, velocidad REAL)')
    c.commit(); c.close()
init()

NOMBRES = {"1":"Ruta 1","2":"Ruta 2","3":"Ruta 3"}
COLORES = {"1":"#e11d48","2":"#2563eb","3":"#16a34a"}

# --- PANTALLA CHOFER PRO ---
HTML_CHOFER = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cremeria Yaqui - Chofer</title><style>body{font-family:Arial;margin:0;background:#0f172a;color:white;text-align:center;padding:20px} .card{background:white;color:#111;border-radius:16px;padding:20px;max-width:420px;margin:0 auto} select,input{width:100%;padding:14px;font-size:18px;border:2px solid #ddd;border-radius:10px;margin:8px 0} button{width:100%;padding:18px;font-size:22px;font-weight:bold;background:#16a34a;color:white;border:none;border-radius:12px} .ok{background:#dcfce7;color:#166534;padding:10px;border-radius:10px;margin-top:12px;font-weight:bold} .small{font-size:13px;color:#666}</style></head><body><h2 style="letter-spacing:2px">🧀 CREMERIA YAQUI</h2><p style="color:#94a3b8">SISTEMA GPS PROFESIONAL</p><div class="card"><h3>INICIO DE RUTA</h3><label>Tu Nombre</label><input id="chofer" placeholder="Ej: El Güero"><label>Tu Ruta</label><select id="r"><option value="1">Ruta 1</option><option value="2" selected>Ruta 2</option><option value="3">Ruta 3</option></select><button onclick="s()">▶ INICIAR RUTA</button><div id="e" class="ok" style="display:none">📡 ENVIANDO UBICACIÓN EN VIVO...</div><p class="small" id="info">Esperando GPS... Deja esta pantalla abierta y con datos.</p><p class="small">⚠️ No cierres esta ventana durante la ruta.</p></div><script>let on=false;function s(){let r=document.getElementById('r').value;let ch=document.getElementById('chofer').value||'Chofer';document.getElementById('e').style.display='block';on=true;function e(p){let v=p.coords.speed?Math.round(p.coords.speed*3.6):0;fetch('/api/ubicacion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ruta:r,chofer:ch,lat:p.coords.latitude,lon:p.coords.longitude,velocidad:v})});document.getElementById('info').innerText='Lat: '+p.coords.latitude.toFixed(5)+' | Vel: '+v+' km/h | '+new Date().toLocaleTimeString()};if(navigator.geolocation){navigator.geolocation.getCurrentPosition(e);setInterval(()=>{if(on) navigator.geolocation.getCurrentPosition(e)},5000)}else{document.getElementById('info').innerText='Tu cel no tiene GPS activado'}}</script></body></html>"""

# --- PANEL JEFE PRO ---
HTML_PANEL = """<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Panel Jefe - Cremeria Yaqui</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{margin:0;font-family:Arial;background:#f1f5f9} .top{background:#0f172a;color:white;padding:12px 18px;display:flex;justify-content:space-between;align-items:center} .top b{font-size:20px;letter-spacing:1px} .wrap{display:flex;height:calc(100vh - 58px)} .side{width:330px;background:white;padding:14px;overflow:auto;border-right:1px solid #ddd} #map{flex:1} .tarj{border:1px solid #e2e8f0;border-radius:12px;padding:12px;margin-bottom:10px} .dot{width:12px;height:12px;border-radius:50%;display:inline-block} .btn{background:#0f172a;color:white;border:none;padding:8px 12px;border-radius:8px;cursor:pointer;width:100%;margin-top:6px} .btn2{background:#dc2626;color:white;border:none;padding:8px 12px;border-radius:8px;cursor:pointer;width:100%;margin-top:6px} @media(max-width:800px){.wrap{flex-direction:column}.side{width:100%;height:280px}#map{height:60vh}}</style></head><body><div class="top"><div><b>🧀 CREMERIA YAQUI</b><br><small style="color:#94a3b8">PANEL DE CONTROL GPS - EN VIVO</small></div><div style="text-align:right"><span id="hora"></span><br><small id="total">0 unidades activas</small></div></div><div class="wrap"><div class="side"><h3 style="margin:0">🚛 Unidades en Ruta</h3><p style="font-size:12px;color:#666">Actualiza cada 3 segundos</p><div id="lista">Cargando...</div><button class="btn" onclick="location.reload()">🔄 Actualizar Mapa</button><button class="btn2" onclick="if(confirm('¿Borrar todo el historial de hoy y empezar limpio?')){fetch('/api/limpiar',{method:'POST'}).then(()=>location.reload())}">🗑️ Limpiar Día / Empezar Nuevo Día</button><hr><p style="font-size:12px;color:#666"><b>Leyenda:</b><br>🟢 En Movimiento &nbsp; 🟡 Detenido &nbsp; 🔴 Sin Señal<br><br><b>Tip de Jefe:</b> Si un chofer está detenido más de 15 min, márcale.</p></div><div id="map"></div></div><script>var m=L.map('map').setView([27.483,-109.932],12);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(m);var mk={}, lines={};function tiempo(f){if(!f) return 'Sin datos';let d=(new Date()-new Date(f.replace(' ','T')))/1000;if(d<60) return 'Hace '+Math.floor(d)+' seg';if(d<3600) return 'Hace '+Math.floor(d/60)+' min';return 'Hace '+Math.floor(d/3600)+' h'}function c(){fetch('/api/rutas').then(r=>r.json()).then(d=>{let h='';let act=0;for(let k in d){let x=d[k];let col=x.ruta=='1'?'#e11d48':x.ruta=='2'?'#2563eb':'#16a34a';let estado=x.velocidad>3?'🟢 EN MOVIMIENTO':(new Date()-new Date(x.fecha.replace(' ','T')))>90000?'🔴 SIN SEÑAL':'🟡 DETENIDO';if(x.velocidad>3||(new Date()-new Date(x.fecha.replace(' ','T')))<90000) act++;if(mk[k]){mk[k].setLatLng([x.lat,x.lon])}else{mk[k]=L.circleMarker([x.lat,x.lon],{color:col,radius:14,fillColor:col,fillOpacity:1,weight:3}).addTo(m).bindPopup('<b>'+x.nombre+'</b>')};fetch('/api/historial/'+k).then(r=>r.json()).then(pts=>{if(lines[k]) m.removeLayer(lines[k]);let coords=pts.map(p=>[p.lat,p.lon]);if(coords.length>1){lines[k]=L.polyline(coords,{color:col,weight:4,opacity:0.8}).addTo(m)}});h+='<div class="tarj"><span class="dot" style="background:'+col+'"></span> <b>'+x.nombre+'</b> - '+x.chofer+'<br>'+estado+'<br>🚀 '+x.velocidad+' km/h<br>🕒 '+x.fecha+'<br><small>'+tiempo(x.fecha)+'</small></div>'}document.getElementById('lista').innerHTML=h||'Sin unidades aún. Pide a los choferes que inicien ruta.';document.getElementById('total').innerText=act+' unidades activas';document.getElementById('hora').innerText=new Date().toLocaleTimeString()})}setInterval(c,3000);c()</script></body></html>"""

@app.route('/')
def a(): return render_template_string(HTML_CHOFER)
@app.route('/panel')
def b(): return render_template_string(HTML_PANEL)

@app.route('/api/ubicacion', methods=['POST'])
def u():
    d=request.get_json(); ruta=str(d.get('ruta','1')); lat=float(d.get('lat')); lon=float(d.get('lon'))
    chofer=d.get('chofer','Chofer'); vel=float(d.get('velocidad',0) or 0)
    fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S'); nombre=NOMBRES.get(ruta,'Ruta '+ruta)
    estado='MOVIMIENTO' if vel>3 else 'DETENIDO'
    c=db(); c.execute('INSERT OR REPLACE INTO ultima VALUES (?,?,?,?,?,?,?,?)',(ruta,nombre,chofer,lat,lon,fecha,vel,estado))
    c.execute('INSERT INTO historial (ruta,nombre,chofer,lat,lon,fecha,velocidad) VALUES (?,?,?,?,?,?,?)',(ruta,nombre,chofer,lat,lon,fecha,vel))
    c.commit(); c.close()
    return jsonify({'ok':True})

@app.route('/api/rutas')
def r():
    c=db(); rows=c.execute('SELECT * FROM ultima').fetchall(); c.close()
    return jsonify({x['ruta']:{'ruta':x['ruta'],'nombre':x['nombre'],'chofer':x['chofer'],'lat':x['lat'],'lon':x['lon'],'fecha':x['fecha'],'velocidad':x['velocidad'],'estado':x['estado']} for x in rows})

@app.route('/api/historial/<ruta>')
def hist(ruta):
    c=db(); rows=c.execute('SELECT lat,lon,fecha FROM historial WHERE ruta=? ORDER BY id DESC LIMIT 500',(ruta,)).fetchall(); c.close()
    return jsonify([{'lat':x['lat'],'lon':x['lon'],'fecha':x['fecha']} for x in reversed(rows)])

@app.route('/api/limpiar', methods=['POST'])
def limpiar():
    c=db(); c.execute('DELETE FROM ultima'); c.execute('DELETE FROM historial'); c.commit(); c.close()
    return jsonify({'ok':True})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
