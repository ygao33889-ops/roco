from flask import Flask, render_template_string, request, jsonify, session, Response
import json
import os

app = Flask(__name__)
app.secret_key = "lock_world_pet_ledger_2026_secret"
ADMIN_PASSWORD = "123456"
DATA_FILE = "pet_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "pets": [],
            "big_eggs": []
        }
        save_data(default)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def require_admin():
    return session.get("admin", False)

HTML = '''
<!DOCTYPE html>
<html lang="zh‑CN">
<head>
<meta charset="UTF-8">
 <meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>洛克王国世界 精灵台账</title>
<style>
*{box-sizing:border-box;font-family:"Microsoft Yahei",sans-serif;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{max-width:none;margin:0;padding:0;background:#f0f2f5;min-height:100vh;background-size:cover;background-position:center;background-attachment:fixed;}
.landing{height:100vh;min-height:600px;display:flex;align-items:center;justify-content:center;background:#111;background-size:cover;background-position:center;position:relative;overflow:hidden;}
.landing::after{content:"";position:absolute;inset:0;background:rgba(0,0,0,.28);}
.landing-content{position:relative;z-index:2;text-align:center;color:#fff;padding:30px;}
.landing-content h1{font-size:48px;text-shadow:0 3px 12px rgba(0,0,0,.5);margin-bottom:16px;}
.landing-content p{font-size:18px;margin-bottom:25px;text-shadow:0 2px 8px rgba(0,0,0,.5);}
.enter-btn{padding:13px 34px;border:0;border-radius:30px;background:#fff;color:#16213e;font-size:17px;font-weight:bold;cursor:pointer;}
.main-page{max-width:1100px;margin:0 auto;padding:20px;min-height:100vh;}
.public-tip{background:rgba(255,255,255,.92);padding:12px 16px;border-radius:8px;margin-bottom:16px;color:#555;font-size:14px;}
body::before{content:"";position:fixed;inset:0;background:rgba(255,255,255,.78);z-index:-1;}
.pet-img{width:64px;height:64px;object-fit:contain;border-radius:10px;background:#f7f8fb;border:1px solid #eee;}
.pet-card{display:flex;align-items:center;gap:14px;}
.section-title{display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none;}
.section-title .arrow{transition:.2s;font-size:16px;}
.collapsed .arrow{transform:rotate(-90deg);}
.collapse-body{overflow:hidden;transition:max-height .25s ease;}
.settings{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px;}
.settings label{font-size:13px;color:#555;}
.bg-preview{width:46px;height:30px;object-fit:cover;border-radius:5px;border:1px solid #ddd;}
 h1{text-align:center;color:#1a1a2e;margin-bottom:20px;}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);}
.card h2{color:#16213e;margin-bottom:16px;font-size:20px;border-left:4px solid #0f3460;padding-left:10px;}
.auth-bar{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:16px 20px;border-radius:12px;margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.auth-bar input{padding:8px 14px;border:none;border-radius:6px;font-size:14px;flex:1;min-width:150px;color:#333;}
.auth-bar button{padding:8px 18px;background:#fff;color:#667eea;border:none;border-radius:6px;cursor:pointer;font-weight:bold;font-size:14px;}
.auth-bar .status{font-size:14px;}
.auth-bar .logout{background:transparent;color:#fff;border:1px solid #fff;}
.auth-bar .export-btn{background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.5);}
table{width:100%;border-collapse:collapse;margin-top:12px;}
th,td{padding:12px 10px;text-align:left;border-bottom:1px solid #eee;}
th{background:#f8f9fc;color:#333;font-weight:600;}
tr:hover{background:#f8f9fc;}
input,select{padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px;}
.add-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;}
.add-row input,.add-row select{flex:1;min-width:100px;}
.btn{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:14px;}
.btn-primary{background:#0f3460;color:#fff;}
.btn-danger{background:#e94560;color:#fff;}
.hidden{display:none !important;}
.readonly-tip{background:#fff3cd;color:#856404;padding:10px 16px;border-radius:6px;margin-bottom:16px;font-size:14px;}
.import-area{margin-top:12px;padding:12px;background:#f8f9fc;border-radius:8px;}
</style>
</head>
<body>
<div class="landing" id="landing">
  <div class="landing-content">
    <h1>洛克王国世界</h1>
    <p>精灵台账 · 大块头蛋记录</p>
    <button class="enter-btn" onclick="enterMain()">进入主页面 ↓</button>
  </div>
</div>
<div class="main-page" id="mainPage">
<button class="btn" onclick="backToLanding()" style="margin-bottom:12px;">↑ 返回背景首页</button>
<h1>洛克王国世界 精灵台账</h1>
<div class="auth-bar">
    <span class="status" id="authStatus">🔒 只读模式</span>
    <input type="password" id="pwdInput" placeholder="管理员密码">
    <button onclick="login()">解锁编辑</button>
    <button class="logout hidden" id="logoutBtn" onclick="logout()">退出</button>
    <button class="export-btn hidden" id="exportBtn" onclick="exportData()">导出备份</button>
</div>

<div class="readonly-tip hidden" id="readonlyTip">当前为游客模式：只能查看“大块头蛋”。输入管理员密码后才能编辑并查看其他内容。</div>
<div class="public-tip" id="publicTip">👀 游客模式：当前仅开放“大块头蛋”查看。</div>

<div class="card hidden" id="petCard">
    <div class="section-title" onclick="toggleSection('petCard')">
        <h2>我的精灵列表</h2><span class="arrow">▼</span>
    </div>
    <div class="collapse-body">
    <div class="add-row hidden" id="petAddBar">
        <input id="petName" placeholder="精灵名字">
        <select id="petSex">
            <option value="雄性">雄性</option>
            <option value="雌性">雌性</option>
            <option value="无性别">无性别</option>
        </select>
        <input id="petEggGroup" placeholder="蛋组">
        <input id="petBonus" placeholder="加成">
        <label style="display:flex;align-items:center;gap:5px;">图片 <input type="file" id="petImage" accept="image/*"></label>
        <button class="btn btn-primary" onclick="addPet()">新增</button>
    </div>
    <table>
        <thead><tr><th>图片</th><th>名字</th><th>性别</th><th>蛋组</th><th>加成</th><th id="petOpHead" class="hidden">操作</th></tr></thead>
        <tbody id="petTableBody"></tbody>
    </table>
    </div>
</div>

<div class="card" id="eggCard">
    <div class="section-title" onclick="toggleSection('eggCard')">
        <h2>大块头蛋</h2><span class="arrow">▼</span>
    </div>
    <div class="collapse-body">
    <div class="add-row hidden" id="eggAddBar">
        <input id="eggInfo" placeholder="录入大块头蛋信息" style="flex:3;">
        <button class="btn btn-primary" onclick="addEgg()">新增</button>
    </div>
    <table>
        <thead><tr><th>大块头蛋记录</th><th id="eggOpHead" class="hidden">操作</th></tr></thead>
        <tbody id="eggTableBody"></tbody>
    </table>
    <div class="import-area hidden" id="importArea">
        <p style="margin-bottom:8px;font-size:13px;color:#666;">数据恢复（选择之前导出的JSON文件）：</p>
        <input type="file" id="importFile" accept=".json">
        <button class="btn btn-primary" onclick="importData()">恢复数据</button>
    </div>
    </div>
</div>

<div class="card hidden" id="settingsCard">
    <h2>网页外观设置</h2>
    <div class="settings">
        <label>背景图片：</label>
        <input type="file" id="bgFile" accept="image/*" onchange="changeBackground(this)">
        <button class="btn" onclick="clearBackground()">恢复默认背景</button>
        <span id="bgStatus" style="font-size:13px;color:#666;"></span>
    </div>
</div>

<script>
let isAdmin = false;
function enterMain(){document.getElementById("mainPage").scrollIntoView({behavior:"smooth"});}
function backToLanding(){document.getElementById("landing").scrollIntoView({behavior:"smooth"});}
function setPublicView(){
    document.getElementById("petCard").classList.add("hidden");
    document.getElementById("settingsCard").classList.add("hidden");
    document.getElementById("publicTip").classList.remove("hidden");
}
function setAdminView(){
    document.getElementById("petCard").classList.remove("hidden");
    document.getElementById("settingsCard").classList.remove("hidden");
    document.getElementById("publicTip").classList.add("hidden");
}
async function api(url, method="GET", body=null){
    let opt = {method, headers:{"Content-Type":"application/json"}};
    if(body) opt.body = JSON.stringify(body);
    let res = await fetch(url, opt);
    return res.json();
}
async function login(){
    let pwd = document.getElementById("pwdInput").value;
    let r = await api("/api/login","POST",{password:pwd});
    if(r.ok){
        isAdmin = true;
        document.getElementById("authStatus").textContent = "✅ 已解锁编辑";
        document.getElementById("readonlyTip").classList.add("hidden");
        setAdminView();
        ["logoutBtn","exportBtn","petAddBar","eggAddBar","petOpHead","eggOpHead","importArea"].forEach(id=>document.getElementById(id).classList.remove("hidden"));
        document.getElementById("pwdInput").classList.add("hidden");
        loadPets(); loadEggs();
    } else alert("密码错误");
}
async function logout(){
    await api("/api/logout","POST");
    location.reload();
}
async function checkAuth(){
    let r = await api("/api/check");<svg width='27' height='12' viewBox='0 0 27 12' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M6 0.5H21C24.0376 0.5 26.5 2.96243 26.5 6V11C26.5 11.2761 26.2761 11.5 26 11.5H6C2.96243 11.5 0.5 9.03757 0.5 6C0.5 2.96243 2.96243 0.5 6 0.5Z' fill='white'/><path d='M6 0.5H21C24.0376 0.5 26.5 2.96243 26.5 6V11C26.5 11.2761 26.2761 11.5 26 11.5H6C2.96243 11.5 0.5 9.03757 0.5 6C0.5 2.96243 2.96243 0.5 6 0.5Z' stroke='url(#paint0_radial_2138_6284)'/><path d='M7.27 3.69C8.56 3.69 9.21 4.39 9.21 5.81V9H8.07V5.91C8.07 5.06 7.68 4.64 6.9 4.64C6.62 4.64 6.37 4.74 6.16 4.94C5.92 5.16 5.78 5.48 5.74 5.89V9H4.6V3.83H5.74V4.43C5.94 4.19 6.17 4 6.42 3.88C6.68 3.75 6.96 3.69 7.27 3.69ZM12.6105 3.69C13.4605 3.69 14.1105 3.97 14.5605 4.55C14.9705 5.07 15.1805 5.8 15.1805 6.73H11.3105C11.3505 7.21 11.4805 7.58 11.7005 7.83C11.9205 8.08 12.2405 8.21 12.6505 8.21C13.0005 8.21 13.2805 8.13 13.5005 7.97C13.6705 7.84 13.8205 7.63 13.9605 7.34H15.1005C14.9805 7.82 14.7405 8.23 14.3805 8.55C13.9205 8.94 13.3505 9.14 12.6605 9.14C11.8905 9.14 11.2805 8.9 10.8305 8.43C10.3505 7.94 10.1105 7.27 10.1105 6.41C10.1105 5.64 10.3305 5 10.7905 4.48C11.2305 3.95 11.8405 3.69 12.6105 3.69ZM12.6405 4.62C12.2605 4.62 11.9705 4.72 11.7505 4.94C11.5405 5.15 11.4005 5.46 11.3305 5.87H13.9905C13.8905 5.03 13.4405 4.62 12.6405 4.62ZM15.5344 3.83H16.7944L17.8244 7.65L18.8444 3.83H19.8944L20.9144 7.65L21.9444 3.83H23.2044L21.4644 9H20.4044L19.3744 5.22L18.3344 9H17.2744L15.5344 3.83Z' fill='white'/><path d='M7.27 3.69C8.56 3.69 9.21 4.39 9.21 5.81V9H8.07V5.91C8.07 5.06 7.68 4.64 6.9 4.64C6.62 4.64 6.37 4.74 6.16 4.94C5.92 5.16 5.78 5.48 5.74 5.89V9H4.6V3.83H5.74V4.43C5.94 4.19 6.17 4 6.42 3.88C6.68 3.75 6.96 3.69 7.27 3.69ZM12.6105 3.69C13.4605 3.69 14.1105 3.97 14.5605 4.55C14.9705 5.07 15.1805 5.8 15.1805 6.73H11.3105C11.3505 7.21 11.4805 7.58 11.7005 7.83C11.9205 8.08 12.2405 8.21 12.6505 8.21C13.0005 8.21 13.2805 8.13 13.5005 7.97C13.6705 7.84 13.8205 7.63 13.9605 7.34H15.1005C14.9805 7.82 14.7405 8.23 14.3805 8.55C13.9205 8.94 13.3505 9.14 12.6605 9.14C11.8905 9.14 11.2805 8.9 10.8305 8.43C10.3505 7.94 10.1105 7.27 10.1105 6.41C10.1105 5.64 10.3305 5 10.7905 4.48C11.2305 3.95 11.8405 3.69 12.6105 3.69ZM12.6405 4.62C12.2605 4.62 11.9705 4.72 11.7505 4.94C11.5405 5.15 11.4005 5.46 11.3305 5.87H13.9905C13.8905 5.03 13.4405 4.62 12.6405 4.62ZM15.5344 3.83H16.7944L17.8244 7.65L18.8444 3.83H19.8944L20.9144 7.65L21.9444 3.83H23.2044L21.4644 9H20.4044L19.3744 5.22L18.3344 9H17.2744L15.5344 3.83Z' fill='url(#paint1_radial_2138_6284)'/><defs><radialGradient id='paint0_radial_2138_6284' cx='0' cy='0' r='1' gradientUnits='userSpaceOnUse' gradientTransform='translate(14.22 17.5) rotate(-90) scale(16.125 27.5537)'><stop stop-color='#5ADEFF'/><stop offset='1' stop-color='#2986FF'/></radialGradient><radialGradient id='paint1_radial_2138_6284' cx='0' cy='0' r='1' gradientUnits='userSpaceOnUse' gradientTransform='translate(14.5333 14.5833) rotate(-90) scale(13.4375 20.4102)'><stop stop-color='#5ADEFF'/><stop offset='1' stop-color='#2986FF'/></radialGradient></defs></svg>
    if(r.authed){
        isAdmin = true;
        document.getElementById("authStatus").textContent = "✅ 已解锁编辑";
        setAdminView();
        ["logoutBtn","exportBtn","petAddBar","eggAddBar","petOpHead","eggOpHead","importArea"].forEach(id=>document.getElementById(id).classList.remove("hidden"));
        document.getElementById("pwdInput").classList.add("hidden");
    } else {
        document.getElementById("readonlyTip").classList.remove("hidden");
        setPublicView();
    }
}
async function loadPets(){
    if(!isAdmin) return;
    let arr = await api("/api/pets");
    let tb = document.getElementById("petTableBody"); tb.innerHTML = "";
    arr.forEach((item,idx)=>{
        let tr = document.createElement("tr");
        let op = isAdmin ? `<td><button class="btn btn-danger" onclick="delPet(${idx})">删除</button></td>` : "";
        let img = item.image ? `<img class="pet-img" src="${item.image}" alt="${item.name}">` : `<div class="pet-img" style="display:flex;align-items:center;justify-content:center;color:#aaa;">暂无</div>`;
        tr.innerHTML = `<td>${img}</td><td>${item.name}</td><td>${item.sex}</td><td>${item.egg_group}</td><td>${item.bonus}</td>${op}`;
        tb.appendChild(tr);
    });
}
async function addPet(){
    if(!isAdmin) return;
    let name=document.getElementById("petName").value.trim(), sex=document.getElementById("petSex").value;
    let eg=document.getElementById("petEggGroup").value.trim(), bonus=document.getElementById("petBonus").value.trim();
    let imageFile=document.getElementById("petImage").files[0];
    if(!name){alert("名字不能为空");return;}
    let image="";
    if(imageFile){
        if(imageFile.size>2*1024*1024){alert("图片建议控制在2MB以内");return;}
        image=await new Promise(resolve=>{
            const r=new FileReader(); r.onload=e=>resolve(e.target.result); r.readAsDataURL(imageFile);
        });
    }
    let r = await api("/api/pets/add","POST",{name,sex,egg_group:eg,bonus,image});
    if(r.ok){
        ["petName","petEggGroup","petBonus"].forEach(id=>document.getElementById(id).value="");
        document.getElementById("petImage").value="";
        loadPets();
    }
}
async function delPet(idx){
    if(!isAdmin||!confirm("确定删除？")) return;
    let r = await api("/api/pets/del","POST",{index:idx});
    if(r.ok) loadPets();
}
async function loadEggs(){
    let arr = await api("/api/big_eggs");
    let tb = document.getElementById("eggTableBody"); tb.innerHTML = "";
    arr.forEach((item,idx)=>{
        let tr = document.createElement("tr");
        let op = isAdmin ? `<td><button class="btn btn-danger" onclick="delEgg(${idx})">删除</button></td>` : "";
        tr.innerHTML = `<td>${item}</td>${op}`; tb.appendChild(tr);
    });
}
async function addEgg(){
    if(!isAdmin) return;
    let info = document.getElementById("eggInfo").value.trim();
    if(!info) return;
    let r = await api("/api/egg/add","POST",{data:info});
    if(r.ok){ document.getElementById("eggInfo").value=""; loadEggs(); }
}
async function delEgg(idx){
    if(!isAdmin||!confirm("确定删除？")) return;
    let r = await api("/api/egg/del","POST",{index:idx});
    if(r.ok) loadEggs();
}
function toggleSection(id){
    const card=document.getElementById(id);
    card.classList.toggle("collapsed");
    const body=card.querySelector(".collapse-body");
    body.style.maxHeight=card.classList.contains("collapsed") ? "0px" : body.scrollHeight+"px";
    localStorage.setItem("collapse_"+id, card.classList.contains("collapsed") ? "1" : "0");
}
function restoreCollapse(){
    ["petCard","eggCard"].forEach(id=>{
        const card=document.getElementById(id), body=card.querySelector(".collapse-body");
        if(localStorage.getItem("collapse_"+id)==="1"){
            card.classList.add("collapsed"); body.style.maxHeight="0px";
        }else body.style.maxHeight=body.scrollHeight+"px";
    });
}
function changeBackground(input){
    const file=input.files[0];
    if(!file)return;
    const reader=new FileReader();
    reader.onload=e=>{
        localStorage.setItem("pageBackground",e.target.result);
        applyBackground(e.target.result);
    };
    reader.readAsDataURL(file);
}
function applyBackground(url){
    document.body.style.backgroundImage=`url("${url}")`;
    document.getElementById("landing").style.backgroundImage=`url("${url}")`;
    document.getElementById("bgStatus").textContent="已使用自定义背景";
}
function clearBackground(){
    localStorage.removeItem("pageBackground");
    document.body.style.backgroundImage="";
    document.getElementById("landing").style.backgroundImage="";
    document.getElementById("bgStatus").textContent="已恢复默认背景";
}
function restoreBackground(){
    const bg=localStorage.getItem("pageBackground");
    if(bg)applyBackground(bg);
}
function exportData(){
    window.open("/api/export","_blank");
}
async function importData(){
    let file = document.getElementById("importFile").files[0];
    if(!file){alert("请选择文件");return;}
    try{
        let text = await file.text();
        let jsonData = JSON.parse(text);
        let opt = {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify(jsonData)
        };
        let res = await fetch("/api/import", opt);
        let r = await res.json();
        if(r.ok){
            alert("恢复成功");
            loadPets();
            loadEggs();
        }
        else alert("恢复失败："+r.msg);
    }
    catch(err){
        console.error(err);
        alert("文件解析失败！JSON格式错误。");
    }
}
window.onload = ()=>{
    setPublicView();
    checkAuth();
    loadPets();
    loadEggs();
    restoreBackground();
    setTimeout(restoreCollapse,100);
};
</script>
</body>
</html>
'''

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/login", methods=["POST"])
def login():
    j = request.get_json()
    if j.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.route("/api/check")
def check():
    return jsonify({"authed": session.get("admin", False)})

@app.route("/api/pets")
def api_pets():
    if not require_admin():
        return jsonify({"ok": False, "msg": "无权限"}), 403
    return jsonify(load_data()["pets"])

@app.route("/api/big_eggs")
def api_eggs():
    return jsonify(load_data()["big_eggs"])

@app.route("/api/export")
def export_data():
    if not require_admin():
        return jsonify({"ok": False, "msg": "无权限"}), 403
    d = load_data()
    return Response(
        json.dumps(d, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content‑Disposition": "attachment; filename=pet_backup.json"}
    )

@app.route("/api/import", methods=["POST"])
def import_data():
    if not session.get("admin"):
        return jsonify({"ok": False, "msg": "无权限"}), 403
    try:
        j = request.get_json(silent=True)
        if j is None:
            return jsonify({"ok": False, "msg": "不是合法JSON文件"})
        if "pets" in j and "big_eggs" in j:
            save_data(j)
            return jsonify({"ok": True})
        return jsonify({"ok": False, "msg": "文件格式不对，缺少pets或big_eggs字段"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@app.route("/api/pets/add", methods=["POST"])
def pet_add():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    d["pets"].append({"name": j["name"], "sex": j["sex"], "egg_group": j["egg_group"], "bonus": j["bonus"], "image": j.get("image","")})
    save_data(d)
    return jsonify({"ok": True})

@app.route("/api/pets/del", methods=["POST"])
def pet_del():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    idx = j["index"]
    if 0 <= idx < len(d["pets"]):
        del d["pets"][idx]
        save_data(d)
    return jsonify({"ok": True})

@app.route("/api/egg/add", methods=["POST"])
def egg_add():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    d["big_eggs"].append(j["data"])
    save_data(d)
    return jsonify({"ok": True})

@app.route("/api/egg/del", methods=["POST"])
def egg_del():
    if not require_admin():
        return jsonify({"ok": False}), 403
    j = request.get_json()
    d = load_data()
    idx = j["index"]
    if 0 <= idx < len(d["big_eggs"]):
        del d["big_eggs"][idx]
        save_data(d)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
